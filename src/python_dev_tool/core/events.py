"""
FUSE - (python dev tool) - Core Events
events.py - Event System Infrastructure
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Callable, Optional, Union
from uuid import uuid4
import threading
import json
from concurrent.futures import ThreadPoolExecutor


class EventType(Enum):
    """Standard event types"""

    # File system events
    FILE_CHANGED = "file_changed"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    FILE_MOVED = "file_moved"

    # Process events
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    PROCESS_CRASHED = "process_crashed"
    PROCESS_RESTARTED = "process_restarted"

    # Server events
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    SERVER_RELOAD = "server_reload"

    # Deployment events
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"

    # Configuration events
    CONFIG_CHANGED = "config_changed"
    CONFIG_LOADED = "config_loaded"

    # Framework events
    FRAMEWORK_DETECTED = "framework_detected"
    FRAMEWORK_CHANGED = "framework_changed"

    # Plugin events
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ERROR = "plugin_error"

    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """Event data structure"""

    type: Union[EventType, str]
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "event_id": self.event_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())


class EventHandler:
    """Base event handler class"""

    def __init__(self, handler: Callable, priority: int = 0, once: bool = False):
        self.handler = handler
        self.priority = priority
        self.once = once
        self.call_count = 0
        self.is_async = asyncio.iscoroutinefunction(handler)
        self.handler_id = str(uuid4())

    async def call(self, event: Event):
        """Call the handler with the event"""
        try:
            self.call_count += 1

            if self.is_async:
                return await self.handler(event)
            else:
                return self.handler(event)
        except Exception as e:
            print(f"Error in event handler {self.handler_id}: {e}")
            raise

    def __str__(self):
        return f"EventHandler(id={self.handler_id}, priority={self.priority}, once={self.once})"


class EventBus:
    """Event bus for communication between components"""

    def __init__(self, max_workers: int = 10):
        self.listeners: Dict[str, List[EventHandler]] = defaultdict(list)
        self.middleware: List[Callable] = []
        self.event_history: List[Event] = []
        self.max_history = 1000
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.stats = {"events_published": 0, "events_processed": 0, "handler_errors": 0}

    def subscribe(
        self,
        event_type: Union[EventType, str, List[Union[EventType, str]]],
        handler: Callable,
        priority: int = 0,
        once: bool = False,
    ) -> str:
        """Subscribe to events"""
        if isinstance(event_type, list):
            handler_ids = []
            for et in event_type:
                handler_ids.append(self.subscribe(et, handler, priority, once))
            return handler_ids

        event_key = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        event_handler = EventHandler(handler, priority, once)

        with self.lock:
            self.listeners[event_key].append(event_handler)
            # Sort by priority (higher priority first)
            self.listeners[event_key].sort(key=lambda h: h.priority, reverse=True)

        return event_handler.handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe handler by ID"""
        with self.lock:
            for event_type, handlers in self.listeners.items():
                for handler in handlers[:]:
                    if handler.handler_id == handler_id:
                        handlers.remove(handler)
                        return True
        return False

    def unsubscribe_all(self, event_type: Union[EventType, str]):
        """Unsubscribe all handlers for event type"""
        event_key = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        with self.lock:
            self.listeners[event_key].clear()

    def add_middleware(self, middleware: Callable):
        """Add middleware that processes events before handlers"""
        self.middleware.append(middleware)

    def remove_middleware(self, middleware: Callable):
        """Remove middleware"""
        if middleware in self.middleware:
            self.middleware.remove(middleware)

    async def publish(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any] = None,
        source: str = "unknown",
        metadata: Dict[str, Any] = None,
    ) -> Event:
        """Publish event asynchronously"""
        event = Event(
            type=event_type, data=data or {}, source=source, metadata=metadata or {}
        )

        return await self.publish_event(event)

    async def publish_event(self, event: Event) -> Event:
        """Publish event object"""
        # Update stats
        self.stats["events_published"] += 1

        # Add to history
        self._add_to_history(event)

        # Process middleware
        for middleware in self.middleware:
            try:
                if asyncio.iscoroutinefunction(middleware):
                    event = await middleware(event)
                else:
                    event = middleware(event)

                if event is None:
                    return  # Middleware blocked the event
            except Exception as e:
                print(f"Error in middleware: {e}")
                continue

        # Get handlers for this event type
        event_key = (
            event.type.value if isinstance(event.type, EventType) else event.type
        )
        handlers = self.listeners.get(event_key, [])

        # Process handlers
        tasks = []
        handlers_to_remove = []

        for handler in handlers:
            try:
                task = asyncio.create_task(handler.call(event))
                tasks.append(task)

                # Mark for removal if it's a one-time handler
                if handler.once:
                    handlers_to_remove.append(handler)

            except Exception as e:
                self.stats["handler_errors"] += 1
                print(f"Error creating task for handler {handler.handler_id}: {e}")

        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Remove one-time handlers
        if handlers_to_remove:
            with self.lock:
                for handler in handlers_to_remove:
                    if handler in self.listeners[event_key]:
                        self.listeners[event_key].remove(handler)

        self.stats["events_processed"] += 1
        return event

    def publish_sync(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any] = None,
        source: str = "unknown",
        metadata: Dict[str, Any] = None,
    ) -> Event:
        """Publish event synchronously"""
        event = Event(
            type=event_type, data=data or {}, source=source, metadata=metadata or {}
        )

        # For sync publishing, we create a new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.publish_event(event))

    def _add_to_history(self, event: Event):
        """Add event to history"""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

    def get_event_history(
        self, event_type: Optional[Union[EventType, str]] = None, limit: int = 100
    ) -> List[Event]:
        """Get event history"""
        events = self.event_history

        if event_type:
            event_key = (
                event_type.value if isinstance(event_type, EventType) else event_type
            )
            events = [e for e in events if e.type == event_key]

        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self.stats,
            "active_listeners": sum(
                len(handlers) for handlers in self.listeners.values()
            ),
            "event_types": list(self.listeners.keys()),
            "middleware_count": len(self.middleware),
            "history_size": len(self.event_history),
        }

    def clear_history(self):
        """Clear event history"""
        self.event_history.clear()

    def shutdown(self):
        """Shutdown event bus"""
        self.executor.shutdown(wait=True)
        self.listeners.clear()
        self.middleware.clear()
        self.event_history.clear()


