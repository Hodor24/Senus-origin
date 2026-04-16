from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def encrypt_data(data: bytes, key: str) -> str:
    key_bytes = hashlib.sha256(key.encode("utf-8")).digest()
    encrypted = _xor_cipher(data, key_bytes)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_data(cipher_text_b64: str, key: str) -> bytes:
    key_bytes = hashlib.sha256(key.encode("utf-8")).digest()
    encrypted = base64.b64decode(cipher_text_b64.encode("ascii"))
    return _xor_cipher(encrypted, key_bytes)


@dataclass(slots=True)
class AccessControl:
    user_roles: dict[str, str] = field(default_factory=dict)

    def can_read(self, user_id: str) -> bool:
        return self.user_roles.get(user_id) in {"owner", "researcher", "reviewer"}

    def can_write(self, user_id: str) -> bool:
        return self.user_roles.get(user_id) in {"owner", "researcher"}


@dataclass(slots=True)
class AuditLog:
    entries: list[dict[str, Any]] = field(default_factory=list)
    secret: str = "audit-secret"

    def append(self, actor: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        prev_hash = self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
        body = {"timestamp": _now_iso(), "actor": actor, "action": action, "payload": payload, "prev_hash": prev_hash}
        digest = hmac.new(self.secret.encode("utf-8"), json.dumps(body, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
        entry = {**body, "entry_hash": digest}
        self.entries.append(entry)
        return entry
