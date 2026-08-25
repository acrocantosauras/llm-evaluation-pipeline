"""Security utilities for API key management.

Key design:
- Keys are 256-bit random values (`secrets.token_urlsafe(32)`), so a fast
  unsalted hash is appropriate: SHA-256 preimage resistance is sufficient —
  an attacker cannot run a meaningful dictionary/brute-force attack against
  2^256 of entropy. Slow password hashes (bcrypt/argon2) would add latency
  to every request without meaningful security gain here.
- Plaintext keys are shown exactly once at creation and never logged.
- Verification uses constant-time comparison to avoid timing oracles.
"""

import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    """Generate a secure API key. Returns the plaintext key (show once)."""
    return f"llm_eval_{secrets.token_urlsafe(32)}"


def key_prefix(key: str, length: int = 15) -> str:
    """Display prefix for a key — safe to show in listings/logs."""
    return key[:length] + "..."


def hash_api_key(key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash (constant-time comparison)."""
    return hmac.compare_digest(hash_api_key(key), key_hash)
