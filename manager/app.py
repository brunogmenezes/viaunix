#!/usr/bin/env python3
"""ViaUnix Manager - Backend + API de provisionamento, agente, acesso remoto auditado e painel web.

- Armazena maquinas, comandos, sessoes de acesso remoto e auditoria no PostgreSQL.
- Criptografa senhas (adm-*, root e senhas temporarias RustDesk) em AES-256-GCM
  usando chave mestra fora do banco (/etc/viaunix/master.key).
- Login do painel: API Jupiter (restrito a ADMIN_USERS) + conta admin local de emergencia.
- Fluxo de acesso remoto (estilo RustDesk): operador solicita com motivo -> usuario autoriza
  ou recusa na tela da estacao -> senha temporaria unica -> log completo de tudo.
"""

import asyncio
import base64
import csv
import datetime
import hashlib
import hmac
import io
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CONF_PATH = os.environ.get("VIAUNIX_MANAGER_CONF", "/etc/viaunix/manager.conf")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
COOKIE_NAME = "viaunix_session"
SESSION_TTL = 8 * 3600  # 8 horas
LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def load_config() -> dict:
    cfg = {
        "DATABASE_URL": "postgresql://viaunix:viaunix@127.0.0.1/viaunix_manager",
        "MASTER_KEY_FILE": "/etc/viaunix/master.key",
        "SESSION_SECRET": "dev-change-me",
        "PROVISION_TOKEN": "viaunix-provision-alterar-em-producao",
        "JUPITER_API_URL": "https://api.jupiter.com.br/action/Usuario/logar",
        "ADMIN_USERS": "Brunog",
        "LOCAL_ADMIN_USER": "admin",
        "LOCAL_ADMIN_HASH": "",
        "RUSTDESK_SERVER": "172.16.152.2",
    }
    if os.path.isfile(CONF_PATH):
        with open(CONF_PATH, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


CFG = load_config()


def load_master_key() -> bytes:
    path = CFG["MASTER_KEY_FILE"]
    with open(path, "r", encoding="utf-8") as f:
        raw = base64.b64decode(f.read().strip())
    if len(raw) != 32:
        raise RuntimeError(f"Chave mestra em {path} precisa ter 32 bytes (AES-256).")
    return raw


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    key = load_master_key()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return "v1:" + base64.b64encode(nonce + ct).decode("ascii")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    if not token.startswith("v1:"):
        return token
    raw = base64.b64decode(token[3:])
    nonce, ct = raw[:12], raw[12:]
    key = load_master_key()
    return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")


def sha256_hex(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


def verify_scrypt_hash(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    try:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, expected)


def make_session_cookie(username: str) -> str:
    exp = int(time.time()) + SESSION_TTL
    payload = f"{username}|{exp}".encode("utf-8")
    b64 = base64.urlsafe_b64encode(payload).decode("ascii")
    sig = hmac.new(CFG["SESSION_SECRET"].encode("utf-8"), b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def parse_session_cookie(cookie: Optional[str]) -> Optional[str]:
    if not cookie or "." not in cookie:
        return None
    b64, sig = cookie.rsplit(".", 1)
    expected = hmac.new(CFG["SESSION_SECRET"].encode("utf-8"), b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        decoded = base64.urlsafe_b64decode(b64.encode("ascii")).decode("utf-8")
        username, exp_str = decoded.rsplit("|", 1)
        if int(exp_str) < int(time.time()):
            return None
        return username
    except (ValueError, OSError):
        return None


def verify_jupiter_api(username: str, password: str) -> bool:
    payload = json.dumps({"usuario": username, "senha": password}).encode("utf-8")
    req = urllib.request.Request(
        CFG["JUPITER_API_URL"],
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            token = data.get("accessToken") if isinstance(data, dict) else None
            return isinstance(token, str) and bool(token.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


@contextmanager
def db_conn():
    conn = psycopg2.connect(CFG["DATABASE_URL"])
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    id SERIAL PRIMARY KEY,
                    hostname TEXT UNIQUE NOT NULL,
                    usuario TEXT UNIQUE NOT NULL,
                    senha_enc TEXT NOT NULL,
                    root_senha_enc TEXT NOT NULL DEFAULT '',
                    agent_token_hash TEXT NOT NULL DEFAULT '',
                    mac TEXT NOT NULL DEFAULT '',
                    serial TEXT NOT NULL DEFAULT '',
                    ip_origem TEXT NOT NULL DEFAULT '',
                    ip_local TEXT NOT NULL DEFAULT '',
                    vpn_ip TEXT NOT NULL DEFAULT '',
                    rustdesk_id TEXT NOT NULL DEFAULT '',
                    logged_user TEXT NOT NULL DEFAULT '',
                    os_version TEXT NOT NULL DEFAULT '',
                    cpu_percent REAL,
                    mem_percent REAL,
                    disk_percent REAL,
                    uptime_sec BIGINT,
                    last_seen TIMESTAMPTZ,
                    instalado_em TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                ALTER TABLE machines ADD COLUMN IF NOT EXISTS vpn_ip TEXT NOT NULL DEFAULT '';
                ALTER TABLE machines ADD COLUMN IF NOT EXISTS rustdesk_id TEXT NOT NULL DEFAULT '';

                CREATE TABLE IF NOT EXISTS commands (
                    id SERIAL PRIMARY KEY,
                    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    payload TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    output TEXT NOT NULL DEFAULT '',
                    requested_by TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS remote_sessions (
                    id SERIAL PRIMARY KEY,
                    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
                    hostname TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    operator_ip TEXT NOT NULL DEFAULT '',
                    station_user TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    rustdesk_id TEXT NOT NULL DEFAULT '',
                    otp_enc TEXT NOT NULL DEFAULT '',
                    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    responded_at TIMESTAMPTZ,
                    ended_at TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_hostname TEXT NOT NULL DEFAULT '',
                    ip TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)


def add_audit(cur, actor: str, action: str, target_hostname: str = "", ip: str = "", details: str = "") -> None:
    cur.execute(
        "INSERT INTO audit_log (actor, action, target_hostname, ip, details) VALUES (%s, %s, %s, %s, %s)",
        (actor, action, target_hostname, ip, details),
    )


def client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return fwd or (request.client.host if request.client else "")


def check_login_rate_limit(ip: str) -> None:
    now = time.time()
    recent = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
    if len(recent) >= 10:
        raise HTTPException(status_code=429, detail="Muitas tentativas de login. Aguarde 1 minuto.")
    recent.append(now)
    LOGIN_ATTEMPTS[ip] = recent


def require_admin(request: Request) -> str:
    user = parse_session_cookie(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    return user


app = FastAPI(title="ViaUnix Manager", docs_url=None, redoc_url=None)
if os.path.isdir("/usr/share/novnc"):
    app.mount("/novnc", StaticFiles(directory="/usr/share/novnc"), name="novnc")

# Relay WebSocket VNC em memoria: session_id -> {"agent": WebSocket, "viewer": WebSocket, "ready": asyncio.Event}
ACTIVE_VNC: dict[int, dict] = {}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# --- Schemas ---
class LoginBody(BaseModel):
    usuario: str
    senha: str


class ProvisionBody(BaseModel):
    hostname: str
    usuario: str
    senha: str
    root_senha: str = ""
    mac: str = ""
    serial: str = ""
    instalado_em: str = ""


class AgentRegisterBody(BaseModel):
    hostname: str
    mac: str = ""
    serial: str = ""


class HeartbeatBody(BaseModel):
    hostname: str = ""
    ip_local: str = ""
    vpn_ip: str = ""
    rustdesk_id: str = ""
    logged_user: str = ""
    os_version: str = ""
    cpu_percent: Optional[float] = None
    mem_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    uptime_sec: Optional[int] = None


class CommandCreateBody(BaseModel):
    action: str
    payload: str = ""


class CommandResultBody(BaseModel):
    status: str
    output: str = ""
    new_senha: Optional[str] = None
    new_root_senha: Optional[str] = None


class RemoteRequestBody(BaseModel):
    reason: str = ""


class RemoteRespondBody(BaseModel):
    approved: bool
    station_user: str = ""
    rustdesk_id: str = ""
    otp: str = ""
    detail: str = ""


ALLOWED_ACTIONS = {"reboot", "shutdown", "apt_upgrade", "lock_screen", "rotate_password", "shell"}


# --- Rotas publicas / saude / UI ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/vnc.html")
def vnc_viewer():
    return FileResponse(os.path.join(STATIC_DIR, "vnc.html"))


# --- Autenticacao do Painel Web ---
@app.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    ip = client_ip(request)
    check_login_rate_limit(ip)
    user = body.usuario.strip()
    pw = body.senha
    if not user or not pw:
        raise HTTPException(status_code=400, detail="Informe usuario e senha")

    ok = False
    method = ""
    if user == CFG["LOCAL_ADMIN_USER"] and verify_scrypt_hash(pw, CFG["LOCAL_ADMIN_HASH"]):
        ok = True
        method = "local"
    else:
        allowed = {u.strip().lower() for u in CFG.get("ADMIN_USERS", "").split(",") if u.strip()}
        if user.lower() in allowed and verify_jupiter_api(user, pw):
            ok = True
            method = "jupiter_api"

    with db_conn() as conn:
        with conn.cursor() as cur:
            if not ok:
                add_audit(cur, user, "login_failed", "", ip, "credenciais invalidas ou sem permissao")
                raise HTTPException(status_code=401, detail="Usuario ou senha invalidos (ou sem permissao de TI)")
            add_audit(cur, user, "login", "", ip, f"via {method}")

    token = make_session_cookie(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL,
        path="/",
    )
    return {"ok": True, "usuario": user}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(admin: str = Depends(require_admin)):
    return {"usuario": admin, "rustdesk_server": CFG.get("RUSTDESK_SERVER", "172.16.152.2")}


# --- Provisionamento ---
@app.post("/api/provision", status_code=201)
def provision(body: ProvisionBody, request: Request, x_viaunix_token: str = Header(default="")):
    if not hmac.compare_digest(x_viaunix_token, CFG["PROVISION_TOKEN"]):
        raise HTTPException(status_code=403, detail="invalid_token")

    hostname = body.hostname.strip()
    usuario = body.usuario.strip()
    if not hostname or not usuario or not body.senha:
        raise HTTPException(status_code=400, detail="missing_fields")

    agent_token = secrets.token_hex(32)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM machines WHERE hostname=%s OR usuario=%s", (hostname, usuario))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="duplicate_hostname_or_user")

            cur.execute(
                """
                INSERT INTO machines (
                    hostname, usuario, senha_enc, root_senha_enc, agent_token_hash,
                    mac, serial, ip_origem, instalado_em
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    hostname,
                    usuario,
                    encrypt_secret(body.senha),
                    encrypt_secret(body.root_senha),
                    sha256_hex(agent_token),
                    body.mac.strip(),
                    body.serial.strip(),
                    client_ip(request),
                    body.instalado_em.strip(),
                ),
            )
            add_audit(cur, "viaunix-provision", "provision", hostname, client_ip(request), f"usuario={usuario}")

    return {"ok": True, "hostname": hostname, "usuario": usuario, "agent_token": agent_token}


# --- Agente nas estacoes (viaunix-agent) ---
@app.post("/api/agent/register")
def agent_register(body: AgentRegisterBody, request: Request, x_viaunix_token: str = Header(default="")):
    if not hmac.compare_digest(x_viaunix_token, CFG["PROVISION_TOKEN"]):
        raise HTTPException(status_code=403, detail="invalid_token")

    hostname = body.hostname.strip()
    if not hostname:
        raise HTTPException(status_code=400, detail="missing_hostname")

    agent_token = secrets.token_hex(32)
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM machines WHERE hostname=%s", (hostname,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="machine_not_found")
            cur.execute(
                "UPDATE machines SET agent_token_hash=%s, mac=COALESCE(NULLIF(%s,''), mac), serial=COALESCE(NULLIF(%s,''), serial) WHERE id=%s",
                (sha256_hex(agent_token), body.mac.strip(), body.serial.strip(), row[0]),
            )
            add_audit(cur, "viaunix-agent", "agent_register", hostname, client_ip(request), "token emitido")

    return {"ok": True, "agent_token": agent_token}


def get_machine_by_agent_token(cur, token: str):
    if not token:
        raise HTTPException(status_code=403, detail="missing_agent_token")
    cur.execute("SELECT id, hostname, usuario FROM machines WHERE agent_token_hash=%s", (sha256_hex(token),))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="invalid_agent_token")
    return row


@app.post("/api/agent/heartbeat")
def agent_heartbeat(body: HeartbeatBody, request: Request, x_agent_token: str = Header(default="")):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            m = get_machine_by_agent_token(cur, x_agent_token)
            cur.execute(
                """
                UPDATE machines
                SET ip_origem=%s, ip_local=%s, vpn_ip=%s,
                    rustdesk_id=COALESCE(NULLIF(%s,''), rustdesk_id),
                    logged_user=%s, os_version=%s,
                    cpu_percent=%s, mem_percent=%s, disk_percent=%s, uptime_sec=%s,
                    last_seen=NOW()
                WHERE id=%s
                """,
                (
                    client_ip(request),
                    body.ip_local[:64],
                    body.vpn_ip[:64],
                    body.rustdesk_id[:64],
                    body.logged_user[:64],
                    body.os_version[:128],
                    body.cpu_percent,
                    body.mem_percent,
                    body.disk_percent,
                    body.uptime_sec,
                    m["id"],
                ),
            )

            # Expira solicitacoes de acesso remoto sem resposta ha mais de 90s
            cur.execute(
                """
                UPDATE remote_sessions
                SET status='timeout', responded_at=NOW()
                WHERE machine_id=%s AND status IN ('pending', 'notified')
                  AND requested_at < NOW() - INTERVAL '90 seconds'
                """,
                (m["id"],),
            )

            # 1. Prioridade: solicitacao pendente de acesso remoto (pede autorizacao na tela do usuario)
            cur.execute(
                """
                SELECT id, operator, reason FROM remote_sessions
                WHERE machine_id=%s AND status='pending'
                ORDER BY id ASC LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                (m["id"],),
            )
            rreq = cur.fetchone()
            remote_payload = None
            if rreq:
                cur.execute("UPDATE remote_sessions SET status='notified' WHERE id=%s", (rreq["id"],))
                remote_payload = {
                    "session_id": rreq["id"],
                    "operator": rreq["operator"],
                    "reason": rreq["reason"],
                }

            # 2. Proximo comando da fila (se houver)
            cur.execute(
                """
                SELECT id, action, payload FROM commands
                WHERE machine_id=%s AND status='pending'
                ORDER BY id ASC LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                (m["id"],),
            )
            cmd = cur.fetchone()
            cmd_payload = None
            if cmd:
                cur.execute("UPDATE commands SET status='running' WHERE id=%s", (cmd["id"],))
                cmd_payload = {
                    "id": cmd["id"],
                    "action": cmd["action"],
                    "payload": cmd["payload"],
                    "usuario": m["usuario"],
                }

    return {"ok": True, "command": cmd_payload, "remote_request": remote_payload}


@app.post("/api/agent/remote/{session_id}/respond")
def agent_remote_respond(session_id: int, body: RemoteRespondBody, request: Request, x_agent_token: str = Header(default="")):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            m = get_machine_by_agent_token(cur, x_agent_token)
            cur.execute(
                "SELECT id, operator, status FROM remote_sessions WHERE id=%s AND machine_id=%s",
                (session_id, m["id"]),
            )
            rs = cur.fetchone()
            if not rs:
                raise HTTPException(status_code=404, detail="session_not_found")

            new_status = "approved" if body.approved else "denied"
            cur.execute(
                """
                UPDATE remote_sessions
                SET status=%s, station_user=%s, rustdesk_id=COALESCE(NULLIF(%s,''), rustdesk_id),
                    otp_enc=%s, responded_at=NOW()
                WHERE id=%s
                """,
                (
                    new_status,
                    body.station_user[:64],
                    body.rustdesk_id[:64],
                    encrypt_secret(body.otp) if body.approved and body.otp else "",
                    session_id,
                ),
            )
            if body.rustdesk_id:
                cur.execute("UPDATE machines SET rustdesk_id=%s WHERE id=%s", (body.rustdesk_id[:64], m["id"]))

            detail = f"sessao=#{session_id} operador={rs['operator']} usuario_estacao={body.station_user or '-'} {body.detail}".strip()
            add_audit(cur, body.station_user or "estacao", f"remote_{new_status}", m["hostname"], client_ip(request), detail)
    return {"ok": True}


@app.post("/api/agent/command/{cmd_id}/result")
def agent_command_result(cmd_id: int, body: CommandResultBody, request: Request, x_agent_token: str = Header(default="")):
    status = body.status if body.status in ("done", "failed") else "failed"
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            m = get_machine_by_agent_token(cur, x_agent_token)
            cur.execute("SELECT id, action FROM commands WHERE id=%s AND machine_id=%s", (cmd_id, m["id"]))
            cmd = cur.fetchone()
            if not cmd:
                raise HTTPException(status_code=404, detail="command_not_found")

            if cmd["action"] == "rotate_password" and status == "done" and body.new_senha:
                cur.execute(
                    "UPDATE machines SET senha_enc=%s, root_senha_enc=COALESCE(NULLIF(%s,''), root_senha_enc) WHERE id=%s",
                    (encrypt_secret(body.new_senha), encrypt_secret(body.new_root_senha or ""), m["id"]),
                )
                add_audit(cur, "viaunix-agent", "password_rotated", m["hostname"], client_ip(request), f"cmd={cmd_id}")

            cur.execute(
                "UPDATE commands SET status=%s, output=%s, finished_at=NOW() WHERE id=%s",
                (status, body.output[:32768], cmd_id),
            )
    return {"ok": True}


# --- API do Painel Web (somente admin autenticado) ---
@app.get("/api/machines")
def list_machines(admin: str = Depends(require_admin)):
    now = datetime.datetime.now(datetime.timezone.utc)
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, hostname, usuario, mac, serial, ip_origem, ip_local, vpn_ip,
                       rustdesk_id, logged_user, os_version, cpu_percent, mem_percent,
                       disk_percent, uptime_sec, last_seen, instalado_em, created_at
                FROM machines
                ORDER BY last_seen DESC NULLS LAST, id DESC
            """)
            rows = cur.fetchall()

    out = []
    for r in rows:
        ls = r["last_seen"]
        online = bool(ls and (now - ls).total_seconds() <= 30)
        item = dict(r)
        item["online"] = online
        item["last_seen"] = ls.isoformat() if ls else None
        item["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
        out.append(item)
    return {"machines": out}


@app.post("/api/machines/{machine_id}/reveal")
def reveal_password(machine_id: int, request: Request, admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT hostname, usuario, senha_enc, root_senha_enc FROM machines WHERE id=%s", (machine_id,))
            m = cur.fetchone()
            if not m:
                raise HTTPException(status_code=404, detail="Maquina nao encontrada")
            add_audit(cur, admin, "reveal_password", m["hostname"], client_ip(request), "credenciais visualizadas")
    return {
        "hostname": m["hostname"],
        "usuario": m["usuario"],
        "senha": decrypt_secret(m["senha_enc"]),
        "root_senha": decrypt_secret(m["root_senha_enc"]),
    }


@app.post("/api/machines/{machine_id}/remote/request")
def request_remote_access(machine_id: int, body: RemoteRequestBody, request: Request, admin: str = Depends(require_admin)):
    reason = body.reason.strip()[:240]
    if not reason:
        raise HTTPException(status_code=400, detail="Informe o motivo do suporte remoto.")

    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, hostname, rustdesk_id, logged_user, last_seen FROM machines WHERE id=%s", (machine_id,))
            m = cur.fetchone()
            if not m:
                raise HTTPException(status_code=404, detail="Maquina nao encontrada")

            now = datetime.datetime.now(datetime.timezone.utc)
            if not m["last_seen"] or (now - m["last_seen"]).total_seconds() > 30:
                raise HTTPException(status_code=409, detail="A estacao esta offline no momento.")

            cur.execute(
                """
                INSERT INTO remote_sessions (machine_id, hostname, operator, operator_ip, station_user, reason, rustdesk_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (m["id"], m["hostname"], admin, client_ip(request), m["logged_user"] or "", reason, m["rustdesk_id"] or ""),
            )
            sid = cur.fetchone()["id"]
            add_audit(cur, admin, "remote_request", m["hostname"], client_ip(request), f"sessao=#{sid} motivo={reason}")

    return {"ok": True, "session_id": sid, "hostname": m["hostname"]}


@app.get("/api/remote/{session_id}")
def get_remote_session(session_id: int, admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, machine_id, hostname, operator, station_user, reason, status,
                       rustdesk_id, otp_enc, requested_at, responded_at, ended_at
                FROM remote_sessions WHERE id=%s
                """,
                (session_id,),
            )
            rs = cur.fetchone()
            if not rs:
                raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    otp = decrypt_secret(rs["otp_enc"]) if rs["status"] == "approved" and rs["otp_enc"] else ""
    return {
        "id": rs["id"],
        "machine_id": rs["machine_id"],
        "hostname": rs["hostname"],
        "operator": rs["operator"],
        "station_user": rs["station_user"],
        "reason": rs["reason"],
        "status": rs["status"],
        "rustdesk_id": rs["rustdesk_id"],
        "otp": otp,
        "requested_at": rs["requested_at"].isoformat() if rs["requested_at"] else None,
        "responded_at": rs["responded_at"].isoformat() if rs["responded_at"] else None,
        "ended_at": rs["ended_at"].isoformat() if rs["ended_at"] else None,
    }


@app.post("/api/remote/{session_id}/end")
async def end_remote_session(session_id: int, request: Request, admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, machine_id, hostname, status FROM remote_sessions WHERE id=%s", (session_id,))
            rs = cur.fetchone()
            if not rs:
                raise HTTPException(status_code=404, detail="Sessao nao encontrada")

            cur.execute(
                "UPDATE remote_sessions SET status='ended', otp_enc='', ended_at=NOW() WHERE id=%s",
                (session_id,),
            )
            add_audit(cur, admin, "remote_ended", rs["hostname"], client_ip(request), f"sessao=#{session_id} encerrada")

    # Fecha imediatamente os WebSockets (o agente encerra o x11vnc ao perder o tunel)
    slot = ACTIVE_VNC.pop(session_id, None)
    if slot:
        for key in ("viewer", "agent"):
            ws = slot.get(key)
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass
    return {"ok": True}


async def _relay_ws(src: WebSocket, dst: WebSocket) -> None:
    try:
        while True:
            msg = await src.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                await dst.send_bytes(msg["bytes"])
            elif msg.get("text") is not None:
                await dst.send_text(msg["text"])
    except Exception:
        pass


@app.websocket("/ws/vnc/agent/{session_id}")
async def ws_vnc_agent(websocket: WebSocket, session_id: int):
    token = websocket.headers.get("x-agent-token", "")
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, hostname FROM machines WHERE agent_token_hash=%s", (sha256_hex(token),))
            m = cur.fetchone()
            if not m:
                await websocket.close(code=1008)
                return
            cur.execute(
                "SELECT id, status FROM remote_sessions WHERE id=%s AND machine_id=%s",
                (session_id, m["id"]),
            )
            rs = cur.fetchone()
            if not rs or rs["status"] != "approved":
                await websocket.close(code=1008)
                return

    await websocket.accept()
    slot = ACTIVE_VNC.setdefault(session_id, {"agent": None, "viewer": None, "ready": asyncio.Event(), "done": asyncio.Event()})
    slot["agent"] = websocket
    slot["ready"].set()
    try:
        await slot["done"].wait()
    finally:
        ACTIVE_VNC.pop(session_id, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/vnc/viewer/{session_id}")
async def ws_vnc_viewer(websocket: WebSocket, session_id: int):
    admin = parse_session_cookie(websocket.cookies.get(COOKIE_NAME))
    if not admin:
        await websocket.close(code=1008)
        return

    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, hostname, status FROM remote_sessions WHERE id=%s", (session_id,))
            rs = cur.fetchone()
            if not rs or rs["status"] != "approved":
                await websocket.close(code=1008)
                return
            hostname = rs["hostname"]

    # Subprotocolo 'binary' esperado pelo noVNC
    subproto = "binary" if "binary" in websocket.headers.get("sec-websocket-protocol", "") else None
    await websocket.accept(subprotocol=subproto)

    slot = ACTIVE_VNC.setdefault(session_id, {"agent": None, "viewer": None, "ready": asyncio.Event(), "done": asyncio.Event()})
    try:
        await asyncio.wait_for(slot["ready"].wait(), timeout=20.0)
    except asyncio.TimeoutError:
        await websocket.close(code=1011)
        return

    agent_ws = slot.get("agent")
    if not agent_ws:
        await websocket.close(code=1011)
        return
    slot["viewer"] = websocket

    with db_conn() as conn:
        with conn.cursor() as cur:
            add_audit(cur, admin, "remote_connected", hostname, "", f"sessao=#{session_id} tela aberta no navegador")

    try:
        t1 = asyncio.create_task(_relay_ws(websocket, agent_ws))
        t2 = asyncio.create_task(_relay_ws(agent_ws, websocket))
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
    finally:
        slot["done"].set()
        ACTIVE_VNC.pop(session_id, None)
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE remote_sessions SET status='ended', otp_enc='', ended_at=COALESCE(ended_at, NOW()) WHERE id=%s AND status='approved'",
                    (session_id,),
                )
                add_audit(cur, admin, "remote_disconnected", hostname, "", f"sessao=#{session_id} desconectada")
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/api/remote")
def list_remote_sessions(admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, hostname, operator, operator_ip, station_user, reason, status,
                       rustdesk_id, requested_at, responded_at, ended_at
                FROM remote_sessions
                ORDER BY id DESC LIMIT 100
            """)
            rows = cur.fetchall()
    for r in rows:
        for k in ("requested_at", "responded_at", "ended_at"):
            r[k] = r[k].isoformat() if r[k] else None
    return {"sessions": rows}


@app.post("/api/machines/{machine_id}/command")
def enqueue_command(machine_id: int, body: CommandCreateBody, request: Request, admin: str = Depends(require_admin)):
    action = body.action.strip()
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail="Acao invalida")
    if action == "shell" and not body.payload.strip():
        raise HTTPException(status_code=400, detail="Informe o comando shell")

    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, hostname FROM machines WHERE id=%s", (machine_id,))
            m = cur.fetchone()
            if not m:
                raise HTTPException(status_code=404, detail="Maquina nao encontrada")
            cur.execute(
                "INSERT INTO commands (machine_id, action, payload, requested_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (machine_id, action, body.payload.strip(), admin),
            )
            cmd_id = cur.fetchone()["id"]
            details = body.payload.strip()[:120] if action == "shell" else ""
            add_audit(cur, admin, f"cmd:{action}", m["hostname"], client_ip(request), details)
    return {"ok": True, "command_id": cmd_id}


@app.get("/api/machines/{machine_id}/commands")
def list_machine_commands(machine_id: int, admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, action, payload, status, output, requested_by, created_at, finished_at
                FROM commands WHERE machine_id=%s ORDER BY id DESC LIMIT 30
                """,
                (machine_id,),
            )
            rows = cur.fetchall()
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
        r["finished_at"] = r["finished_at"].isoformat() if r["finished_at"] else None
    return {"commands": rows}


@app.get("/api/audit")
def list_audit(admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, actor, action, target_hostname, ip, details, created_at FROM audit_log ORDER BY id DESC LIMIT 200")
            rows = cur.fetchall()
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
    return {"audit": rows}


@app.get("/api/audit/export.csv")
def export_audit_csv(admin: str = Depends(require_admin)):
    with db_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, created_at, actor, action, target_hostname, ip, details FROM audit_log ORDER BY id DESC LIMIT 1000")
            rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "data_hora", "ator", "acao", "maquina", "ip", "detalhes"])
    for r in rows:
        writer.writerow([
            r["id"],
            r["created_at"].isoformat() if r["created_at"] else "",
            r["actor"],
            r["action"],
            r["target_hostname"],
            r["ip"],
            r["details"],
        ])
    return PlainTextResponse(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=viaunix-auditoria.csv"},
    )
