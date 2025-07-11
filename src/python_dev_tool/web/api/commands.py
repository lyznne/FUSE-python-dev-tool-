"""
FUSE - (python dev tool) - Web App
api/commands.py - Commands API
"""
import logging
import asyncio
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


from python_dev_tool.web.services.project_service import ProjectService, get_project_service
from python_dev_tool.web.services.process_service import ProcessService, get_process_service

logger = logging.getLogger(__name__)
router = APIRouter()

class CommandStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CommandExecution(BaseModel):
    """Model for command execution"""
    id: str
    command: str
    args: List[str] = Field(default_factory=list)
    cwd: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)
    project_id: Optional[str] = None
    status: CommandStatus = CommandStatus.PENDING
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: Optional[int] = None

class CommandRequest(BaseModel):
    """Request model for command execution"""
    command: str = Field(..., description="Command to execute")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    cwd: Optional[str] = Field(None, description="Working directory")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    project_id: Optional[str] = Field(None, description="Project ID")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    async_execution: bool = Field(False, description="Execute asynchronously")

class CommandResponse(BaseModel):
    """Response model for command execution"""
    id: str
    command: str
    args: List[str]
    cwd: Optional[str]
    project_id: Optional[str]
    status: CommandStatus
    exit_code: Optional[int]
    stdout: str
    stderr: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration: Optional[float] = None

class CommandListResponse(BaseModel):
    """Response model for command list"""
    commands: List[CommandResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

class CommandTemplate(BaseModel):
    """Model for command templates"""
    id: str
    name: str
    description: str
    command: str
    args: List[str] = Field(default_factory=list)
    framework: Optional[str] = None
    category: str = "general"
    variables: Dict[str, str] = Field(default_factory=dict)

# In-memory storage for command executions (in production, use a database)
command_executions: Dict[str, CommandExecution] = {}

@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    command_request: CommandRequest,
    background_tasks: BackgroundTasks,
    project_service: ProjectService = Depends(get_project_service),
    process_service: ProcessService = Depends(get_process_service)
):
    """Execute a command"""
    try:
        # Create command execution record
        execution_id = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(command_executions)}"
        execution = CommandExecution(
            id=execution_id,
            command=command_request.command,
            args=command_request.args,
            cwd=command_request.cwd,
            env=command_request.env,
            project_id=command_request.project_id,
            timeout=command_request.timeout
        )

        command_executions[execution_id] = execution

        if command_request.async_execution:
            # Execute in background
            background_tasks.add_task(
                _execute_command_async,
                execution_id,
                command_request,
                process_service
            )

            return CommandResponse(
                id=execution.id,
                command=execution.command,
                args=execution.args,
                cwd=execution.cwd,
                project_id=execution.project_id,
                status=execution.status,
                exit_code=execution.exit_code,
                stdout=execution.stdout,
                stderr=execution.stderr,
                created_at=execution.created_at,
                started_at=execution.started_at,
                completed_at=execution.completed_at
            )
        else:
            # Execute synchronously
            result = await _execute_command_sync(execution_id, command_request, process_service)
            return result

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute command")

async def _execute_command_sync(
    execution_id: str,
    command_request: CommandRequest,
    process_service: ProcessService
) -> CommandResponse:
    """Execute command synchronously"""
    execution = command_executions[execution_id]

    try:
        execution.status = CommandStatus.RUNNING
        execution.started_at = datetime.now()

        # Build full command
        full_command = [command_request.command] + command_request.args

        # Execute command
        result = await process_service.execute_command(
            command=full_command,
            cwd=command_request.cwd,
            env=command_request.env,
            timeout=command_request.timeout
        )

        # Update execution record
        execution.exit_code = result.get("exit_code", 0)
        execution.stdout = result.get("stdout", "")
        execution.stderr = result.get("stderr", "")
        execution.completed_at = datetime.now()

        if execution.exit_code == 0:
            execution.status = CommandStatus.COMPLETED
        else:
            execution.status = CommandStatus.FAILED

    except asyncio.TimeoutError:
        execution.status = CommandStatus.FAILED
        execution.stderr = "Command timed out"
        execution.completed_at = datetime.now()
    except Exception as e:
        execution.status = CommandStatus.FAILED
        execution.stderr = str(e)
        execution.completed_at = datetime.now()

    # Calculate duration
    duration = None
    if execution.started_at and execution.completed_at:
        duration = (execution.completed_at - execution.started_at).total_seconds()

    return CommandResponse(
        id=execution.id,
        command=execution.command,
        args=execution.args,
        cwd=execution.cwd,
        project_id=execution.project_id,
        status=execution.status,
        exit_code=execution.exit_code,
        stdout=execution.stdout,
        stderr=execution.stderr,
        created_at=execution.created_at,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        duration=duration
    )

async def _execute_command_async(
    execution_id: str,
    command_request: CommandRequest,
    process_service: ProcessService
):
    """Execute command asynchronously"""
    try:
        await _execute_command_sync(execution_id, command_request, process_service)
    except Exception as e:
        logger.error(f"Error in async command execution {execution_id}: {e}")
        execution = command_executions.get(execution_id)
        if execution:
            execution.status = CommandStatus.FAILED
            execution.stderr = str(e)
            execution.completed_at = datetime.now()

@router.get("/", response_model=CommandListResponse)
async def list_commands(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[CommandStatus] = Query(None, description="Filter by status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    search: Optional[str] = Query(None, description="Search commands")
):
    """List command executions with pagination and filtering"""
    try:
        # Filter commands
        filtered_commands = []
        for cmd in command_executions.values():
            if status and cmd.status != status:
                continue
            if project_id and cmd.project_id != project_id:
                continue
            if search and search.lower() not in cmd.command.lower():
                continue
            filtered_commands.append(cmd)

        # Sort by created_at descending
        filtered_commands.sort(key=lambda x: x.created_at, reverse=True)

        # Paginate
        total = len(filtered_commands)
        start = (page - 1) * per_page
        end = start + per_page
        page_commands = filtered_commands[start:end]

        # Convert to response format
        command_responses = []
        for cmd in page_commands:
            duration = None
            if cmd.started_at and cmd.completed_at:
                duration = (cmd.completed_at - cmd.started_at).total_seconds()

            command_responses.append(CommandResponse(
                id=cmd.id,
                command=cmd.command,
                args=cmd.args,
                cwd=cmd.cwd,
                project_id=cmd.project_id,
                status=cmd.status,
                exit_code=cmd.exit_code,
                stdout=cmd.stdout,
                stderr=cmd.stderr,
                created_at=cmd.created_at,
                started_at=cmd.started_at,
                completed_at=cmd.completed_at,
                duration=duration
            ))

        return CommandListResponse(
            commands=command_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=end < total,
            has_prev=page > 1
            )

    except Exception as e:
        logger.error(f"Error listing commands: {e}")
        raise HTTPException(status_code=500, detail="Failed to list commands")
