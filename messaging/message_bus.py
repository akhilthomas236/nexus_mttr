"""
Enhanced Message Bus for NEXUS MVP
Provides reliable message routing and event handling between agents
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import asdict
from collections import defaultdict, deque

from models import AgentMessage, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    """
    Central message bus for agent communication
    Handles message routing, queuing, and event distribution
    """
    
    def __init__(self, max_queue_size: int = 1000, message_ttl_minutes: int = 60):
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))
        self.subscribers: Dict[MessageType, List[str]] = defaultdict(list)
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = defaultdict(dict)
        self.message_history: List[AgentMessage] = []
        self.message_ttl = timedelta(minutes=message_ttl_minutes)
        self.running = False
        self.stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'messages_dropped': 0
        }
    
    def register_agent(self, agent_id: str, agent: 'BaseAgent') -> None:
        """Register an agent with the message bus"""
        self.agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            # Clear message queue
            if agent_id in self.message_queues:
                del self.message_queues[agent_id]
            # Remove from subscribers
            for subscribers in self.subscribers.values():
                if agent_id in subscribers:
                    subscribers.remove(agent_id)
            logger.info(f"Unregistered agent: {agent_id}")
    
    def subscribe(self, agent_id: str, message_type: MessageType, handler: Optional[Callable] = None) -> None:
        """Subscribe an agent to a specific message type"""
        if agent_id not in self.subscribers[message_type]:
            self.subscribers[message_type].append(agent_id)
        
        if handler:
            self.message_handlers[agent_id][message_type] = handler
        
        logger.debug(f"Agent {agent_id} subscribed to {message_type}")
    
    def unsubscribe(self, agent_id: str, message_type: MessageType) -> None:
        """Unsubscribe an agent from a message type"""
        if agent_id in self.subscribers[message_type]:
            self.subscribers[message_type].remove(agent_id)
        
        if agent_id in self.message_handlers and message_type in self.message_handlers[agent_id]:
            del self.message_handlers[agent_id][message_type]
        
        logger.debug(f"Agent {agent_id} unsubscribed from {message_type}")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message to a specific recipient or broadcast"""
        try:
            self.stats['messages_sent'] += 1
            self.message_history.append(message)
            
            # Clean up old messages
            await self._cleanup_old_messages()
            
            if message.recipient_id == "broadcast" or message.recipient_id == "*":
                # Broadcast to all subscribers
                return await self._broadcast_message(message)
            else:
                # Send to specific recipient
                return await self._send_to_recipient(message)
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.stats['messages_failed'] += 1
            return False
    
    async def _send_to_recipient(self, message: AgentMessage) -> bool:
        """Send message to a specific recipient"""
        recipient_id = message.recipient_id
        
        if recipient_id not in self.agents:
            logger.warning(f"Recipient {recipient_id} not found")
            self.stats['messages_failed'] += 1
            return False
        
        # Add to recipient's queue
        self.message_queues[recipient_id].append(message)
        
        # Try to deliver immediately if agent has a handler
        if recipient_id in self.message_handlers:
            handler = self.message_handlers[recipient_id].get(message.message_type)
            if handler:
                try:
                    await handler(message)
                    self.stats['messages_delivered'] += 1
                    return True
                except Exception as e:
                    logger.error(f"Error in message handler for {recipient_id}: {e}")
        
        # Otherwise, let agent poll for messages
        self.stats['messages_delivered'] += 1
        return True
    
    async def _broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast message to all subscribers of the message type"""
        subscribers = self.subscribers.get(message.message_type, [])
        
        if not subscribers:
            logger.debug(f"No subscribers for message type {message.message_type}")
            return True
        
        success_count = 0
        
        for agent_id in subscribers:
            # Create a copy of the message for each recipient
            agent_message = AgentMessage(
                sender_id=message.sender_id,
                recipient_id=agent_id,
                message_type=message.message_type,
                data=message.data.copy() if message.data else {},
                timestamp=message.timestamp
            )
            
            if await self._send_to_recipient(agent_message):
                success_count += 1
        
        return success_count == len(subscribers)
    
    async def get_messages(self, agent_id: str, limit: int = 10) -> List[AgentMessage]:
        """Get pending messages for an agent"""
        if agent_id not in self.message_queues:
            return []
        
        messages = []
        queue = self.message_queues[agent_id]
        
        for _ in range(min(limit, len(queue))):
            if queue:
                messages.append(queue.popleft())
        
        return messages
    
    async def peek_messages(self, agent_id: str, limit: int = 10) -> List[AgentMessage]:
        """Peek at pending messages without removing them"""
        if agent_id not in self.message_queues:
            return []
        
        queue = self.message_queues[agent_id]
        return list(queue)[:limit]
    
    def get_queue_size(self, agent_id: str) -> int:
        """Get the number of pending messages for an agent"""
        return len(self.message_queues.get(agent_id, []))
    
    async def publish_event(self, event_type: MessageType, sender_id: str, data: Dict[str, Any]) -> bool:
        """Publish an event to all subscribers"""
        event_message = AgentMessage(
            sender_id=sender_id,
            recipient_id="broadcast",
            message_type=event_type,
            data=data,
            timestamp=datetime.utcnow()
        )
        
        return await self.send_message(event_message)
    
    async def _cleanup_old_messages(self):
        """Clean up old messages from history"""
        cutoff_time = datetime.utcnow() - self.message_ttl
        
        # Remove old messages from history
        self.message_history = [
            msg for msg in self.message_history
            if msg.timestamp > cutoff_time
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            'registered_agents': len(self.agents),
            'total_subscribers': sum(len(subs) for subs in self.subscribers.values()),
            'queue_sizes': {agent_id: len(queue) for agent_id, queue in self.message_queues.items()},
            'message_stats': self.stats.copy(),
            'message_history_size': len(self.message_history),
            'subscription_breakdown': {
                str(msg_type): len(subs) for msg_type, subs in self.subscribers.items()
            }
        }
    
    def get_message_history(self, limit: int = 100, message_type: Optional[MessageType] = None) -> List[Dict]:
        """Get recent message history"""
        messages = self.message_history[-limit:]
        
        if message_type:
            messages = [msg for msg in messages if msg.message_type == message_type]
        
        return [
            {
                'sender_id': msg.sender_id,
                'recipient_id': msg.recipient_id,
                'message_type': str(msg.message_type),
                'timestamp': msg.timestamp.isoformat(),
                'data_keys': list(msg.data.keys()) if msg.data else []
            }
            for msg in messages
        ]
    
    async def start(self):
        """Start the message bus"""
        self.running = True
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus"""
        self.running = False
        
        # Clear all queues
        self.message_queues.clear()
        self.message_history.clear()
        
        logger.info("Message bus stopped")


