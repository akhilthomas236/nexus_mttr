#!/usr/bin/env python3
"""
Simple startup script for NEXUS MVP
"""

import os
import sys
from pathlib import Path

# Add the nexus-mvp directory to Python path
nexus_dir = Path(__file__).parent
sys.path.insert(0, str(nexus_dir))

if __name__ == "__main__":
    print("🚀 Starting NEXUS MVP...")
    print("Choose an option:")
    print("1. Run full demo (agents + web interface)")
    print("2. Run agents only")
    print("3. Run web interface only")
    print("4. Run tests")
    print("5. Generate sample logs")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        print("Starting full demo...")
        os.system(f"python {nexus_dir}/scripts/run_mvp.py --mode demo")
    
    elif choice == "2":
        print("Starting agents only...")
        os.system(f"python {nexus_dir}/scripts/run_mvp.py --mode agents-only")
    
    elif choice == "3":
        print("Starting web interface only...")
        os.system(f"python {nexus_dir}/scripts/run_mvp.py --mode web-only")
    
    elif choice == "4":
        print("Running tests...")
        os.system(f"python {nexus_dir}/scripts/test_agents.py")
    
    elif choice == "5":
        print("Generating sample logs...")
        os.system(f"python {nexus_dir}/scripts/generate_logs.py")
    
    else:
        print("Invalid choice. Please run again and select 1-5.")
        sys.exit(1)
