"""
FUSE - (python dev tool) - Web App
api/websocket.py - WebSocket API
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import logging
from datetime import datetime

from python_dev_tool.web.services.project_service import ProjectService, get_project_service
from python_dev_tool.web.services.process_service import ProcessService, get_process_service
from python_dev_tool.web.services.log_service import LogService, get_log_service


logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.project_subscribers: Dict[str, Set[str]] = {}
        self.process_subscribers: Dict[str, Set[str]] = {}
        self.log_subscribers: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """Disconnect a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Remove from all subscriptions
        for project_id, subscribers in self.project_subscribers.items():
            subscribers.discard(client_id)
        for process_id, subscribers in self.process_subscribers.items():
            subscribers.discard(client_id)
        for log_id, subscribers in self.log_subscribers.items():
            subscribers.discard(client_id)

        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast_to_project_subscribers(self, message: dict, project_id: str):
        """Broadcast message to all subscribers of a project"""
        if project_id in self.project_subscribers:
            for client_id in self.project_subscribers[project_id].copy():
                await self.send_personal_message(message, client_id)

    async def broadcast_to_process_subscribers(self, message: dict, process_id: str):
        """Broadcast message to all subscribers of a process"""
        if process_id in self.process_subscribers:
            for client_id in self.process_subscribers[process_id].copy():
                await self.send_personal_message(message, client_id)

    async def broadcast_to_log_subscribers(self, message: dict, log_id: str):
        """Broadcast message to all subscribers of logs"""
        if log_id in self.log_subscribers:
            for client_id in self.log_subscribers[log_id].copy():
                await self.send_personal_message(message, client_id)

    def subscribe_to_project(self, client_id: str, project_id: str):
        """Subscribe a client to project updates"""
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = set()
        self.project_subscribers[project_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to project {project_id}")

    def subscribe_to_process(self, client_id: str, process_id: str):
        """Subscribe a client to process updates"""
        if process_id not in self.process_subscribers:
            self.process_subscribers[process_id] = set()
        self.process_subscribers[process_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to process {process_id}")

    def subscribe_to_logs(self, client_id: str, log_id: str):
        """Subscribe a client to log updates"""
        if log_id not in self.log_subscribers:
            self.log_subscribers[log_id] = set()
        self.log_subscribers[log_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to logs {log_id}")

    def unsubscribe_from_project(self, client_id: str, project_id: str):
        """Unsubscribe a client from project updates"""
        if project_id in self.project_subscribers:
            self.project_subscribers[project_id].discard(client_id)
            logger.info(f"Client {client_id} unsubscribed from project {project_id}")

    def unsubscribe_from_process(self, client_id: str, process_id: str):
        """Unsubscribe a client from process updates"""
        if process_id in self.process_subscribers:
            self.process_subscribers[process_id].discard(client_id)
            logger.info(f"Client {client_id} unsubscribed from process {process_id}")

    def unsubscribe_from_logs(self, client_id: str, log_id: str):
        """Unsubscribe a client from log updates"""
        if log_id in self.log_subscribers:
            self.log_subscribers[log_id].discard(client_id)
            logger.info(f"Client {client_id} unsubscribed from logs {log_id}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/connect/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    project_service: ProjectService = Depends(get_project_service),
    process_service: ProcessService = Depends(get_process_service),
    log_service: LogService = Depends(get_log_service),
):
    """Main WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, client_id)

    try:
        # Send initial connection message
        await manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            await handle_websocket_message(
                message, client_id, project_service, process_service, log_service
            )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


async def handle_websocket_message(
    message: dict,
    client_id: str,
    project_service: ProjectService,
    process_service: ProcessService,
    log_service: LogService,
):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")

    if message_type == "subscribe":
        await handle_subscribe_message(message, client_id)
    elif message_type == "unsubscribe":
        await handle_unsubscribe_message(message, client_id)
    elif message_type == "project_action":
        await handle_project_action(message, client_id, project_service)
    elif message_type == "process_action":
        await handle_process_action(message, client_id, process_service)
    elif message_type == "logs_request":
        await handle_logs_request(message, client_id, log_service)
    elif message_type == "ping":
        await handle_ping(client_id)
    else:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )


async def handle_subscribe_message(message: dict, client_id: str):
    """Handle subscription messages"""
    subscription_type = message.get("subscription_type")
    resource_id = message.get("resource_id")

    if subscription_type == "project":
        manager.subscribe_to_project(client_id, resource_id)
    elif subscription_type == "process":
        manager.subscribe_to_process(client_id, resource_id)
    elif subscription_type == "logs":
        manager.subscribe_to_logs(client_id, resource_id)

    await manager.send_personal_message(
        {
            "type": "subscription_confirmed",
            "subscription_type": subscription_type,
            "resource_id": resource_id,
            "timestamp": datetime.now().isoformat(),
        },
        client_id,
    )


async def handle_unsubscribe_message(message: dict, client_id: str):
    """Handle unsubscription messages"""
    subscription_type = message.get("subscription_type")
    resource_id = message.get("resource_id")

    if subscription_type == "project":
        manager.unsubscribe_from_project(client_id, resource_id)
    elif subscription_type == "process":
        manager.unsubscribe_from_process(client_id, resource_id)
    elif subscription_type == "logs":
        manager.unsubscribe_from_logs(client_id, resource_id)

    await manager.send_personal_message(
        {
            "type": "unsubscription_confirmed",
            "subscription_type": subscription_type,
            "resource_id": resource_id,
            "timestamp": datetime.now().isoformat(),
        },
        client_id,
    )


async def handle_project_action(
    message: dict, client_id: str, project_service: ProjectService
):
    """Handle project action messages"""
    action = message.get("action")
    project_id = message.get("project_id")

    try:
        if action == "start":
            result = await project_service.start_project(project_id)
        elif action == "stop":
            result = await project_service.stop_project(project_id)
        elif action == "restart":
            result = await project_service.restart_project(project_id)
        else:
            raise ValueError(f"Unknown action: {action}")

        # Broadcast to all project subscribers
        await manager.broadcast_to_project_subscribers(
            {
                "type": "project_updated",
                "project_id": project_id,
                "action": action,
                "result": result.dict() if result else None,
                "timestamp": datetime.now().isoformat(),
            },
            project_id,
        )

    except Exception as e:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": f"Failed to {action} project: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )


async def handle_process_action(
    message: dict, client_id: str, process_service: ProcessService
):
    """Handle process action messages"""
    action = message.get("action")
    process_id = message.get("process_id")

    try:
        if action == "start":
            result = await process_service.start_process(process_id)
        elif action == "stop":
            result = await process_service.stop_process(process_id)
        elif action == "restart":
            result = await process_service.restart_process(process_id)
        else:
            raise ValueError(f"Unknown action: {action}")

        # Broadcast to all process subscribers
        await manager.broadcast_to_process_subscribers(
            {
                "type": "process_updated",
                "process_id": process_id,
                "action": action,
                "result": result.dict() if result else None,
                "timestamp": datetime.now().isoformat(),
            },
            process_id,
        )

    except Exception as e:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": f"Failed to {action} process: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

async def handle_logs_request(message: dict, client_id: str, log_service: LogService):
    """Handle logs request messages"""
    log_type = message.get("log_type", "all")
    project_id = message.get("project_id")
    process_id = message.get("process_id")
    lines = message.get("lines", 100)

    try:
        logs = await log_service.get_logs(
            project_id=project_id, process_id=process_id, log_type=log_type, lines=lines
        )

        await manager.send_personal_message(
            {
                "type": "logs_response",
                "logs": logs,
                "project_id": project_id,
                "process_id": process_id,
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )

    except Exception as e:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": f"Failed to get logs: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            },
            client_id,
        )


async def handle_ping(client_id: str):
    """Handle ping messages"""
    await manager.send_personal_message(
        {"type": "pong", "timestamp": datetime.now().isoformat()}, client_id
    )


# Event handlers for broadcasting updates
async def broadcast_project_update(project_id: str, update_data: dict):
    """Broadcast project updates to subscribers"""
    await manager.broadcast_to_project_subscribers(
        {
            "type": "project_update",
            "project_id": project_id,
            "data": update_data,
            "timestamp": datetime.now().isoformat(),
        },
        project_id,
    )


async def broadcast_process_update(process_id: str, update_data: dict):
    """Broadcast process updates to subscribers"""
    await manager.broadcast_to_process_subscribers(
        {
            "type": "process_update",
            "process_id": process_id,
            "data": update_data,
            "timestamp": datetime.now().isoformat(),
        },
        process_id,
    )


async def broadcast_log_update(log_id: str, log_data: dict):
    """Broadcast log updates to subscribers"""
    await manager.broadcast_to_log_subscribers(
        {
            "type": "log_update",
            "log_id": log_id,
            "data": log_data,
            "timestamp": datetime.now().isoformat(),
        },
        log_id,
    )


# Real-time log streaming
@router.websocket("/logs/{project_id}")
async def logs_websocket(
    websocket: WebSocket,
    project_id: str,
    log_service: LogService = Depends(get_log_service),
):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()

    try:
        # Start log streaming
        async for log_entry in log_service.stream_logs(project_id):
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "log_entry",
                        "project_id": project_id,
                        "entry": log_entry,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except WebSocketDisconnect:
        logger.info(f"Log streaming disconnected for project {project_id}")
    except Exception as e:
        logger.error(f"Error in log streaming for project {project_id}: {e}")
        await websocket.close()


# Process monitoring WebSocket
@router.websocket("/processes/{process_id}/monitor")
async def process_monitor_websocket(
    websocket: WebSocket,
    process_id: str,
    process_service: ProcessService = Depends(get_process_service),
):
    """WebSocket endpoint for real-time process monitoring"""
    await websocket.accept()

    try:
        # Start process monitoring
        async for metrics in process_service.stream_metrics(process_id):
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "process_metrics",
                        "process_id": process_id,
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except WebSocketDisconnect:
        logger.info(f"Process monitoring disconnected for process {process_id}")
    except Exception as e:
        logger.error(f"Error in process monitoring for process {process_id}: {e}")
        await websocket.close()


# System metrics WebSocket
@router.websocket("/system/metrics")
async def system_metrics_websocket(
    websocket: WebSocket, process_service: ProcessService = Depends(get_process_service)
):
    """WebSocket endpoint for real-time system metrics"""
    await websocket.accept()

    try:
        # Start system metrics streaming
        async for metrics in process_service.stream_system_metrics():
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "system_metrics",
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except WebSocketDisconnect:
        logger.info("System metrics streaming disconnected")
    except Exception as e:
        logger.error(f"Error in system metrics streaming: {e}")
        await websocket.close()
