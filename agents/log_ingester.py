"""
Log Ingester Agent for NEXUS MVP
Processes and ingests log data for analysis
"""
import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from agents.base_agent import BaseAgent, MCPMessage
from config import LOGS_DIR

logger = logging.getLogger(__name__)

class LogIngesterAgent(BaseAgent):
    """Agent responsible for ingesting and processing log data"""
    
    def __init__(self):
        super().__init__(
            agent_id="log-ingester-001",
            agent_type="perception",
            capabilities=["log_ingestion", "log_parsing", "real_time_monitoring"]
        )
        self.processed_files = set()
        self.log_buffer = []
        self.buffer_size = 1000
        
        # Register message handlers
        self.register_handler("ingest_logs", self._handle_ingest_logs)
        self.register_handler("get_recent_logs", self._handle_get_recent_logs)
        self.register_handler("analyze_log_patterns", self._handle_analyze_patterns)
    
    async def initialize(self):
        """Initialize the log ingester"""
        print(f"Initializing Log Ingester Agent...")
        
        # Start continuous log monitoring
        asyncio.create_task(self._monitor_logs())
        
        # Load existing logs
        await self._load_existing_logs()
    
    async def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up Log Ingester Agent...")
    
    async def _monitor_logs(self):
        """Continuously monitor for new log files"""
        while self.running:
            try:
                await self._check_for_new_logs()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"Error monitoring logs: {e}")
                await asyncio.sleep(10)
    
    async def _load_existing_logs(self):
        """Load existing log files"""
        if not os.path.exists(LOGS_DIR):
            return
        
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith('.jsonl') and filename not in self.processed_files:
                filepath = os.path.join(LOGS_DIR, filename)
                await self._process_log_file(filepath)
                self.processed_files.add(filename)
    
    async def _check_for_new_logs(self):
        """Check for new log files"""
        if not os.path.exists(LOGS_DIR):
            return
        
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith('.jsonl') and filename not in self.processed_files:
                filepath = os.path.join(LOGS_DIR, filename)
                await self._process_log_file(filepath)
                self.processed_files.add(filename)
    
    async def process_log_file(self, filepath: str):
        """Public method to process a log file and return analysis results"""
        return await self._process_log_file(filepath)
    
    async def _process_log_file(self, filepath: str):
        """Process a single log file"""
        logger.info(f"Processing log file: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                logs = []
                for line in f:
                    if line.strip():
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                
                # Generate summary and detect anomalies
                if logs:
                    summary = self._generate_log_summary(logs)
                    
                    # Add to buffer
                    self.log_buffer.extend(logs)
                    if len(self.log_buffer) > self.buffer_size:
                        self.log_buffer = self.log_buffer[-self.buffer_size:]
                    
                    # Mark file as processed
                    self.processed_files.add(filepath)
                    
                    logger.info(f"Processed {len(logs)} log entries from {filepath}")
                    logger.info(f"Detected {len(summary.get('anomalies_detected', []))} anomalies")
                    
                    # Return results for web interface
                    return {
                        'log_entries': logs[-100:],  # Return last 100 entries
                        'anomalies': summary.get('anomalies_detected', []),
                        'summary': summary,
                        'source_file': os.path.basename(filepath),
                        'processed_count': len(logs)
                    }
                
                return {'log_entries': [], 'anomalies': [], 'summary': {}}
        
        except Exception as e:
            logger.error(f"Error processing log file {filepath}: {e}")
            return {'log_entries': [], 'anomalies': [], 'summary': {}, 'error': str(e)}
    
    def _generate_log_summary(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for logs"""
        if not logs:
            return {}
        
        # Count by level
        level_counts = {}
        service_counts = {}
        error_messages = []
        
        for log in logs:
            level = log.get('level', 'UNKNOWN')
            service = log.get('service', 'unknown')
            
            level_counts[level] = level_counts.get(level, 0) + 1
            service_counts[service] = service_counts.get(service, 0) + 1
            
            if level in ['ERROR', 'FATAL']:
                error_messages.append({
                    'timestamp': log.get('timestamp'),
                    'service': service,
                    'message': log.get('message', ''),
                    'metadata': log.get('metadata', {})
                })
        
        # Calculate error rate
        total_logs = len(logs)
        error_count = level_counts.get('ERROR', 0) + level_counts.get('FATAL', 0)
        error_rate = error_count / total_logs if total_logs > 0 else 0
        
        # Time range
        timestamps = [log.get('timestamp') for log in logs if log.get('timestamp')]
        time_range = {
            'start': min(timestamps) if timestamps else None,
            'end': max(timestamps) if timestamps else None
        }
        
        return {
            'total_logs': total_logs,
            'error_rate': error_rate,
            'level_distribution': level_counts,
            'service_distribution': service_counts,
            'time_range': time_range,
            'recent_errors': error_messages[-10:],  # Last 10 errors
            'anomalies_detected': self._detect_anomalies(logs)
        }
    
    def _detect_anomalies(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple anomaly detection in logs"""
        anomalies = []
        
        # Check for error spikes
        error_logs = [log for log in logs if log.get('level') in ['ERROR', 'FATAL']]
        if len(error_logs) > len(logs) * 0.1:  # More than 10% errors
            anomalies.append({
                'type': 'error_spike',
                'description': f'High error rate detected: {len(error_logs)}/{len(logs)} logs',
                'severity': 'high' if len(error_logs) > len(logs) * 0.2 else 'medium'
            })
        
        # Check for repeated errors
        error_messages = {}
        for log in error_logs:
            msg = log.get('message', '')
            error_messages[msg] = error_messages.get(msg, 0) + 1
        
        for msg, count in error_messages.items():
            if count > 5:  # Same error repeated more than 5 times
                anomalies.append({
                    'type': 'repeated_error',
                    'description': f'Repeated error: "{msg[:50]}..." ({count} times)',
                    'severity': 'medium'
                })
        
        # Check for service-specific issues
        service_errors = {}
        for log in error_logs:
            service = log.get('service', 'unknown')
            service_errors[service] = service_errors.get(service, 0) + 1
        
        for service, count in service_errors.items():
            service_total = len([log for log in logs if log.get('service') == service])
            if service_total > 0 and count / service_total > 0.2:  # More than 20% errors for this service
                anomalies.append({
                    'type': 'service_degradation',
                    'description': f'Service {service} showing high error rate: {count}/{service_total}',
                    'severity': 'high',
                    'affected_service': service
                })
        
        return anomalies
    
    async def _handle_ingest_logs(self, message: MCPMessage) -> MCPMessage:
        """Handle log ingestion request"""
        payload = message.payload
        logs = payload.get('logs', [])
        
        # Process logs
        summary = self._generate_log_summary(logs)
        
        # Add to buffer
        self.log_buffer.extend(logs)
        if len(self.log_buffer) > self.buffer_size:
            self.log_buffer = self.log_buffer[-self.buffer_size:]
        
        return MCPMessage(
            message_type="logs_ingested",
            payload={
                'processed_count': len(logs),
                'summary': summary,
                'timestamp': datetime.utcnow().isoformat()
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_get_recent_logs(self, message: MCPMessage) -> MCPMessage:
        """Handle request for recent logs"""
        payload = message.payload
        limit = payload.get('limit', 100)
        service_filter = payload.get('service')
        level_filter = payload.get('level')
        
        # Filter logs
        filtered_logs = self.log_buffer
        
        if service_filter:
            filtered_logs = [log for log in filtered_logs 
                           if log.get('service') == service_filter]
        
        if level_filter:
            filtered_logs = [log for log in filtered_logs 
                           if log.get('level') == level_filter]
        
        # Sort by timestamp and limit
        filtered_logs = sorted(filtered_logs, 
                             key=lambda x: x.get('timestamp', ''), 
                             reverse=True)[:limit]
        
        return MCPMessage(
            message_type="recent_logs_response",
            payload={
                'logs': filtered_logs,
                'total_count': len(self.log_buffer),
                'filtered_count': len(filtered_logs)
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_analyze_patterns(self, message: MCPMessage) -> MCPMessage:
        """Handle log pattern analysis request"""
        payload = message.payload
        time_window = payload.get('time_window_minutes', 60)
        
        # Get logs from time window
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window)
        recent_logs = [
            log for log in self.log_buffer 
            if datetime.fromisoformat(log.get('timestamp', '1970-01-01')) > cutoff_time
        ]
        
        # Analyze patterns
        patterns = self._analyze_log_patterns(recent_logs)
        
        return MCPMessage(
            message_type="pattern_analysis_response",
            payload={
                'time_window_minutes': time_window,
                'analyzed_logs': len(recent_logs),
                'patterns': patterns,
                'timestamp': datetime.utcnow().isoformat()
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    def _analyze_log_patterns(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in logs"""
        if not logs:
            return {}
        
        # Temporal patterns
        hourly_distribution = {}
        for log in logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                hour = datetime.fromisoformat(timestamp).hour
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
        
        # Error patterns
        error_patterns = {}
        for log in logs:
            if log.get('level') in ['ERROR', 'FATAL']:
                service = log.get('service', 'unknown')
                message = log.get('message', '')
                # Group similar error messages
                error_key = f"{service}:{message[:50]}"
                error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
        
        # Service activity patterns
        service_activity = {}
        for log in logs:
            service = log.get('service', 'unknown')
            service_activity[service] = service_activity.get(service, 0) + 1
        
        return {
            'hourly_distribution': hourly_distribution,
            'error_patterns': error_patterns,
            'service_activity': service_activity,
            'total_logs_analyzed': len(logs),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    async def run(self):
        """Main run loop for the Log Ingester Agent"""
        logger.info(f"Log Ingester Agent {self.agent_id} starting...")
        
        while self.running:
            try:
                # Monitor for new log files
                await self._monitor_logs()
                
                # Process any pending messages
                await self.process_pending_messages()
                
                # Send heartbeat
                await self.send_heartbeat()
                
                # Wait before next iteration
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in log ingester run loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
        
        logger.info(f"Log Ingester Agent {self.agent_id} stopped")
