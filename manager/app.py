#!/usr/bin/env python3
"""ViaUnix Manager - Backend + API de provisionamento, agente e painel web.

- Armazena maquinas, comandos e auditoria no PostgreSQL.
- Criptografa senhas (adm-* e root) em AES-256-GCM usando chave mestra fora do banco.
- Login do painel: API Jupiter (restrito a ADMIN_USERS) + conta admin local de emergencia.
- Mantem compatibilidade total com POST /api/provision do viaunix-provision.
"""

import base64
import datetime
import hashlib
import hmac
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
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

CONF_PATH = os.environ.get("VIAUNIX_MANAGER_CONF", "/etc/viaunix/manager.conf")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
COOKIE_NAME = "viaunix_session"
SESSION_TTL = 8 * 3600  # 8 horas


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
        "MESHCENTRAL_URL": "https://172.16.152.2:8090",
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


def require_admin(request: Request) -> str:
    user = parse_session_cookie(request.cookies.get(COOKIE_NAME))
    if not user:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    return user


app = FastAPI(title="ViaUnix Manager", docs_url=None, redoc_url=None)


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


ALLOWED_ACTIONS = {"reboot", "shutdown", "apt_upgrade", "lock_screen", "rotate_password", "shell"}


# --- Rotas publicas / saude / UI ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# --- Autenticacao do Painel Web ---
@app.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    user = body.usuario.strip()
    pw = body.senha
    if not user or not pw:
        raise HTTPException(status_code=400, detail="Informe usuario e senha")

    ok = False
    method = ""

    # 1. Conta admin local de emergencia
    if user == CFG["LOCAL_ADMIN_USER"] and verify_scrypt_hash(pw, CFG["LOCAL_ADMIN_HASH"]):
        ok = True
        method = "local"
    else:
        # 2. API Jupiter (somente usuarios autorizados em ADMIN_USERS)
        allowed = {u.strip().lower() for u in CFG.get("ADMIN_USERS", "").split(",") if u.strip()}
        if user.lower() in allowed and verify_jupiter_api(user, pw):
            ok = True
            method = "jupiter_api"

    with db_conn() as conn:
        with conn.cursor() as cur:
            if not ok:
                add_audit(cur, user, "login_failed", "", client_ip(request), "credenciais invalidas ou sem permissao")
                raise HTTPException(status_code=401, detail="Usuario ou senha invalidos (ou sem permissao de TI)")
            add_audit(cur, user, "login", "", client_ip(request), f"via {method}")

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
    return {"usuario": admin, "meshcentral_url": CFG.get("MESHCENTRAL_URL", "")}


# --- Provisionamento (compativel com viaunix-provision) ---
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
                SET ip_origem=%s, ip_local=%s, logged_user=%s, os_version=%s,
                    cpu_percent=%s, mem_percent=%s, disk_percent=%s, uptime_sec=%s,
                    last_seen=NOW()
                WHERE id=%s
                """,
                (
                    client_ip(request),
                    body.ip_local[:64],
                    body.logged_user[:64],
                    body.os_version[:128],
                    body.cpu_percent,
                    body.mem_percent,
                    body.disk_percent,
                    body.uptime_sec,
                    m["id"],
                ),
            )
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
            if cmd:
                cur.execute("UPDATE commands SET status='running' WHERE id=%s", (cmd["id"],))
                return {"ok": True, "command": {"id": cmd["id"], "action": cmd["action"], "payload": cmd["payload"], "usuario": m["usuario"]}}
    return {"ok": True, "command": None}


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
                SELECT id, hostname, usuario, mac, serial, ip_origem, ip_local,
                       logged_user, os_version, cpu_percent, mem_percent, disk_percent,
                       uptime_sec, last_seen, instalado_em, created_at
                FROM machines
                ORDER BY last_seen DESC NULLS LAST, id DESC
            """)
            rows = cur.fetchall()

    out = []
    for r in rows:
        ls = r["last_seen"]
        online = bool(ls and (now - ls).total_seconds() <= 90)
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
            cur.execute("SELECT id, actor, action, target_hostname, ip, details, created_at FROM audit_log ORDER BY id DESC LIMIT 100")
            rows = cur.fetchall()
    for r in rows:
        r["created_at"] = r["created_at"].isoformat() if r["created_at"] else None
    return {"audit": rows}
