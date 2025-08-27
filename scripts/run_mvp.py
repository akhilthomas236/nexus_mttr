#!/usr/bin/env python3
"""
Run the complete NEXUS MVP end-to-end
This script starts all agents and the web interface
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.log_ingester import LogIngesterAgent
from agents.analyzer import AnalyzerAgent
from agents.remediation import RemediationAgent
from web.app import run_server
from scripts.generate_logs import LogGenerator
import config

logger = logging.getLogger(__name__)


class NexusMVP:
    """Main orchestrator for the NEXUS MVP"""
    
    def __init__(self):
        self.running = False
        self.agents = {}
        self.tasks = []
        
    async def start_agents(self):
        """Start all NEXUS agents"""
        logger.info("Starting NEXUS agents...")
        
        # Initialize agents
        self.agents['log_ingester'] = LogIngesterAgent()
        self.agents['analyzer'] = AnalyzerAgent()
        self.agents['remediation'] = RemediationAgent()
        
        # Start agent tasks
        for agent_name, agent in self.agents.items():
            task = asyncio.create_task(agent.run())
            task.set_name(f"agent-{agent_name}")
            self.tasks.append(task)
            logger.info(f"Started {agent_name} agent")
        
        # Give agents time to start
        await asyncio.sleep(2)
        
    async def stop_agents(self):
        """Stop all agents gracefully"""
        logger.info("Stopping NEXUS agents...")
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All agents stopped")
    
    async def generate_sample_logs(self):
        """Generate sample logs for testing"""
        logger.info("Generating sample logs...")
        
        log_generator = LogGenerator()
        
        # Generate normal operations logs
        await asyncio.get_event_loop().run_in_executor(None, log_generator.generate_normal_logs, 1)
        
        # Generate some incident scenarios
        incident_scenarios = [
            {
                'type': 'database_connection_timeout',
                'duration_minutes': 30
            },
            {
                'type': 'memory_leak',
                'duration_minutes': 45
            }
        ]
        
        for scenario in incident_scenarios:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                log_generator.generate_incident_logs,
                scenario['type'],
                scenario['duration_minutes']
            )
        
        logger.info("Sample logs generated")
    
    async def run_log_processing(self):
        """Process generated logs through the system"""
        logger.info("Processing logs through NEXUS pipeline...")
        
        log_dir = Path(config.LOGS_DIR)
        log_files = list(log_dir.glob("*.log"))
        
        if not log_files:
            logger.warning("No log files found to process")
            return
        
        # Process each log file
        log_ingester = self.agents.get('log_ingester')
        if log_ingester:
            for log_file in log_files:
                logger.info(f"Processing {log_file.name}")
                try:
                    result = await log_ingester.process_log_file(str(log_file))
                    if result:
                        logger.info(f"Processed {log_file.name}: {len(result.get('log_entries', []))} entries, {len(result.get('anomalies', []))} anomalies")
                except Exception as e:
                    logger.error(f"Error processing {log_file.name}: {e}")
        
        logger.info("Log processing complete")
    
    async def run_demo_scenario(self):
        """Run a complete demo scenario"""
        logger.info("🚀 Starting NEXUS MVP Demo Scenario")
        
        try:
            # Step 1: Start agents
            await self.start_agents()
            
            # Step 2: Generate sample data
            await self.generate_sample_logs()
            
            # Step 3: Process logs
            await self.run_log_processing()
            
            # Step 4: Let agents process for a bit
            logger.info("Letting agents process data...")
            await asyncio.sleep(10)
            
            # Step 5: Show results
            await self.show_results()
            
            logger.info("✅ Demo scenario complete!")
            
        except Exception as e:
            logger.error(f"Error in demo scenario: {e}")
            raise
    
    async def show_results(self):
        """Show results from the demo scenario"""
        logger.info("\n" + "="*50)
        logger.info("NEXUS MVP DEMO RESULTS")
        logger.info("="*50)
        
        # Show agent status
        for agent_name, agent in self.agents.items():
            logger.info(f"{agent_name.upper()} Agent: Running (ID: {agent.agent_id})")
        
        # Show log processing results
        log_dir = Path(config.LOGS_DIR)
        log_files = list(log_dir.glob("*.log"))
        logger.info(f"\nLog Files Generated: {len(log_files)}")
        
        for log_file in log_files[:5]:  # Show first 5
            size_kb = log_file.stat().st_size / 1024
            logger.info(f"  - {log_file.name} ({size_kb:.1f} KB)")
        
        logger.info(f"\nWeb Interface: http://localhost:8000")
        logger.info("API Endpoints:")
        logger.info("  - GET /api/incidents - List incidents")
        logger.info("  - GET /api/system/health - System health")
        logger.info("  - GET /api/metrics - System metrics")
        logger.info("  - POST /api/simulate/incident - Simulate incident")
        
        logger.info("\n" + "="*50)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self, mode: str = "full"):
        """Run the NEXUS MVP in different modes"""
        self.running = True
        self.setup_signal_handlers()
        
        try:
            if mode == "demo":
                # Run demo scenario
                await self.run_demo_scenario()
                
            elif mode == "agents-only":
                # Start agents only
                await self.start_agents()
                logger.info("Agents running. Press Ctrl+C to stop.")
                
                while self.running:
                    await asyncio.sleep(1)
                    
            elif mode == "web-only":
                # Start web interface only
                logger.info("Starting web interface only...")
                run_server(host="0.0.0.0", port=8000, reload=False)
                
            else:  # full mode
                # Start everything
                await self.start_agents()
                
                logger.info("🚀 NEXUS MVP is running!")
                logger.info("Web interface: http://localhost:8000")
                logger.info("Press Ctrl+C to stop")
                
                # Start web server in background
                import threading
                web_thread = threading.Thread(
                    target=run_server,
                    kwargs={"host": "0.0.0.0", "port": 8000, "reload": False},
                    daemon=True
                )
                web_thread.start()
                
                # Keep running until signal
                while self.running:
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        
        finally:
            await self.stop_agents()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run NEXUS MVP")
    parser.add_argument(
        "--mode", 
        choices=["full", "demo", "agents-only", "web-only"],
        default="demo",
        help="Run mode (default: demo)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('nexus-mvp.log')
        ]
    )
    
    logger.info(f"Starting NEXUS MVP in {args.mode} mode")
    
    # Create and run MVP
    mvp = NexusMVP()
    await mvp.run(args.mode)


if __name__ == "__main__":
    asyncio.run(main())
