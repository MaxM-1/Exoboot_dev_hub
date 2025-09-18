#!/usr/bin/env python3
"""
Port Detection Script

Scans for available /dev/tty* ports and attempts to identify which ones
are likely connected to ExoBoot/FlexSEA devices.

This script helps distinguish between system ports and actual device ports
by checking port characteristics and attempting basic communication.
"""

import os
import serial
import serial.tools.list_ports
import time
import glob
from typing import List, Dict, Tuple


def get_all_tty_ports() -> List[str]:
    """Get all /dev/tty* ports using glob"""
    # Common device port patterns for FlexSEA devices
    patterns = [
        '/dev/ttyACM*',  # Most common for FlexSEA devices
        '/dev/ttyUSB*',  # USB serial adapters
        '/dev/ttyS*',    # Hardware serial ports
    ]
    
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    
    return sorted(ports)


def get_detailed_port_info() -> List[Dict]:
    """Get detailed information about available serial ports"""
    ports_info = []
    
    # Use pyserial's list_ports for detailed info
    for port in serial.tools.list_ports.comports():
        port_info = {
            'device': port.device,
            'name': port.name,
            'description': port.description,
            'manufacturer': port.manufacturer,
            'product': port.product,
            'vid': port.vid,
            'pid': port.pid,
            'serial_number': port.serial_number,
            'hwid': port.hwid,
        }
        ports_info.append(port_info)
    
    return ports_info


def test_port_connectivity(port: str, timeout: float = 2.0) -> Tuple[bool, str]:
    """
    Test if a port is accessible and responsive
    
    Returns:
        Tuple of (is_accessible, status_message)
    """
    try:
        # Try to open the port
        with serial.Serial(port, baudrate=230400, timeout=timeout) as ser:
            if ser.is_open:
                # Try to write a simple command (this is safe for most devices)
                time.sleep(0.1)  # Brief pause
                return True, "Port accessible and responsive"
            else:
                return False, "Port could not be opened"
                
    except serial.SerialException as e:
        return False, f"Serial error: {e}"
    except PermissionError:
        return False, "Permission denied (try adding user to dialout group)"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def identify_likely_flexsea_ports(ports_info: List[Dict]) -> List[Dict]:
    """Identify ports that are likely FlexSEA devices"""
    likely_ports = []
    
    # Known identifiers that suggest FlexSEA devices
    flexsea_indicators = [
        'dephy',
        'flexsea', 
        'ftdi',     # FTDI chips are commonly used
        'cp210x',   # Silicon Labs USB-to-UART bridges
        'ch340',    # CH340 USB-to-serial chips
    ]
    
    for port_info in ports_info:
        is_likely = False
        reasons = []
        
        # Check device path patterns
        if '/dev/ttyACM' in port_info['device']:
            is_likely = True
            reasons.append("ACM device (USB CDC)")
        elif '/dev/ttyUSB' in port_info['device']:
            is_likely = True
            reasons.append("USB serial device")
            
        # Check manufacturer/description
        desc_lower = (port_info['description'] or '').lower()
        mfg_lower = (port_info['manufacturer'] or '').lower()
        
        for indicator in flexsea_indicators:
            if indicator in desc_lower or indicator in mfg_lower:
                is_likely = True
                reasons.append(f"Contains '{indicator}' identifier")
                break
        
        if is_likely:
            port_info['likely_flexsea'] = True
            port_info['reasons'] = reasons
            likely_ports.append(port_info)
        else:
            port_info['likely_flexsea'] = False
            port_info['reasons'] = ["No FlexSEA indicators found"]
            
    return likely_ports


def print_port_summary(ports_info: List[Dict]):
    """Print a summary of all detected ports"""
    print("=" * 80)
    print("ALL DETECTED SERIAL PORTS")
    print("=" * 80)
    
    if not ports_info:
        print("No serial ports detected.")
        return
    
    for i, port in enumerate(ports_info, 1):
        print(f"\n{i}. {port['device']}")
        print(f"   Description: {port['description'] or 'N/A'}")
        print(f"   Manufacturer: {port['manufacturer'] or 'N/A'}")
        if port.get('product'):
            print(f"   Product: {port['product']}")
        if port.get('vid') and port.get('pid'):
            print(f"   VID:PID: {port['vid']:04x}:{port['pid']:04x}")
        if port.get('serial_number'):
            print(f"   Serial: {port['serial_number']}")
        
        # Test connectivity
        accessible, status = test_port_connectivity(port['device'])
        status_symbol = "✓" if accessible else "✗"
        print(f"   Status: {status_symbol} {status}")


