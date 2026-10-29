"""
Test script for build version endpoint.

This script tests the build version management system by:
1. Importing and initializing the build manager
2. Getting current build info
3. Incrementing the build
4. Displaying version information
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.build_manager import get_build_manager
from src.models.build import BuildInfo

def test_build_manager():
    """Test build manager functionality."""
    print("=" * 60)
    print("Testing Build Version Management System")
    print("=" * 60)
    
    # Get build manager instance
    build_manager = get_build_manager()
    
    # Get current build info
    print("\n1. Current Build Information:")
    print("-" * 60)
    current_build = build_manager.get_current_build()
    for key, value in current_build.items():
        print(f"  {key:20s}: {value}")
    
    # Validate with Pydantic model
    print("\n2. Validating with Pydantic Model:")
    print("-" * 60)
    try:
        build_info = BuildInfo(**current_build)
        print(f"  ✓ Model validation successful")
        print(f"  JSON output: {build_info.model_dump_json(indent=2)}")
    except Exception as e:
        print(f"  ✗ Model validation failed: {e}")
    
    # Test increment
    print("\n3. Testing Build Increment:")
    print("-" * 60)
    response = input("  Increment build number? (y/n): ").strip().lower()
    if response == 'y':
        new_build = build_manager.increment_build()
        print("  Build incremented successfully!")
        for key, value in new_build.items():
            print(f"  {key:20s}: {value}")
    else:
        print("  Skipped increment.")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_build_manager()
