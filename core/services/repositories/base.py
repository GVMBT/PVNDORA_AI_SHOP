"""Base repository with shared Supabase client."""

from supabase._async.client import AsyncClient

from supabase import Client


class BaseRepository:
    """Base class for all repositories.

    Accepts either sync Client or AsyncClient.
    All methods should use await with the client.
    """

    def __init__(self, client: Client | AsyncClient) -> None:
        self.client = client
