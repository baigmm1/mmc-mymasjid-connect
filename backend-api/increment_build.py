#!/usr/bin/env python3
"""
Command-line utility to manage build versions.

Usage:
    python increment_build.py              # Show current build
    python increment_build.py increment    # Increment build number
    python increment_build.py reset        # Reset to build #1
    python increment_build.py reset 10     # Reset to build #10
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.build_manager import get_build_manager
from src.models.build import BuildInfo


def show_build(build_info: dict):
    """Display build information in a formatted way."""
    print("\n" + "=" * 60)
    print("Build Version Information")
    print("=" * 60)
    print(f"Build Number:    {build_info['build_number']}")
    print(f"Build Date:      {build_info['build_date']}")
    print(f"Build Timestamp: {build_info['build_timestamp']}")
    print(f"Version:         {build_info['version']}")
    print(f"Full Version:    {build_info['full_version']}")
    print("=" * 60 + "\n")


def main():
    """Main entry point for CLI."""
    build_manager = get_build_manager()
    
    # Parse command line arguments
    if len(sys.argv) == 1:
        # No arguments - show current build
        build_info = build_manager.get_current_build()
        show_build(build_info)
        
    elif sys.argv[1] == "increment":
        # Increment build
        print("\n⚙️  Incrementing build number...")
        build_info = build_manager.increment_build()
        print("✅ Build incremented successfully!")
        show_build(build_info)
        
    elif sys.argv[1] == "reset":
        # Reset build
        if len(sys.argv) > 2:
            try:
                build_number = int(sys.argv[2])
            except ValueError:
                print(f"❌ Error: '{sys.argv[2]}' is not a valid number")
                sys.exit(1)
        else:
            build_number = 1
        
        print(f"\n⚠️  Resetting build number to {build_number}...")
        build_info = build_manager.reset_build(build_number)
        print("✅ Build reset successfully!")
        show_build(build_info)
        
    elif sys.argv[1] in ["-h", "--help", "help"]:
        # Show help
        print(__doc__)
        
    else:
        print(f"❌ Error: Unknown command '{sys.argv[1]}'")
        print("\nUsage:")
        print("  python increment_build.py              # Show current build")
        print("  python increment_build.py increment    # Increment build number")
        print("  python increment_build.py reset        # Reset to build #1")
        print("  python increment_build.py reset 10     # Reset to build #10")
        print("  python increment_build.py help         # Show help")
        sys.exit(1)


if __name__ == "__main__":
    main()
