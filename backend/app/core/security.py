"""
Password hashing utilities for H.I.R.E.

Uses the bcrypt library directly (bcrypt>=4.0 API) rather than going
through passlib, which is incompatible with bcrypt 5.x (the version
pinned in requirements.txt).

All password handling is centralised here so no route or service
needs to import bcrypt directly.
"""

import bcrypt


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*.  Never store or log *plain*."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True iff *plain* matches *hashed*.  Constant-time compare."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
