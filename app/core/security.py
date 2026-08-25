"""Security utilities for API key management."""

import hashlib
import secrets


def generate_api_key() -> str:
    """Generate a secure API key. Returns the plaintext key (show once)."""
    return f"llm_eval_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(key) == key_hash
