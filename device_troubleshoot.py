#!/usr/bin/env python3
"""
Device Troubleshooting Script

A barebones script to connect to a FlexSEA device and get available firmware versions.
Useful for troubleshooting connection and firmware issues.

Usage:
    python device_troubleshoot.py
"""

import sys
import platform
from flexsea.device import Device
from flexsea.utilities.firmware import get_available_firmware_versions


def print_system_info():
    """Print basic system information"""
    print("=" * 50)
    print("SYSTEM INFORMATION")
    print("=" * 50)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python Version: {sys.version}")
    print()


def print_available_firmware_versions():
    """Get and print all available firmware versions"""
    print("=" * 50)
    print("AVAILABLE FIRMWARE VERSIONS")
    print("=" * 50)
    try:
        versions = get_available_firmware_versions()
        print(f"Found {len(versions)} available firmware versions:")
        for version in sorted(versions, reverse=True):  # Show newest first
            print(f"  - {version}")
        print()
        return versions
    except Exception as e:
        print(f"ERROR: Could not retrieve firmware versions: {e}")
        print("This might indicate network connectivity issues.")
        print()
        return []


def test_device_connection():
    """Test basic device connection"""
    print("=" * 50)
    print("DEVICE CONNECTION TEST")
    print("=" * 50)
    
    # Get firmware version from user
    firmware_version = input("Enter firmware version (or press Enter for latest): ").strip()
    if not firmware_version:
        try:
            versions = get_available_firmware_versions()
            firmware_version = sorted(versions, reverse=True)[0]  # Get latest
            print(f"Using latest firmware version: {firmware_version}")
        except:
            firmware_version = "12.0.0"  # Fallback
            print(f"Using fallback firmware version: {firmware_version}")
    
    # Get port from user
    if platform.system().lower() == "windows":
        default_port = "COM3"
        port_hint = "e.g., COM3, COM4, etc."
    else:
        default_port = "/dev/ttyACM0"
        port_hint = "e.g., /dev/ttyACM0, /dev/ttyUSB0, etc."
    
    port = input(f"Enter device port ({port_hint}) or press Enter for {default_port}: ").strip()
    if not port:
        port = default_port
    
    print(f"\nAttempting to connect to device:")
    print(f"  Port: {port}")
    print(f"  Firmware Version: {firmware_version}")
    print()
    
    # Test connection
    try:
        print("Creating device instance...")
        device = Device(port=port, firmwareVersion=firmware_version)
        
        print("Opening connection...")
        device.open()
        
        print("✓ Successfully connected to device!")
        print()
        
        # Try to get some basic device info
        try:
            print("Device Information:")
            print("-" * 30)
            # Note: Actual device info methods may vary by firmware version
            print(f"  Port: {device.port}")
            print(f"  Firmware Version: {device.firmwareVersion}")
            print(f"  Baud Rate: {device.baudRate}")
            print(f"  Device ID: {getattr(device, 'id', 'N/A')}")
            print()
        except Exception as e:
            print(f"Warning: Could not retrieve detailed device info: {e}")
            print()
        
        # Clean shutdown
        print("Closing connection...")
        device.close()
        print("✓ Device connection closed successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ ERROR: Failed to connect to device")
        print(f"Error details: {e}")
        print()
        print("Troubleshooting tips:")
        print("1. Make sure the device is powered on")
        print("2. Check that the correct port is specified")
        print("3. Ensure no other applications are using the device")
        print("4. Try power cycling the device")
        print("5. Check cable connections")
        if platform.system().lower() != "windows":
            print("6. Check device permissions (may need to be in dialout group)")
        return False


def main():
    """Main troubleshooting function"""
    print("FlexSEA Device Troubleshooting Tool")
    print("=" * 50)
    
    if platform.system().lower() == "windows":
        print("WARNING: These demos may not function properly on Windows")
        print("due to timing issues. They work best on Linux.")
        print()
    
    # System info
    print_system_info()
    
    # Available firmware versions
    versions = print_available_firmware_versions()
    
    # Device connection test
    if input("Test device connection? (y/n): ").lower().startswith('y'):
        success = test_device_connection()
        
        if success:
            print("\n" + "=" * 50)
            print("✓ TROUBLESHOOTING COMPLETE - Device connection successful!")
        else:
            print("\n" + "=" * 50)
            print("✗ TROUBLESHOOTING COMPLETE - Device connection failed")
            print("Please check the troubleshooting tips above.")
    else:
        print("Skipping device connection test.")
    
    print("=" * 50)


if __name__ == "__main__":
    main()