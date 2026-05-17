"""Supabase client singleton — shared across all controllers."""

from __future__ import annotations

from supabase import Client, create_client

from app.core.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client
