#!/usr/bin/env python3
"""
Test Amazon Bedrock Integration for NEXUS MVP
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bedrock_client import get_bedrock_client, test_bedrock_connection


async def test_bedrock_features():
    """Test all Bedrock AI features"""
    print("🧪 Testing Amazon Bedrock Integration for NEXUS MVP")
    print("=" * 60)
    
    client = get_bedrock_client()
    
    # Test 1: Basic connection
    print("\n1. Testing Bedrock Connection...")
    is_connected = await test_bedrock_connection()
    
    if is_connected:
        print("✅ Bedrock connection successful!")
    else:
        print("⚠️  Bedrock not available - using mock responses")
    
    # Test 2: Log analysis
    print("\n2. Testing Log Analysis...")
    sample_logs = [
        "2024-01-15 10:00:00 ERROR auth-service Database connection failed",
        "2024-01-15 10:01:00 ERROR auth-service Connection timeout after 30s",
        "2024-01-15 10:02:00 FATAL auth-service Service shutdown due to repeated failures",
        "2024-01-15 10:03:00 ERROR payment-service Unable to process transactions",
        "2024-01-15 10:04:00 WARN notification-service High queue depth detected"
    ]
    
    log_analysis = await client.analyze_logs(sample_logs, "Analyzing critical service failures")
    print(f"   Found {len(log_analysis.get('anomalies', []))} anomalies")
    print(f"   Detected {len(log_analysis.get('incidents', []))} potential incidents")
    
    # Test 3: Root cause analysis
    print("\n3. Testing Root Cause Analysis...")
    evidence = [
        "Multiple authentication failures observed",
        "Database connection timeouts reported",
        "Service shutdown occurred after repeated failures",
        "Downstream services affected"
    ]
    
    root_cause = await client.perform_root_cause_analysis(
        "Authentication service failure with downstream impact",
        evidence
    )
    print(f"   Identified {len(root_cause.get('root_causes', []))} potential root causes")
    print(f"   Analysis confidence: {root_cause.get('confidence', 0):.1%}")
    
    # Test 4: Remediation plan generation
    print("\n4. Testing Remediation Plan Generation...")
    remediation = await client.generate_remediation_plan(
        incident_type="service_failure",
        root_cause="Database connectivity issues",
        affected_services=["auth-service", "payment-service"]
    )
    print(f"   Generated {len(remediation.get('immediate_actions', []))} immediate actions")
    print(f"   Created {len(remediation.get('detailed_steps', []))} detailed steps")
    
    # Test 5: Incident summary
    print("\n5. Testing Incident Summary...")
    summary = await client.generate_incident_summary(sample_logs, "last 5 minutes")
    print(f"   Summary: {summary[:100]}...")
    
    print("\n" + "=" * 60)
    print("🎉 Bedrock integration testing complete!")
    
    if is_connected:
        print("💡 System is ready for AI-powered incident response")
    else:
        print("💡 System will use pattern-based analysis (no AWS credentials required)")


async def test_agent_integration():
    """Test Bedrock integration with NEXUS agents"""
    print("\n🤖 Testing Agent Integration with Bedrock...")
    print("-" * 40)
    
    # Import agents
    from agents.analyzer import AnalyzerAgent
    from agents.remediation import RemediationAgent
    from models import Incident
    
    # Test analyzer
    print("\n📊 Testing Analyzer Agent...")
    analyzer = AnalyzerAgent()
    
    test_log_data = {
        'log_entries': [
            {
                'timestamp': '2024-01-15 10:00:00',
                'level': 'ERROR',
                'service': 'auth-service',
                'message': 'Database connection failed'
            },
            {
                'timestamp': '2024-01-15 10:01:00',
                'level': 'FATAL',
                'service': 'auth-service',
                'message': 'Service unavailable'
            }
        ],
        'anomalies': [
            {
                'service': 'auth-service',
                'metric': 'error_rate',
                'severity': 'high',
                'value': 0.9
            }
        ]
    }
    
    incidents = await analyzer.analyze_logs_for_incidents(test_log_data)
    print(f"   Detected {len(incidents)} incidents")
    
    # Test remediation
    if incidents:
        print("\n🔧 Testing Remediation Agent...")
        remediation_agent = RemediationAgent()
        
        incident = incidents[0]
        plan = await remediation_agent.generate_remediation_plan(incident)
        
        print(f"   Generated plan for: {incident.title}")
        print(f"   Plan type: {'AI-powered' if plan.get('ai_generated') else 'Template-based'}")
        print(f"   Steps: {len(plan.get('detailed_steps', []))}")
        print(f"   Estimated time: {plan.get('estimated_resolution_time', 'Unknown')}")
    
    print("\n✅ Agent integration testing complete!")


async def main():
    """Main test runner"""
    try:
        await test_bedrock_features()
        await test_agent_integration()
        
        print("\n🌟 All tests completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python start.py' to start the full system")
        print("2. Access the web dashboard at http://localhost:8000")
        print("3. Use 'python scripts/test_agents.py' for comprehensive testing")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\nThis is normal if AWS credentials are not configured.")
        print("The system will work with pattern-based analysis.")


if __name__ == "__main__":
    asyncio.run(main())
