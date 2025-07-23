"""
FUSE - (python dev tool) - Web App
api/processes.py - Processes API
"""



from fastapi import APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from python_dev_tool.web.models.process import ProcessStatus,  ProcessCreate, ProcessUpdate
from python_dev_tool.web.services.process_service import ProcessMetrics, ProcessService, get_process_service


logger = logging.getLogger(__name__)
router = APIRouter()

class ProcessResponse(BaseModel):
    """Response model for process data"""
    id: str
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    cwd: str
    env: Dict[str, str] = Field(default_factory=dict)
    status: ProcessStatus
    pid: Optional[int] = None
    project_id: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    metrics: Optional[ProcessMetrics] = None

class ProcessListResponse(BaseModel):
    """Response model for process list"""
    processes: List[ProcessResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class ProcessActionRequest(BaseModel):
    """Request model for process actions"""
    action: str = Field(..., description="Action to perform (start, stop, restart, kill)")
    force: bool = Field(False, description="Force action even if process is in invalid state")

@router.get("/", response_model=ProcessListResponse)
async def list_processes(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[ProcessStatus] = Query(None, description="Filter by status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    search: Optional[str] = Query(None, description="Search processes by name"),
    process_service: ProcessService = Depends(get_process_service)
):
    """List all processes with pagination and filtering"""
    try:
        result = await process_service.list_processes(
            page=page,
            per_page=per_page,
            status=status,
            project_id=project_id,
            search=search
        )

        return ProcessListResponse(
            processes=[ProcessResponse(**process.dict()) for process in result["processes"]],
            total=result["total"],
            page=page,
            per_page=per_page,
            has_next=result["has_next"],
            has_prev=result["has_prev"]
        )
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        raise HTTPException(status_code=500, detail="Failed to list processes")

@router.post("/", response_model=ProcessResponse, status_code=201)
async def create_process(
    process_data: ProcessCreate,
    background_tasks: BackgroundTasks,
    process_service: ProcessService = Depends(get_process_service)
):
    """Create a new process"""
    try:
        process = await process_service.create_process(process_data)

        # Optionally auto-start the process
        if process_data.auto_start:
            background_tasks.add_task(process_service.start_process, process.id)

        return ProcessResponse(**process.dict())
    except ValueError as e:
        logger.error(f"Invalid process data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating process: {e}")
        raise HTTPException(status_code=500, detail="Failed to create process")

@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get a specific process by ID"""
    try:
        process = await process_service.get_process(process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        return ProcessResponse(**process.dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get process")

@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(
    process_data: ProcessUpdate,
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Update a process"""
    try:
        process = await process_service.update_process(process_id, process_data)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        return ProcessResponse(**process.dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid process data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating process {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update process")

@router.delete("/{process_id}", status_code=204)
async def delete_process(
    process_id: str = Path(..., description="Process ID"),
    force: bool = Query(False, description="Force delete even if process is running"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Delete a process"""
    try:
        success = await process_service.delete_process(process_id, force=force)
        if not success:
            raise HTTPException(status_code=404, detail="Process not found")
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Cannot delete process: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting process {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete process")

@router.post("/{process_id}/action", response_model=ProcessResponse)
async def process_action(
    action_request: ProcessActionRequest,
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Perform an action on a process"""
    try:
        action = action_request.action.lower()

        if action == "start":
            process = await process_service.start_process(process_id)
        elif action == "stop":
            process = await process_service.stop_process(process_id, force=action_request.force)
        elif action == "restart":
            process = await process_service.restart_process(process_id)
        elif action == "kill":
            process = await process_service.kill_process(process_id)
        else:
            raise ValueError(f"Unknown action: {action}")

        if not process:
            raise HTTPException(status_code=404, detail="Process not found")

        return ProcessResponse(**process.dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid action: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error performing action {action_request.action} on process {process_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to {action_request.action} process")

@router.get("/{process_id}/status")
async def get_process_status(
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get detailed process status"""
    try:
        status = await process_service.get_process_status(process_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process status {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get process status")

@router.get("/{process_id}/metrics")
async def get_process_metrics(
    process_id: str = Path(..., description="Process ID"),
    period: str = Query("1h", description="Time period for metrics (1m, 5m, 1h, 1d)"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get process performance metrics"""
    try:
        metrics = await process_service.get_process_metrics(process_id, period)
        if metrics is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process metrics {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get process metrics")

@router.get("/{process_id}/logs")
async def get_process_logs(
    process_id: str = Path(..., description="Process ID"),
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    log_type: str = Query("all", description="Type of logs (stdout, stderr, all)"),
    follow: bool = Query(False, description="Follow logs in real-time"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get process logs"""
    try:
        logs = await process_service.get_process_logs(
            process_id,
            lines=lines,
            log_type=log_type,
            follow=follow
        )
        if logs is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return {
            "process_id": process_id,
            "logs": logs,
            "lines": lines,
            "log_type": log_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process logs {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get process logs")

@router.post("/{process_id}/signal")
async def send_process_signal(
    process_id: str = Path(..., description="Process ID"),
    signal_name: str = Query(..., description="Signal name (SIGTERM, SIGKILL, SIGINT, etc.)"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Send a signal to a process"""
    try:
        result = await process_service.send_signal(process_id, signal_name)
        if result is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return {
            "process_id": process_id,
            "signal": signal_name,
            "sent": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid signal: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending signal {signal_name} to process {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send signal")

@router.get("/{process_id}/environment")
async def get_process_environment(
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get process environment variables"""
    try:
        env = await process_service.get_process_environment(process_id)
        if env is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return {"environment": env}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process environment {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get process environment")

@router.put("/{process_id}/environment")
async def update_process_environment(
    environment: Dict[str, str],
    process_id: str = Path(..., description="Process ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Update process environment variables"""
    try:
        updated_env = await process_service.update_process_environment(process_id, environment)
        if updated_env is None:
            raise HTTPException(status_code=404, detail="Process not found")

        return {"environment": updated_env}
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid environment data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating process environment {process_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update process environment")

@router.get("/project/{project_id}")
async def get_project_processes(
    project_id: str = Path(..., description="Project ID"),
    status: Optional[ProcessStatus] = Query(None, description="Filter by status"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Get all processes for a specific project"""
    try:
        processes = await process_service.get_project_processes(project_id, status=status)
        return {
            "project_id": project_id,
            "processes": [ProcessResponse(**process.dict()) for process in processes],
            "total": len(processes)
        }
    except Exception as e:
        logger.error(f"Error getting processes for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project processes")

@router.post("/project/{project_id}/action")
async def project_processes_action(
    action_request: ProcessActionRequest,
    project_id: str = Path(..., description="Project ID"),
    process_service: ProcessService = Depends(get_process_service)
):
    """Perform an action on all processes in a project"""
    try:
        result = await process_service.project_processes_action(
            project_id,
            action_request.action,
            force=action_request.force
        )

        return {
            "project_id": project_id,
            "action": action_request.action,
            "results": result,
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        logger.error(f"Invalid action: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error performing action {action_request.action} on project {project_id} processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to {action_request.action} project processes")

@router.get("/system/metrics")
async def get_system_metrics(
    process_service: ProcessService = Depends(get_process_service)
):
    """Get system-wide process metrics"""
    try:
        metrics = await process_service.get_system_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")
