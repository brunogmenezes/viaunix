#!/usr/bin/env python3
"""ViaUnix - servidor receptor de credenciais de provisionamento.

Recebe POST /api/provision com JSON (hostname, usuario, senha, root_senha, mac, serial, instalado_em),
valida o token (X-ViaUnix-Token), garante unicidade de hostname/usuario (409 em colisao)
e salva em /var/lib/viaunix-provision/maquinas.jsonl e maquinas.csv (permissao 0600 root:root).
"""

import csv
import datetime
import hmac
import http.server
import json
import os
import threading

CONF_PATH = "/etc/viaunix/provision-server.conf"
DATA_DIR = "/var/lib/viaunix-provision"
JSONL_PATH = os.path.join(DATA_DIR, "maquinas.jsonl")
CSV_PATH = os.path.join(DATA_DIR, "maquinas.csv")
CSV_FIELDS = ["recebido_em", "ip_origem", "hostname", "usuario", "senha", "root_senha", "mac", "serial", "instalado_em"]

LOCK = threading.Lock()


def load_config() -> dict:
    cfg = {
        "BIND": "0.0.0.0",
        "PORT": "8088",
        "PROVISION_TOKEN": "viaunix-provision-alterar-em-producao",
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


def load_existing_keys() -> tuple[set, set]:
    hosts, users = set(), set()
    if not os.path.isfile(JSONL_PATH):
        return hosts, users
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("hostname"):
                    hosts.add(row["hostname"])
                if row.get("usuario"):
                    users.add(row["usuario"])
            except ValueError:
                continue
    return hosts, users


def append_record(record: dict) -> None:
    os.makedirs(DATA_DIR, mode=0o700, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)

    fd = os.open(JSONL_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    write_header = not os.path.isfile(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    fd_csv = os.open(CSV_PATH, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(record)


class ProvisionHandler(http.server.BaseHTTPRequestHandler):
    token = ""

    def _send(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok"})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/api/provision":
            self._send(404, {"error": "not_found"})
            return

        provided = self.headers.get("X-ViaUnix-Token", "")
        if not hmac.compare_digest(provided, self.token):
            self._send(403, {"error": "invalid_token"})
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > 16384:
            self._send(400, {"error": "invalid_body"})
            return

        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            self._send(400, {"error": "invalid_json"})
            return

        hostname = str(data.get("hostname", "")).strip()
        usuario = str(data.get("usuario", "")).strip()
        senha = str(data.get("senha", "")).strip()
        if not hostname or not usuario or not senha:
            self._send(400, {"error": "missing_fields"})
            return

        record = {
            "recebido_em": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),
            "ip_origem": self.client_address[0],
            "hostname": hostname,
            "usuario": usuario,
            "senha": senha,
            "root_senha": str(data.get("root_senha", "")).strip(),
            "mac": str(data.get("mac", "")).strip(),
            "serial": str(data.get("serial", "")).strip(),
            "instalado_em": str(data.get("instalado_em", "")).strip(),
        }

        with LOCK:
            hosts, users = load_existing_keys()
            if hostname in hosts or usuario in users:
                self._send(409, {"error": "duplicate_hostname_or_user"})
                return
            append_record(record)

        self._send(201, {"ok": True, "hostname": hostname, "usuario": usuario})

    def log_message(self, fmt: str, *args) -> None:
        # Nao registra corpo/senhas, apenas metodo, rota e status
        print(f"[viaunix-provision-server] {self.client_address[0]} - {fmt % args}", flush=True)


def main() -> None:
    cfg = load_config()
    ProvisionHandler.token = cfg["PROVISION_TOKEN"]
    host = cfg["BIND"]
    port = int(cfg["PORT"])
    server = http.server.ThreadingHTTPServer((host, port), ProvisionHandler)
    print(f"[viaunix-provision-server] ouvindo em http://{host}:{port}/api/provision", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
