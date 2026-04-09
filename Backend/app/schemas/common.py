from pydantic import BaseModel
from typing import Optional, Dict, Any

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    pages: int

class StatsResponse(BaseModel):
    total_users: int
    total_persons: int
    total_relationships: int
    total_events: int
    total_media: int

class SystemInfoResponse(BaseModel):
    version: str
    uptime_seconds: float
    database_status: str
    redis_status: str

class MessageResponse(BaseModel):
    message: str
    details: Optional[Dict[str, Any]] = None