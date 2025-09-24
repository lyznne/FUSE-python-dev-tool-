"""
FUSE - (python dev tool) - Web App
Project Models
"""

from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProjectCreate(BaseModel):
    """Project creation data"""

    pass


class ProjectUpdate(BaseModel):
    """Project update data"""

    pass


class ProjectStatus(str, Enum):
    """Project statuses"""

    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ProjectType(str, Enum):
    """Project types"""

    SERVER = "server"
    WEB = "web"


class Project:
    """Project data"""

    id: str
    name: str
    type: ProjectType
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    metrics: Optional[dict] = None


class ProjectResponse(BaseModel):
    """Response model for project data"""

    pass
