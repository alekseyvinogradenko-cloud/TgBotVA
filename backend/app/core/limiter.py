"""Shared rate limiter (slowapi). In-memory storage — fine for a single
Render worker; switch to Redis storage_uri if scaling to multiple workers."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
