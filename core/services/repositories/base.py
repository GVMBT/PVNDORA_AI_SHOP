"""Base repository with shared Supabase client."""
from typing import Union
from supabase import Client
from supabase._async.client import AsyncClient


class BaseRepository:
    """Base class for all repositories.
    
    Accepts either sync Client or AsyncClient.
    All methods should use await with the client.
    """
    
    def __init__(self, client: Union[Client, AsyncClient]):
        self.client = client

