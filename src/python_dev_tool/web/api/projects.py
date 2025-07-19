"""
FUSE - (python dev tool) - Web App
api/projects.py - Projects API
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from python_dev_tool.web.models.process import Process
from python_dev_tool.web.models.project import ProjectCreate, ProjectStatus, ProjectUpdate, ProjectResponse
from python_dev_tool.web.services.project_service import ProjectService,get_project_service




logger = logging.getLogger(__name__)
router = APIRouter()


class ProjectResponse(BaseModel):
    """Response model for project data"""

    id: str
    name: str
    path: str
    framework: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    config: Dict[str, Any] = Field(default_factory=dict)
    processes: List[Process] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectListResponse(BaseModel):
    """Response model for project list"""

    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    search: Optional[str] = Query(None, description="Search projects by name"),
    project_service: ProjectService = Depends(get_project_service),
):
    """List all projects with pagination and filtering"""
    try:
        result = await project_service.list_projects(
            page=page,
            per_page=per_page,
            status=status,
            framework=framework,
            search=search,
        )

        return ProjectListResponse(
            projects=[
                ProjectResponse(**project.dict()) for project in result["projects"]
            ],
            total=result["total"],
            page=page,
            per_page=per_page,
            has_next=result["has_next"],
            has_prev=result["has_prev"],
        )
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
):
    """Create a new project"""
    try:
        project = await project_service.create_project(project_data)
        return ProjectResponse(**project.dict())
    except ValueError as e:
        logger.error(f"Invalid project data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get a specific project by ID"""
    try:
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str = Path(..., description="Project ID"),
    project_data: ProjectUpdate = None,
    project_service: ProjectService = Depends(get_project_service),
):
    """Update a project"""
    try:
        project = await project_service.update_project(project_id, project_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project.dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid project data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str = Path(..., description="Project ID"),
    force: bool = Query(False, description="Force delete even if project is running"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Delete a project"""
    try:
        success = await project_service.delete_project(project_id, force=force)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Cannot delete project: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.post("/{project_id}/start", response_model=ProjectResponse)
async def start_project(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Start a project"""
    try:
        project = await project_service.start_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start project")


@router.post("/{project_id}/stop", response_model=ProjectResponse)
async def stop_project(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Stop a project"""
    try:
        project = await project_service.stop_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop project")


@router.post("/{project_id}/restart", response_model=ProjectResponse)
async def restart_project(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Restart a project"""
    try:
        project = await project_service.restart_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return ProjectResponse(**project.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to restart project")


@router.get("/{project_id}/config")
async def get_project_config(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get project configuration"""
    try:
        config = await project_service.get_project_config(project_id)
        if config is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"config": config}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project config {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project config")


@router.put("/{project_id}/config")
async def update_project_config(
    project_id: str = Path(..., description="Project ID"),
    config: Dict[str, Any] = {},
    project_service: ProjectService = Depends(get_project_service),
):
    """Update project configuration"""
    try:
        updated_config = await project_service.update_project_config(project_id, config)
        if updated_config is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"config": updated_config}
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid config data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating project config {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project config")


@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get detailed project status"""
    try:
        status = await project_service.get_project_status(project_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project status {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project status")


@router.post("/{project_id}/detect-framework")
async def detect_framework(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Detect and update project framework"""
    try:
        framework = await project_service.detect_framework(project_id)
        if framework is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"framework": framework}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting framework for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect framework")


@router.get("/{project_id}/metrics")
async def get_project_metrics(
    project_id: str = Path(..., description="Project ID"),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get project performance metrics"""
    try:
        metrics = await project_service.get_project_metrics(project_id)
        if metrics is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project metrics {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project metrics")
