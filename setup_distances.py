#!/usr/bin/env python3
"""
Setup script for tennis court distance-based sorting

This script helps you set up the distance-based sorting system by:
1. Scraping court addresses
2. Calculating biking distances from your address
3. Setting up the data files needed for distance-based sorting
"""

import os
import sys
import subprocess
from typing import Optional

def check_requirements() -> bool:
    """Check if required dependencies are available"""
    print("🔍 Checking requirements...")
    
    # Check if selenium is available
    try:
        import selenium
        print("✅ Selenium found")
    except ImportError:
        print("❌ Selenium not found!")
        print("💡 Install with: pip install selenium")
        return False
    
    print("✅ Requirements met! (Firefox will be auto-detected)")
    return True

def get_user_address() -> str:
    """Get address from user input"""
    print("\n📍 Please enter your address:")
    
    try:
        user_input = input("Address: ").strip()
        
        if not user_input:
            print("❌ Address is required!")
            return None
        
        return user_input
    except (EOFError, KeyboardInterrupt):
        # Handle non-interactive environments
        print("❌ Address is required!")
        return None

def run_script(script_name: str, args: list = None) -> bool:
    """Run a Python script and return success status"""
    try:
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        
        print(f"🔄 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ Script not found: {script_name}")
        return False

def main():
    """Main setup function"""
    print("🎾 Tennis Court Distance Setup (Web Scraping)")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Get user address
    address = get_user_address()
    if not address:
        print("❌ Setup cancelled - address is required")
        return False
    
    print(f"📍 Using address: {address}")
    
    # Step 1: Calculate distances (no address scraping needed)
    print(f"\n🚴 Step 1: Calculating biking distances...")
    if not run_script('google_maps_distance_calculator.py', [address]):
        print("❌ Failed to calculate distances")
        return False
    
    # Step 2: Verify setup
    print(f"\n✅ Step 2: Verifying setup...")
    
    if os.path.exists('court_distances.json'):
        print("✅ Court distances file created")
    else:
        print("❌ Court distances file missing")
        return False
    
    print(f"\n🎉 Setup complete!")
    print(f"📍 Your tennis courts will now be sorted by biking distance from: {address}")
    print(f"🌐 Using web scraping (completely free!)")
    print(f"\n💡 Usage examples:")
    print(f"   python sf-tennis tomorrow")
    print(f"   python sf-tennis 'next friday'")
    print(f"   python sf-tennis --refresh-distances  # To update distances")
    print(f"   python sf-tennis --address 'New Address' tomorrow  # To use different address")
    print(f"\n⏱️  Note: Distance updates take a few minutes due to web scraping")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
