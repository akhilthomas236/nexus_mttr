"""
Configuration settings for NEXUS MVP
"""
import os
from typing import Dict, Any

# Application settings
APP_NAME = "NEXUS MVP"
VERSION = "0.1.0"
DEBUG = True
HOST = "0.0.0.0"
PORT = 8000

# Data directories
DATA_DIR = "data"
LOGS_DIR = f"{DATA_DIR}/logs"
INCIDENTS_DIR = f"{DATA_DIR}/incidents"
KNOWLEDGE_DIR = f"{DATA_DIR}/knowledge"

# Database settings
DATABASE_URL = f"sqlite:///{INCIDENTS_DIR}/incidents.db"

# AI/ML settings - Amazon Bedrock
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# Bedrock model configuration
BEDROCK_CONFIG = {
    "model_id": "anthropic.claude-3-haiku-20240307-v1:0",  # Fast, cost-effective model
    "max_tokens": 1000,
    "temperature": 0.3,
    "top_p": 0.9,
    "region": AWS_REGION
}

# Alternative models for different use cases
BEDROCK_MODELS = {
    "fast": "anthropic.claude-3-haiku-20240307-v1:0",      # Quick analysis
    "balanced": "anthropic.claude-3-sonnet-20240229-v1:0", # Balanced performance  
    "advanced": "anthropic.claude-3-opus-20240229-v1:0"    # Complex reasoning
}

# Log generation settings
LOG_GENERATION = {
    "services": ["auth-service", "user-service", "payment-service", "notification-service", "analytics-service"],
    "log_levels": ["INFO", "WARN", "ERROR", "FATAL"],
    "error_rate": 0.05,  # 5% error rate baseline
    "incident_probability": 0.1,  # 10% chance of incident per hour
    "logs_per_minute": 100,
    "retention_days": 30
}

# Incident detection settings
INCIDENT_DETECTION = {
    "error_rate_threshold": 0.15,  # 15% error rate triggers incident
    "response_time_threshold": 5000,  # 5 second response time threshold (ms)
    "availability_threshold": 0.95,  # 95% availability threshold
    "detection_window_minutes": 5,  # Rolling window for detection
    "min_samples": 10  # Minimum samples needed for detection
}

# Agent settings
AGENT_CONFIG = {
    "heartbeat_interval": 30,  # seconds
    "max_retries": 3,
    "timeout": 60,  # seconds
    "log_level": "INFO"
}

# MCP protocol settings
MCP_CONFIG = {
    "version": "1.0.0",
    "message_timeout": 30,
    "max_message_size": 1024 * 1024,  # 1MB
    "compression": True
}

# Knowledge base settings
KNOWLEDGE_BASE = {
    "similarity_threshold": 0.7,
    "max_recommendations": 5,
    "learning_rate": 0.1,
    "confidence_threshold": 0.8
}

# Remediation settings
REMEDIATION = {
    "auto_approve_threshold": 0.9,  # Auto-approve if confidence > 90%
    "require_approval": ["restart", "scale", "deploy"],
    "timeout_minutes": 30,
    "rollback_enabled": True
}

# Service topology for simulation
SERVICE_TOPOLOGY = {
    "auth-service": {
        "dependencies": ["user-db", "redis-cache"],
        "dependents": ["user-service", "payment-service"],
        "type": "api",
        "criticality": "high"
    },
    "user-service": {
        "dependencies": ["auth-service", "user-db"],
        "dependents": ["notification-service", "analytics-service"],
        "type": "api",
        "criticality": "medium"
    },
    "payment-service": {
        "dependencies": ["auth-service", "payment-db", "external-payment-gateway"],
        "dependents": ["notification-service"],
        "type": "api",
        "criticality": "high"
    },
    "notification-service": {
        "dependencies": ["user-service", "payment-service", "message-queue"],
        "dependents": [],
        "type": "worker",
        "criticality": "low"
    },
    "analytics-service": {
        "dependencies": ["user-service", "analytics-db"],
        "dependents": [],
        "type": "batch",
        "criticality": "low"
    },
    "user-db": {
        "dependencies": [],
        "dependents": ["auth-service", "user-service"],
        "type": "database",
        "criticality": "high"
    },
    "payment-db": {
        "dependencies": [],
        "dependents": ["payment-service"],
        "type": "database",
        "criticality": "high"
    },
    "analytics-db": {
        "dependencies": [],
        "dependents": ["analytics-service"],
        "type": "database",
        "criticality": "medium"
    },
    "redis-cache": {
        "dependencies": [],
        "dependents": ["auth-service"],
        "type": "cache",
        "criticality": "medium"
    },
    "message-queue": {
        "dependencies": [],
        "dependents": ["notification-service"],
        "type": "queue",
        "criticality": "medium"
    },
    "external-payment-gateway": {
        "dependencies": [],
        "dependents": ["payment-service"],
        "type": "external",
        "criticality": "high"
    }
}

# Common incident patterns for simulation
INCIDENT_PATTERNS = {
    "database_connection_timeout": {
        "description": "Database connection pool exhausted",
        "affected_services": ["user-db", "auth-service", "user-service"],
        "symptoms": ["high_response_time", "connection_errors", "timeout_errors"],
        "root_cause": "Database connection pool size insufficient for load",
        "remediation": [
            "Increase database connection pool size",
            "Restart affected services",
            "Monitor connection usage"
        ]
    },
    "memory_leak": {
        "description": "Memory leak causing OOM errors",
        "affected_services": ["payment-service"],
        "symptoms": ["increasing_memory_usage", "oom_errors", "service_restarts"],
        "root_cause": "Memory leak in payment processing logic",
        "remediation": [
            "Restart affected service",
            "Deploy memory leak fix",
            "Increase memory limits temporarily"
        ]
    },
    "external_api_failure": {
        "description": "External payment gateway failure",
        "affected_services": ["external-payment-gateway", "payment-service"],
        "symptoms": ["api_errors", "failed_payments", "timeout_errors"],
        "root_cause": "External payment gateway experiencing outage",
        "remediation": [
            "Switch to backup payment provider",
            "Implement circuit breaker",
            "Queue failed payments for retry"
        ]
    },
    "cache_eviction": {
        "description": "Cache hit rate degradation",
        "affected_services": ["redis-cache", "auth-service"],
        "symptoms": ["high_response_time", "database_load_increase", "cache_misses"],
        "root_cause": "Cache eviction due to memory pressure",
        "remediation": [
            "Increase cache memory allocation",
            "Optimize cache key expiration",
            "Scale cache cluster"
        ]
    },
    "queue_backup": {
        "description": "Message queue backup causing delays",
        "affected_services": ["message-queue", "notification-service"],
        "symptoms": ["queue_depth_increase", "message_delays", "consumer_lag"],
        "root_cause": "Consumer processing slower than producer rate",
        "remediation": [
            "Scale consumer instances",
            "Optimize message processing",
            "Implement message batching"
        ]
    }
}

def get_data_directories():
    """Ensure data directories exist"""
    import os
    dirs = [DATA_DIR, LOGS_DIR, INCIDENTS_DIR, KNOWLEDGE_DIR]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    return dirs
