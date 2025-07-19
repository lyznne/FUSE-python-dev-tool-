"""
FUSE - (python dev tool) - Web App
api/logs.py - Logs API
"""



from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from python_dev_tool.web.models.log import LogLevel, LogSource


class LogResponse(BaseModel):
    """Response model for log data"""
    id: str
    message: str
    level: LogLevel
    source: LogSource
    timestamp: datetime
    project_id: Optional[str]
    process_id: Optional[str]
    stack_trace: Optional[str]
    tags: List[str]
    structured_data: Dict[str, Any]

class LogListResponse(BaseModel):
    """Response model for a list of logs"""
    logs: List[LogResponse]
    total: int
    page: int
    page_size: int
