#!/usr/bin/env python3
"""
Quick setup script to verify Bedrock integration for NEXUS MVP
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_bedrock_setup():
    """Check if Bedrock is properly configured"""
    print("🔧 Checking Amazon Bedrock Setup for NEXUS MVP")
    print("=" * 50)
    
    # Check AWS credentials
    print("\n1. Checking AWS Credentials...")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY") 
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    if aws_key and aws_secret:
        print(f"✅ AWS credentials found")
        print(f"   Region: {aws_region}")
        credentials_available = True
    else:
        print("⚠️  AWS credentials not found in environment")
        print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        credentials_available = False
    
    # Check Bedrock client
    print("\n2. Testing Bedrock Client...")
    try:
        from bedrock_client import get_bedrock_client
        client = get_bedrock_client()
        print(f"✅ Bedrock client initialized")
        print(f"   Model: {client.model_id}")
        print(f"   Available: {client.is_available()}")
    except Exception as e:
        print(f"❌ Error initializing Bedrock client: {e}")
        return False
    
    # Test connection if credentials available
    if credentials_available and client.is_available():
        print("\n3. Testing Bedrock Connection...")
        try:
            import asyncio
            from bedrock_client import test_bedrock_connection
            
            result = asyncio.run(test_bedrock_connection())
            if result:
                print("✅ Bedrock connection successful!")
                print("🎉 NEXUS MVP is ready with full AI capabilities!")
                return True
            else:
                print("⚠️  Bedrock connection failed - using fallback mode")
        except Exception as e:
            print(f"⚠️  Connection test error: {e}")
    
    print("\n📝 Fallback Mode Active:")
    print("   - Pattern-based analysis will be used")
    print("   - Mock AI responses for demonstrations")
    print("   - All core functionality available")
    
    return True

if __name__ == "__main__":
    success = check_bedrock_setup()
    
    if success:
        print(f"\n🚀 Ready to run NEXUS MVP!")
        print("   Run: python start.py")
    else:
        print(f"\n❌ Setup incomplete")
        sys.exit(1)
