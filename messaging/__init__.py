"""
NEXUS Messaging Module
Provides message bus and agent registry functionality
"""

from .message_bus import (
    MessageBus,
    EnhancedAgentRegistry,
    get_message_bus,
    get_agent_registry,
    start_message_infrastructure,
    stop_message_infrastructure
)

__all__ = [
    'MessageBus',
    'EnhancedAgentRegistry', 
    'get_message_bus',
    'get_agent_registry',
    'start_message_infrastructure',
    'stop_message_infrastructure'
]
