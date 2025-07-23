"""
FUSE - (python dev tool) - Web App
Process Models
"""


from enum import Enum
from pydantic import BaseModel



class ProcessStatus(str, Enum):
    """Process statuses"""
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class ProcessType(str, Enum):
    """Process types"""
    SERVER = "server"


class Process(BaseModel):
    """Process model for managing processes in the web application."""

    id: str
    name: str
    status: ProcessStatus
    command: str
    created_at: str
    updated_at: str


class ProcessCreate(BaseModel):
    """Model for creating a new process."""
    name: str
    command: str
    type: ProcessType = ProcessType.SERVER


class ProcessUpdate(BaseModel):
    """Model for updating an existing process."""
    name: str
    command: str
    status: ProcessStatus = ProcessStatus.CREATED
    type: ProcessType = ProcessType.SERVER