class EventEmitter:
    """Mixin class for objects that emit events"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus or get_global_event_bus()
        self.source_name = self.__class__.__name__

    async def emit(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> Event:
        """Emit an event"""
        return await self.event_bus.publish(
            event_type=event_type,
            data=data or {},
            source=self.source_name,
            metadata=metadata or {},
        )

    def emit_sync(
        self,
        event_type: Union[EventType, str],
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> Event:
        """Emit an event synchronously"""
        return self.event_bus.publish_sync(
            event_type=event_type,
            data=data or {},
            source=self.source_name,
            metadata=metadata or {},
        )

    def subscribe(
        self,
        event_type: Union[EventType, str],
        handler: Callable,
        priority: int = 0,
        once: bool = False,
    ) -> str:
        """Subscribe to events"""
        return self.event_bus.subscribe(event_type, handler, priority, once)

    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe from events"""
        return self.event_bus.unsubscribe(handler_id)


# Global event bus instance
_global_event_bus = None


def get_global_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_global_event_bus(event_bus: EventBus):
    """Set the global event bus instance"""
    global _global_event_bus
    _global_event_bus = event_bus


# Convenience functions
async def emit_event(
    event_type: Union[EventType, str],
    data: Dict[str, Any] = None,
    source: str = "global",
    metadata: Dict[str, Any] = None,
) -> Event:
    """Emit event using global event bus"""
    return await get_global_event_bus().publish(event_type, data, source, metadata)


def emit_event_sync(
    event_type: Union[EventType, str],
    data: Dict[str, Any] = None,
    source: str = "global",
    metadata: Dict[str, Any] = None,
) -> Event:
    """Emit event synchronously using global event bus"""
    return get_global_event_bus().publish_sync(event_type, data, source, metadata)


def subscribe_to_event(
    event_type: Union[EventType, str],
    handler: Callable,
    priority: int = 0,
    once: bool = False,
) -> str:
    """Subscribe to event using global event bus"""
    return get_global_event_bus().subscribe(event_type, handler, priority, once)


def unsubscribe_from_event(handler_id: str) -> bool:
    """Unsubscribe from event using global event bus"""
    return get_global_event_bus().unsubscribe(handler_id)


# Decorator for event handlers
def event_handler(
    event_type: Union[EventType, str], priority: int = 0, once: bool = False
):
    """Decorator for event handlers"""

    def decorator(func):
        handler_id = subscribe_to_event(event_type, func, priority, once)
        func.handler_id = handler_id
        return func

    return decorator


# Context manager for temporary event subscriptions
class EventSubscription:
    """Context manager for temporary event subscriptions"""

    def __init__(
        self,
        event_type: Union[EventType, str],
        handler: Callable,
        priority: int = 0,
        once: bool = False,
        event_bus: EventBus = None,
    ):
        self.event_bus = event_bus or get_global_event_bus()
        self.handler_id = None
        self.event_type = event_type
        self.handler = handler
        self.priority = priority
        self.once = once

    def __enter__(self):
        self.handler_id = self.event_bus.subscribe(
            self.event_type, self.handler, self.priority, self.once
        )
        return self.handler_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler_id:
            self.event_bus.unsubscribe(self.handler_id)
