"""Base repository with shared Supabase client."""
from supabase import Client


class BaseRepository:
    """Base class for all repositories."""
    
    def __init__(self, client: Client):
        self.client = client

