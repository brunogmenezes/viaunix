#!/usr/bin/env python3
"""Migra maquinas existentes de /var/lib/viaunix-provision/maquinas.jsonl para o PostgreSQL
com senhas criptografadas (AES-256-GCM) e remove os arquivos em texto puro."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as mgr  # noqa: E402

JSONL_PATH = "/var/lib/viaunix-provision/maquinas.jsonl"
CSV_PATH = "/var/lib/viaunix-provision/maquinas.csv"


def main() -> None:
    mgr.init_db()
    if not os.path.isfile(JSONL_PATH):
        print("Nenhum maquinas.jsonl antigo para migrar.")
        return

    imported = 0
    with mgr.db_conn() as conn:
        with conn.cursor() as cur:
            with open(JSONL_PATH, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    hostname = str(rec.get("hostname", "")).strip()
                    usuario = str(rec.get("usuario", "")).strip()
                    senha = str(rec.get("senha", "")).strip()
                    if not hostname or not usuario or not senha:
                        continue
                    cur.execute("SELECT 1 FROM machines WHERE hostname=%s OR usuario=%s", (hostname, usuario))
                    if cur.fetchone():
                        continue
                    cur.execute(
                        """
                        INSERT INTO machines (
                            hostname, usuario, senha_enc, root_senha_enc,
                            mac, serial, ip_origem, instalado_em
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            hostname,
                            usuario,
                            mgr.encrypt_secret(senha),
                            mgr.encrypt_secret(str(rec.get("root_senha", "")).strip()),
                            str(rec.get("mac", "")).strip(),
                            str(rec.get("serial", "")).strip(),
                            str(rec.get("ip_origem", "")).strip(),
                            str(rec.get("instalado_em", "")).strip(),
                        ),
                    )
                    imported += 1

    # Remove arquivos em texto puro apos migracao bem-sucedida
    for p in (JSONL_PATH, CSV_PATH):
        if os.path.isfile(p):
            os.remove(p)

    print(f"Migracao concluida: {imported} maquina(s) importada(s) com senhas criptografadas; arquivos texto puro removidos.")


if __name__ == "__main__":
    main()
