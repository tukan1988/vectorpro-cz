#!/usr/bin/env python3
"""Encrypt GitHub token for site edit saving (password = titanic)."""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "vectorpro-cz" / "assets" / "gh-edit.json"
PASSWORD = "titanic"
OWNER = "tukan1988"
REPO = "vectorpro-cz"


def main() -> None:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography", "-q"])
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

    token = os.environ.get("VP_GITHUB_TOKEN", "").strip()
    if not token:
        p = ROOT / ".edit-github-token"
        if p.exists():
            token = p.read_text(encoding="utf-8").strip()
    if not token:
        print("Chybí token. Vytvořte .edit-github-token nebo nastavte VP_GITHUB_TOKEN.")
        print("Doporučeno: Fine-grained PAT s Contents: Write jen pro repo vectorpro-cz.")
        sys.exit(1)

    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=120000)
    key = kdf.derive(PASSWORD.encode("utf-8"))
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, token.encode("utf-8"), None)

    payload = {
        "owner": OWNER,
        "repo": REPO,
        "v": 1,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "data": base64.b64encode(ct).decode("ascii"),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Zapsáno {OUT}")


if __name__ == "__main__":
    main()
