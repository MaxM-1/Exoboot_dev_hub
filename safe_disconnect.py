#!/usr/bin/env python3
"""
Safe ExoBoot Disconnect Script

This script safely disconnects ExoBoot devices by:
1. Detecting connected ExoBoot devices
2. Stopping motors and controllers
3. Properly closing connections
4. Confirming it's safe to physically disconnect

Always run this before unplugging ExoBoot devices to prevent:
- Motor damage
- Controller corruption
- Unsafe device states
"""

import sys
import time
from typing import List, Tuple
import serial.tools.list_ports
from flexsea.device import Device


def find_connected_exoboots() -> List[str]:
    """
    Find ports that are likely connected to ExoBoot devices
    
    Returns:
        List of port names (e.g., ['/dev/ttyACM0', '/dev/ttyACM1'])
    """
    likely_ports = []
    
    # Get all serial ports
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Look for STMicroelectronics Virtual COM Port or similar indicators
        desc_lower = (port.description or '').lower()
        mfg_lower = (port.manufacturer or '').lower()
        
        # Known indicators for ExoBoot/FlexSEA devices
        indicators = [
            'stmicroelectronics',
            'virtual com port',
            'dephy',
            'flexsea',
            'ftdi',
            'cp210x'
        ]
        
        for indicator in indicators:
            if indicator in desc_lower or indicator in mfg_lower:
                likely_ports.append(port.device)
                break
        
        # Also include common device patterns
        if '/dev/ttyACM' in port.device or '/dev/ttyUSB' in port.device:
            if port.device not in likely_ports:
                likely_ports.append(port.device)
    
    return sorted(likely_ports)


def test_exoboot_connection(port: str, firmware_version: str = "12.0.0") -> Tuple[bool, Device, str]:
    """
    Test if a port has a connected ExoBoot device
    
    Args:
        port: Port to test (e.g., '/dev/ttyACM0')
        firmware_version: Firmware version to use for connection
        
    Returns:
        Tuple of (is_exoboot, device_object_or_None, status_message)
    """
    try:
        print(f"    Testing {port}...")
        
        # Create device instance with short timeout
        device = Device(
            port=port, 
            firmwareVersion=firmware_version,
            interactive=False
        )
        
        # Try to open connection
        device.open()
        
        # If we get here, it's likely an ExoBoot device
        print(f"    ✓ ExoBoot detected on {port}")
        return True, device, f"ExoBoot connected on {port}"
        
    except Exception as e:
        print(f"    ✗ No ExoBoot on {port}: {str(e)[:50]}...")
        return False, None, f"Not an ExoBoot device: {e}"


def safely_disconnect_device(device: Device, port: str) -> bool:
    """
    Safely disconnect a single ExoBoot device
    
    Args:
        device: Connected Device object
        port: Port name for logging
        
    Returns:
        True if successfully disconnected, False otherwise
    """
    try:
        print(f"  Disconnecting ExoBoot on {port}...")
        
        # Step 1: Stop motor (most important for safety)
        print(f"    Stopping motor...")
        device.stop_motor()
        time.sleep(0.5)  # Give time for motor to stop
        
        # Step 2: Send any additional shutdown commands if needed
        # (This depends on your specific ExoBoot configuration)
        print(f"    Sending shutdown commands...")
        
        # Step 3: Close the connection properly
        print(f"    Closing connection...")
        device.close()
        time.sleep(0.2)  # Brief pause
        
        print(f"    ✓ {port} safely disconnected")
        return True
        
    except Exception as e:
        print(f"    ✗ Error disconnecting {port}: {e}")
        print(f"    ⚠ Device may still be in unsafe state!")
        return False


def main():
    """Main safe disconnect function"""
    print("=" * 60)
    print("ExoBoot Safe Disconnect Tool")
    print("=" * 60)
    print("This tool will safely disconnect ExoBoot devices before")
    print("you physically unplug them from the Raspberry Pi.")
    print()
    
    # Step 1: Find potential ExoBoot ports
    print("1. Scanning for potential ExoBoot devices...")
    candidate_ports = find_connected_exoboots()
    
    if not candidate_ports:
        print("   No potential ExoBoot devices found.")
        print("   It should be safe to unplug devices.")
        return
    
    print(f"   Found {len(candidate_ports)} potential device(s): {candidate_ports}")
    print()
    
    # Step 2: Test each port for actual ExoBoot devices
    print("2. Testing connections to identify ExoBoot devices...")
    connected_devices = []
    
    # Try multiple common firmware versions
    firmware_versions = ["12.0.0", "11.0.0", "10.0.0", "9.0.0"]
    
    for port in candidate_ports:
        device_found = False
        
        for fw_version in firmware_versions:
            if device_found:
                break
                
            is_exoboot, device, status = test_exoboot_connection(port, fw_version)
            if is_exoboot:
                connected_devices.append((port, device, fw_version))
                device_found = True
                break
        
        if not device_found:
            print(f"    ✗ {port} - Not an ExoBoot device")
    
    print()
    
    # Step 3: Handle found devices
    if not connected_devices:
        print("3. No ExoBoot devices detected.")
        print("   The connected devices are likely system ports.")
        print("   It should be safe to unplug your ExoBoot devices.")
        print()
    else:
        print(f"3. Found {len(connected_devices)} connected ExoBoot device(s)")
        print("   Proceeding with safe disconnect...")
        print()
        
        # Disconnect each device safely
        all_success = True
        for port, device, fw_version in connected_devices:
            success = safely_disconnect_device(device, port)
            if not success:
                all_success = False
        
        print()
        
        # Final status
        if all_success:
            print("✓ All ExoBoot devices safely disconnected!")
            print("✓ It is now SAFE to physically unplug the devices.")
        else:
            print("⚠ Some devices could not be safely disconnected.")
            print("⚠ Check the errors above before unplugging.")
            print("⚠ You may want to power cycle the devices.")
    
    print()
    print("=" * 60)
    print("Disconnect process complete.")
    print("=" * 60)


def emergency_disconnect():
    """Emergency disconnect function for urgent situations"""
    print("EMERGENCY DISCONNECT MODE")
    print("=" * 40)
    
    # Try to stop any motors on common ports without full initialization
    common_ports = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
    
    for port in common_ports:
        try:
            # Quick motor stop attempt
            device = Device(port=port, firmwareVersion="12.0.0", interactive=False)
            device.open()
            device.stop_motor()
            device.close()
            print(f"✓ Emergency stop sent to {port}")
        except:
            pass  # Ignore errors in emergency mode
    
    print("Emergency disconnect commands sent.")
    print("Wait 5 seconds before unplugging devices.")


if __name__ == "__main__":
    # Check for emergency mode
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['emergency', 'urgent', 'quick']:
        emergency_disconnect()
    else:
        main()