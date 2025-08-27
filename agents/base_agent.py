"""
Base MCP Agent class for NEXUS MVP
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

class MCPMessage:
    """MCP Protocol message"""
    def __init__(self, message_type: str, payload: Dict[str, Any], 
                 source: str, target: str = None, correlation_id: str = None):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.message_type = message_type
        self.payload = payload
        self.source = source
        self.target = target
        self.correlation_id = correlation_id or self.id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.message_type,
            "payload": self.payload,
            "source": self.source,
            "target": self.target,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        msg = cls(
            message_type=data["type"],
            payload=data["payload"],
            source=data["source"],
            target=data.get("target"),
            correlation_id=data.get("correlation_id")
        )
        msg.id = data["id"]
        msg.timestamp = datetime.fromisoformat(data["timestamp"])
        return msg

class BaseAgent(ABC):
    """Base class for MCP agents"""
    
    def __init__(self, agent_id: str, agent_type: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = "starting"
        self.last_heartbeat = datetime.utcnow()
        self.message_handlers: Dict[str, Callable] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
        self.tasks_processed = 0
        self.errors = 0
        
        # Register default handlers
        self.register_handler("ping", self._handle_ping)
        self.register_handler("heartbeat_request", self._handle_heartbeat_request)
        self.register_handler("status_request", self._handle_status_request)
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler
    
    async def start(self):
        """Start the agent"""
        self.status = "starting"
        self.running = True
        
        # Start message processing loop
        asyncio.create_task(self._message_loop())
        
        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())
        
        # Agent-specific initialization
        await self.initialize()
        
        self.status = "online"
        print(f"Agent {self.agent_id} ({self.agent_type}) started")
    
    async def stop(self):
        """Stop the agent"""
        self.status = "stopping"
        self.running = False
        
        # Agent-specific cleanup
        await self.cleanup()
        
        self.status = "offline"
        print(f"Agent {self.agent_id} stopped")
    
    async def send_message(self, message: MCPMessage):
        """Send a message (to be implemented by message bus)"""
        # In MVP, we'll just print the message
        print(f"[{self.agent_id}] Sending: {message.message_type} -> {message.target}")
        print(f"  Payload: {json.dumps(message.payload, indent=2)}")
    
    async def receive_message(self, message: MCPMessage):
        """Receive a message from the message bus"""
        await self.message_queue.put(message)
    
    async def _message_loop(self):
        """Main message processing loop"""
        while self.running:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_message(message)
                self.tasks_processed += 1
                
            except asyncio.TimeoutError:
                # No message received, continue
                continue
            except Exception as e:
                self.errors += 1
                print(f"Error processing message in {self.agent_id}: {e}")
    
    async def _process_message(self, message: MCPMessage):
        """Process a received message"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                response = await handler(message)
                if response:
                    await self.send_message(response)
            except Exception as e:
                print(f"Error in handler {message.message_type}: {e}")
                # Send error response
                error_response = MCPMessage(
                    message_type="error",
                    payload={
                        "error": str(e),
                        "original_message": message.to_dict()
                    },
                    source=self.agent_id,
                    target=message.source,
                    correlation_id=message.correlation_id
                )
                await self.send_message(error_response)
        else:
            print(f"No handler for message type: {message.message_type}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                self.last_heartbeat = datetime.utcnow()
                
                heartbeat = MCPMessage(
                    message_type="heartbeat",
                    payload={
                        "agent_id": self.agent_id,
                        "status": self.status,
                        "timestamp": self.last_heartbeat.isoformat(),
                        "tasks_processed": self.tasks_processed,
                        "errors": self.errors
                    },
                    source=self.agent_id,
                    target="registry"
                )
                
                await self.send_message(heartbeat)
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                print(f"Heartbeat error in {self.agent_id}: {e}")
                await asyncio.sleep(30)
    
    async def _handle_ping(self, message: MCPMessage) -> MCPMessage:
        """Handle ping message"""
        return MCPMessage(
            message_type="pong",
            payload={"timestamp": datetime.utcnow().isoformat()},
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_heartbeat_request(self, message: MCPMessage) -> MCPMessage:
        """Handle heartbeat request"""
        return MCPMessage(
            message_type="heartbeat_response",
            payload={
                "agent_id": self.agent_id,
                "status": self.status,
                "last_heartbeat": self.last_heartbeat.isoformat(),
                "capabilities": self.capabilities,
                "tasks_processed": self.tasks_processed,
                "errors": self.errors
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_status_request(self, message: MCPMessage) -> MCPMessage:
        """Handle status request"""
        return MCPMessage(
            message_type="status_response",
            payload={
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": self.status,
                "capabilities": self.capabilities,
                "uptime": (datetime.utcnow() - self.last_heartbeat).total_seconds(),
                "performance": {
                    "tasks_processed": self.tasks_processed,
                    "errors": self.errors,
                    "error_rate": self.errors / max(self.tasks_processed, 1)
                }
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    @abstractmethod
    async def initialize(self):
        """Agent-specific initialization"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Agent-specific cleanup"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "capabilities": self.capabilities,
            "tasks_processed": self.tasks_processed,
            "errors": self.errors,
            "uptime": (datetime.utcnow() - self.last_heartbeat).total_seconds()
        }

class AgentRegistry:
    """Simple agent registry for MVP"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_bus = MessageBus()
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent"""
        self.agents[agent.agent_id] = agent
        print(f"Registered agent: {agent.agent_id} ({agent.agent_type})")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            print(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseAgent]:
        """Get agents by type"""
        return [agent for agent in self.agents.values() 
                if agent.agent_type == agent_type]
    
    def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """Get agents by capability"""
        return [agent for agent in self.agents.values() 
                if capability in agent.capabilities]
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents"""
        return list(self.agents.values())

class MessageBus:
    """Simple message bus for MVP"""
    
    def __init__(self):
        self.registry = None
    
    def set_registry(self, registry: AgentRegistry):
        """Set the agent registry"""
        self.registry = registry
    
    async def send_message(self, message: MCPMessage):
        """Send message to target agent"""
        if not self.registry:
            print("Message bus not connected to registry")
            return
        
        if message.target:
            # Send to specific agent
            target_agent = self.registry.get_agent(message.target)
            if target_agent:
                await target_agent.receive_message(message)
            else:
                print(f"Target agent not found: {message.target}")
        else:
            # Broadcast to all agents
            for agent in self.registry.get_all_agents():
                if agent.agent_id != message.source:
                    await agent.receive_message(message)
    
    async def broadcast_message(self, message: MCPMessage, agent_type: str = None):
        """Broadcast message to agents of specific type"""
        if not self.registry:
            return
        
        if agent_type:
            targets = self.registry.get_agents_by_type(agent_type)
        else:
            targets = self.registry.get_all_agents()
        
        for agent in targets:
            if agent.agent_id != message.source:
                await agent.receive_message(message)
