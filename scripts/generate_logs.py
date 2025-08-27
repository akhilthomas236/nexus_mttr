"""
Log generation script for NEXUS MVP
Generates realistic application logs with incident scenarios
"""
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
from config import LOGS_DIR, SERVICE_TOPOLOGY, INCIDENT_PATTERNS, LOG_GENERATION, get_data_directories

class LogGenerator:
    def __init__(self):
        self.services = list(SERVICE_TOPOLOGY.keys())
        self.log_levels = LOG_GENERATION["log_levels"]
        self.error_rate = LOG_GENERATION["error_rate"]
        self.current_incidents = []
        
        # Ensure directories exist
        get_data_directories()
        
        # Common log messages by service type
        self.message_templates = {
            "api": [
                "Processing request {request_id} for endpoint {endpoint}",
                "Request completed in {duration}ms",
                "Authentication successful for user {user_id}",
                "Rate limit exceeded for IP {ip_address}",
                "Invalid request parameters: {error}",
                "Database query executed in {query_time}ms",
                "Cache hit for key {cache_key}",
                "Cache miss for key {cache_key}",
                "External API call to {service} completed",
                "Health check passed"
            ],
            "database": [
                "Connection established from {client_ip}",
                "Query executed: {query} in {duration}ms",
                "Transaction committed successfully",
                "Connection pool usage: {pool_usage}%",
                "Index scan on table {table}",
                "Backup completed successfully",
                "Slow query detected: {query}",
                "Connection timeout from {client_ip}",
                "Lock wait timeout exceeded",
                "Disk space usage: {disk_usage}%"
            ],
            "cache": [
                "Cache entry set: {key}",
                "Cache entry retrieved: {key}",
                "Cache entry expired: {key}",
                "Cache eviction occurred",
                "Memory usage: {memory_usage}%",
                "Cache cluster node joined",
                "Replication lag: {lag}ms",
                "Cache miss ratio: {miss_ratio}%",
                "Key space notification sent",
                "Persistence checkpoint completed"
            ],
            "queue": [
                "Message published to queue {queue_name}",
                "Message consumed from queue {queue_name}",
                "Queue depth: {depth} messages",
                "Consumer lag: {lag}ms",
                "Dead letter queue message: {message_id}",
                "Queue purged: {queue_name}",
                "Connection established to broker",
                "Acknowledgment received for {message_id}",
                "Message redelivery attempt {attempt}",
                "Queue binding created"
            ],
            "worker": [
                "Job started: {job_id}",
                "Job completed: {job_id} in {duration}s",
                "Job failed: {job_id} - {error}",
                "Worker process started",
                "Worker process terminated",
                "Task queue processed {count} items",
                "Scheduled job {job_name} executed",
                "Worker health check passed",
                "Memory usage: {memory_usage}MB",
                "CPU usage: {cpu_usage}%"
            ],
            "batch": [
                "Batch job {job_id} started",
                "Processing {count} records",
                "Batch job completed successfully",
                "Data validation passed",
                "ETL pipeline stage {stage} completed",
                "Report generated: {report_name}",
                "Data export completed",
                "Scheduled maintenance task completed",
                "Cleanup job removed {count} old records",
                "Analytics aggregation completed"
            ],
            "external": [
                "API call successful",
                "API call failed with status {status_code}",
                "Rate limit reached",
                "Authentication token refreshed",
                "Circuit breaker opened",
                "Circuit breaker closed",
                "Timeout waiting for response",
                "SSL handshake completed",
                "Connection pool exhausted",
                "Service unavailable"
            ]
        }
        
        # Error message templates
        self.error_templates = [
            "Connection refused to {service}",
            "Timeout waiting for response from {service}",
            "Authentication failed for user {user_id}",
            "Database connection pool exhausted",
            "Out of memory error",
            "File not found: {filename}",
            "Permission denied accessing {resource}",
            "Invalid configuration: {config_key}",
            "Service unavailable: {service}",
            "SSL certificate expired",
            "Disk space insufficient",
            "Network unreachable",
            "Resource limit exceeded",
            "Deadlock detected",
            "Constraint violation"
        ]
    
    def generate_log_entry(self, service: str, timestamp: datetime, force_error: bool = False) -> Dict[str, Any]:
        """Generate a single log entry"""
        service_info = SERVICE_TOPOLOGY[service]
        service_type = service_info["type"]
        
        # Determine log level
        if force_error:
            level = random.choice(["ERROR", "FATAL"])
        else:
            level_weights = {"INFO": 0.7, "WARN": 0.2, "ERROR": 0.08, "FATAL": 0.02}
            level = random.choices(list(level_weights.keys()), weights=list(level_weights.values()))[0]
        
        # Generate message
        if level in ["ERROR", "FATAL"]:
            message_template = random.choice(self.error_templates)
        else:
            templates = self.message_templates.get(service_type, self.message_templates["api"])
            message_template = random.choice(templates)
        
        # Fill in template variables
        message = self._fill_template(message_template, service, service_type)
        
        # Generate metadata
        metadata = self._generate_metadata(service, service_type, level)
        
        return {
            "timestamp": timestamp.isoformat(),
            "service": service,
            "level": level,
            "message": message,
            "metadata": metadata,
            "trace_id": self._generate_trace_id()
        }
    
    def _fill_template(self, template: str, service: str, service_type: str) -> str:
        """Fill template variables with realistic values"""
        replacements = {
            "request_id": f"req_{random.randint(100000, 999999)}",
            "endpoint": random.choice(["/api/users", "/api/auth", "/api/payments", "/health"]),
            "duration": random.randint(50, 2000),
            "user_id": f"user_{random.randint(1000, 9999)}",
            "ip_address": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "error": random.choice(["invalid_token", "missing_parameter", "validation_failed"]),
            "query_time": random.randint(10, 500),
            "cache_key": f"cache_{random.randint(1000, 9999)}",
            "service": random.choice(self.services),
            "client_ip": f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "query": "SELECT * FROM users WHERE id = ?",
            "pool_usage": random.randint(20, 95),
            "table": random.choice(["users", "payments", "sessions", "logs"]),
            "disk_usage": random.randint(30, 90),
            "key": f"key_{random.randint(1000, 9999)}",
            "memory_usage": random.randint(40, 95),
            "lag": random.randint(10, 1000),
            "miss_ratio": random.randint(5, 30),
            "queue_name": random.choice(["notifications", "payments", "analytics"]),
            "depth": random.randint(0, 1000),
            "message_id": f"msg_{random.randint(100000, 999999)}",
            "attempt": random.randint(1, 3),
            "job_id": f"job_{random.randint(100000, 999999)}",
            "count": random.randint(100, 10000),
            "job_name": random.choice(["daily_report", "cleanup", "backup"]),
            "cpu_usage": random.randint(20, 90),
            "stage": random.choice(["extract", "transform", "load"]),
            "report_name": f"report_{datetime.now().strftime('%Y%m%d')}",
            "status_code": random.choice([400, 401, 403, 404, 429, 500, 502, 503]),
            "filename": random.choice(["/var/log/app.log", "/etc/config.yml", "/tmp/data.csv"]),
            "resource": random.choice(["/api/admin", "/var/lib/data", "/etc/secrets"]),
            "config_key": random.choice(["database.url", "api.key", "timeout.value"])
        }
        
        # Replace template variables
        for key, value in replacements.items():
            template = template.replace("{" + key + "}", str(value))
        
        return template
    
    def _generate_metadata(self, service: str, service_type: str, level: str) -> Dict[str, Any]:
        """Generate realistic metadata for log entry"""
        metadata = {
            "service_type": service_type,
            "version": f"1.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "environment": "production",
            "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
            "instance_id": f"i-{random.randint(100000000, 999999999):x}"
        }
        
        if service_type == "api":
            metadata.update({
                "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                "status_code": random.choice([200, 201, 400, 401, 404, 500]),
                "response_time_ms": random.randint(50, 2000),
                "user_agent": "Mozilla/5.0 (compatible; API-Client/1.0)"
            })
        elif service_type == "database":
            metadata.update({
                "connection_count": random.randint(10, 100),
                "active_queries": random.randint(0, 50),
                "buffer_pool_usage": random.randint(60, 95)
            })
        elif service_type == "cache":
            metadata.update({
                "hit_rate": round(random.uniform(0.7, 0.95), 2),
                "memory_usage_mb": random.randint(512, 4096),
                "keys_count": random.randint(1000, 100000)
            })
        
        if level in ["ERROR", "FATAL"]:
            metadata["error_code"] = f"E{random.randint(1000, 9999)}"
            metadata["stack_trace"] = "com.example.Service.method(Service.java:123)"
        
        return metadata
    
    def _generate_trace_id(self) -> str:
        """Generate a trace ID for distributed tracing"""
        return f"trace_{random.randint(100000000000000000, 999999999999999999):x}"
    
    def generate_incident_logs(self, incident_pattern: str, duration_minutes: int = 30) -> List[Dict[str, Any]]:
        """Generate logs for a specific incident pattern"""
        pattern = INCIDENT_PATTERNS[incident_pattern]
        affected_services = pattern["affected_services"]
        logs = []
        
        start_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        # Generate normal logs first
        for minute in range(duration_minutes):
            timestamp = start_time + timedelta(minutes=minute)
            
            # Increase error rate during incident
            error_multiplier = 1
            if minute > duration_minutes * 0.2:  # Incident starts 20% into the window
                error_multiplier = 10 if minute < duration_minutes * 0.8 else 5
            
            for service in affected_services:
                logs_per_minute = random.randint(20, 50)
                for _ in range(logs_per_minute):
                    log_time = timestamp + timedelta(seconds=random.randint(0, 59))
                    force_error = random.random() < (self.error_rate * error_multiplier)
                    logs.append(self.generate_log_entry(service, log_time, force_error))
        
        return logs
    
    def generate_normal_logs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate normal operational logs"""
        logs = []
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        for hour in range(hours):
            for minute in range(60):
                timestamp = start_time + timedelta(hours=hour, minutes=minute)
                
                # Generate logs for all services
                for service in self.services:
                    logs_per_minute = random.randint(5, 20)
                    for _ in range(logs_per_minute):
                        log_time = timestamp + timedelta(seconds=random.randint(0, 59))
                        force_error = random.random() < self.error_rate
                        logs.append(self.generate_log_entry(service, log_time, force_error))
        
        return logs
    
    def save_logs_to_file(self, logs: List[Dict[str, Any]], filename: str):
        """Save logs to JSON file"""
        filepath = os.path.join(LOGS_DIR, filename)
        with open(filepath, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + '\n')
        print(f"Saved {len(logs)} log entries to {filepath}")
    
    def generate_all_scenarios(self):
        """Generate logs for all incident scenarios"""
        print("Generating normal operational logs...")
        normal_logs = self.generate_normal_logs(24)
        self.save_logs_to_file(normal_logs, "normal_operations.jsonl")
        
        print("Generating incident scenario logs...")
        for pattern_name in INCIDENT_PATTERNS.keys():
            print(f"  - {pattern_name}")
            incident_logs = self.generate_incident_logs(pattern_name)
            self.save_logs_to_file(incident_logs, f"incident_{pattern_name}.jsonl")
        
        # Generate recent logs for real-time simulation
        print("Generating recent logs for simulation...")
        recent_logs = []
        for minute in range(60):  # Last hour
            timestamp = datetime.utcnow() - timedelta(minutes=60-minute)
            for service in self.services:
                logs_count = random.randint(2, 8)
                for _ in range(logs_count):
                    log_time = timestamp + timedelta(seconds=random.randint(0, 59))
                    recent_logs.append(self.generate_log_entry(service, log_time))
        
        self.save_logs_to_file(recent_logs, "recent_logs.jsonl")
        
        print(f"Log generation completed! Files saved to {LOGS_DIR}")

if __name__ == "__main__":
    generator = LogGenerator()
    generator.generate_all_scenarios()