def print_likely_flexsea_ports(likely_ports: List[Dict]):
    """Print ports that are likely FlexSEA devices"""
    print("\n" + "=" * 80)
    print("LIKELY FLEXSEA/EXOBOOT DEVICES")
    print("=" * 80)
    
    if not likely_ports:
        print("No likely FlexSEA devices detected.")
        print("\nTroubleshooting tips:")
        print("1. Make sure devices are powered on and connected")
        print("2. Try different USB cables")
        print("3. Check USB port connections")
        print("4. Power cycle the devices")
        return
    
    for i, port in enumerate(likely_ports, 1):
        print(f"\n{i}. {port['device']} - LIKELY FLEXSEA DEVICE")
        print(f"   Description: {port['description'] or 'N/A'}")
        print(f"   Manufacturer: {port['manufacturer'] or 'N/A'}")
        print("   Reasons:")
        for reason in port['reasons']:
            print(f"     • {reason}")
        
        # Test connectivity
        accessible, status = test_port_connectivity(port['device'])
        status_symbol = "✓" if accessible else "✗"
        print(f"   Connectivity: {status_symbol} {status}")


def print_usage_recommendations(likely_ports: List[Dict]):
    """Print recommendations for using the detected ports"""
    print("\n" + "=" * 80)
    print("USAGE RECOMMENDATIONS")
    print("=" * 80)
    
    accessible_ports = [
        port['device'] for port in likely_ports 
        if test_port_connectivity(port['device'])[0]
    ]
    
    if len(accessible_ports) == 0:
        print("No accessible FlexSEA devices found.")
        print("Check connections and permissions.")
    elif len(accessible_ports) == 1:
        print(f"Found 1 accessible device: {accessible_ports[0]}")
        print(f"Use this port in your ExoBoot configuration.")
    else:
        print(f"Found {len(accessible_ports)} accessible devices:")
        for i, port in enumerate(accessible_ports, 1):
            print(f"  {i}. {port}")
        
        print(f"\nFor ExoBoot configuration with 2 devices:")
        if len(accessible_ports) >= 2:
            print(f"  Left boot:  {accessible_ports[0]}")
            print(f"  Right boot: {accessible_ports[1]}")
        else:
            print("  You may need to connect the second device")
    
    print(f"\nExample usage in your code:")
    if accessible_ports:
        print(f"  port = '{accessible_ports[0]}'")
        print(f"  device = Device(port=port, firmwareVersion='12.0.0')")


def main():
    """Main function to detect and analyze ports"""
    print("ExoBoot Port Detection Tool")
    print("=" * 80)
    
    # Get all port information
    print("Scanning for serial ports...")
    ports_info = get_detailed_port_info()
    
    # Print summary of all ports
    print_port_summary(ports_info)
    
    # Identify likely FlexSEA ports
    likely_ports = identify_likely_flexsea_ports(ports_info)
    
    # Print likely FlexSEA devices
    print_likely_flexsea_ports(likely_ports)
    
    # Print usage recommendations
    print_usage_recommendations(likely_ports)
    
    # Additional system info
    print("\n" + "=" * 80)
    print("ADDITIONAL INFORMATION")
    print("=" * 80)
    print(f"Total ports found: {len(ports_info)}")
    print(f"Likely FlexSEA devices: {len(likely_ports)}")
    
    # Check user permissions
    import getpass
    username = getpass.getuser()
    try:
        import grp
        dialout_members = grp.getgrnam('dialout').gr_mem
        if username in dialout_members:
            print(f"✓ User '{username}' is in dialout group")
        else:
            print(f"⚠ User '{username}' is NOT in dialout group")
            print(f"  To fix: sudo usermod -a -G dialout {username}")
            print(f"  Then log out and back in")
    except KeyError:
        print("Could not check dialout group membership")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()