class EnhancedAgentRegistry:
    """
    Enhanced agent registry with health monitoring and discovery
    """
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60  # seconds
    
    def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str], agent_instance: 'BaseAgent') -> None:
        """Register an agent with detailed information"""
        self.agents[agent_id] = {
            'agent_type': agent_type,
            'capabilities': capabilities,
            'status': 'active',
            'last_heartbeat': datetime.utcnow(),
            'registered_at': datetime.utcnow(),
            'message_count': 0,
            'error_count': 0,
            'instance': agent_instance
        }
        
        # Register with message bus
        self.message_bus.register_agent(agent_id, agent_instance)
        
        logger.info(f"Registered agent {agent_id} of type {agent_type} with capabilities: {capabilities}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.message_bus.unregister_agent(agent_id)
            logger.info(f"Unregistered agent {agent_id}")
    
    async def update_heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat"""
        if agent_id in self.agents:
            self.agents[agent_id]['last_heartbeat'] = datetime.utcnow()
            self.agents[agent_id]['status'] = 'active'
    
    async def check_agent_health(self):
        """Check health of all registered agents"""
        current_time = datetime.utcnow()
        timeout_threshold = timedelta(seconds=self.heartbeat_timeout)
        
        for agent_id, agent_info in self.agents.items():
            last_heartbeat = agent_info['last_heartbeat']
            
            if current_time - last_heartbeat > timeout_threshold:
                if agent_info['status'] != 'inactive':
                    agent_info['status'] = 'inactive'
                    logger.warning(f"Agent {agent_id} appears to be inactive (last heartbeat: {last_heartbeat})")
                    
                    # Publish agent health event
                    await self.message_bus.publish_event(
                        MessageType.AGENT_STATUS,
                        "registry",
                        {
                            'agent_id': agent_id,
                            'status': 'inactive',
                            'last_heartbeat': last_heartbeat.isoformat()
                        }
                    )
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        return [
            agent_id for agent_id, info in self.agents.items()
            if capability in info['capabilities'] and info['status'] == 'active'
        ]
    
    def find_agents_by_type(self, agent_type: str) -> List[str]:
        """Find agents of a specific type"""
        return [
            agent_id for agent_id, info in self.agents.items()
            if info['agent_type'] == agent_type and info['status'] == 'active'
        ]
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an agent"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered agents"""
        # Return copy without instance references
        return {
            agent_id: {k: v for k, v in info.items() if k != 'instance'}
            for agent_id, info in self.agents.items()
        }


# Global instances for the MVP
_message_bus = MessageBus()
_agent_registry = EnhancedAgentRegistry(_message_bus)


def get_message_bus() -> MessageBus:
    """Get the global message bus instance"""
    return _message_bus


def get_agent_registry() -> EnhancedAgentRegistry:
    """Get the global agent registry instance"""
    return _agent_registry


async def start_message_infrastructure():
    """Start the message bus and registry"""
    await _message_bus.start()
    logger.info("Message infrastructure started")


async def stop_message_infrastructure():
    """Stop the message bus and registry"""
    await _message_bus.stop()
    logger.info("Message infrastructure stopped")
