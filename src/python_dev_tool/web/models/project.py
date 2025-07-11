"""
FUSE - (python dev tool) - Web App
Project Models
"""


from enum import Enum
from pydantic import BaseModel


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
   1 8 9n
#
