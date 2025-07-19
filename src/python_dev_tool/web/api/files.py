"""
FUSE - (python dev tool) - Web App
api/files.py - File API
"""
from typing import List, Dict, Any
from pydantic import BaseModel


class FileResponse(BaseModel):
    """Response model for file data"""
    pass

class FileListResponse(BaseModel):
    """Response model for a list of files"""
    files: List[FileResponse]
    total: int
    page: int
    page_size: int
