"""
ExoBoot Communication Diagnostic Tool

This script helps diagnose and fix serial communication issues with the ExoBoot.
Based on DebugLog analysis showing serial port communication failures.
"""

import time
import serial
import serial.tools.list_ports
from exoboot_1 import ExoBootController, LEFT, RIGHT

# =====================================================
# CONFIGURATION:
# =====================================================
PORT = "/dev/ttyACM0"
FIRMWARE_VERSION = "7.2.0" 
SIDE = RIGHT
USER_WEIGHT = 90

def check_serial_ports():
    """Check available serial ports and their status"""
    print("=== SERIAL PORT SCAN ===")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("❌ No serial ports found!")
        return None
    
    print("Available serial ports:")
    for port in ports:
        print(f"  🔌 {port.device}")
        print(f"     Description: {port.description}")
        print(f"     Hardware ID: {port.hwid}")
        
        # Test basic connectivity
        try:
            test_serial = serial.Serial(port.device, timeout=1)
            test_serial.close()
            print(f"     Status: ✅ Accessible")
        except Exception as e:
            print(f"     Status: ❌ Error - {e}")
        print()
    
    return ports

def test_basic_serial_communication(port):
    """Test basic serial communication without FlexSEA"""
    print(f"=== BASIC SERIAL TEST: {port} ===")
    
    try:
        # Test different baud rates commonly used by Dephy
        baud_rates = [230400, 115200, 57600, 9600]
        
        for baud in baud_rates:
            print(f"Testing baud rate: {baud}")
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baud,
                    timeout=2,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                
                # Clear any existing data
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Try to read some data
                time.sleep(0.5)
                data = ser.read(50)  # Read up to 50 bytes
                
                if data:
                    print(f"  ✅ Got {len(data)} bytes at {baud} baud")
                    print(f"  Sample data: {data[:20].hex()}")
                else:
                    print(f"  ⚠️  No data at {baud} baud")
                
                ser.close()
                
            except Exception as e:
                print(f"  ❌ Error at {baud} baud: {e}")
        
    except Exception as e:
        print(f"❌ Serial test failed: {e}")

def test_flexsea_connection_with_recovery():
    """Test FlexSEA connection with error recovery"""
    print("=== FLEXSEA CONNECTION WITH RECOVERY ===")
    
    # Try different log levels (0 = most verbose, 6 = no logging)
    log_levels = [6, 3, 0]  # Start with no logging, then moderate, then verbose
    
    for log_level in log_levels:
        print(f"\nTrying connection with log level {log_level}...")
        
        try:
            # Create controller with specific log level
            from flexsea.device import Device
            
            # Try direct Device creation with log level
            device = Device(port=PORT, firmwareVersion=FIRMWARE_VERSION, logLevel=log_level)
            
            print("  Device object created")
            device.open()
            print("  Device opened")
            
            # Try to start streaming with lower frequency
            device.start_streaming(frequency=50)  # Lower frequency
            print("  Streaming started at 50Hz")
            
            # Test reading data
            for i in range(5):
                try:
                    data = device.read()
                    if data:
                        print(f"  ✅ Data read attempt {i+1}: Success")
                        print(f"     Sample keys: {list(data.keys())[:5]}")
                        break
                    else:
                        print(f"  ⚠️  Data read attempt {i+1}: No data")
                except Exception as e:
                    print(f"  ❌ Data read attempt {i+1}: {e}")
                
                time.sleep(0.2)
            
            # Test sending a command
            try:
                device.set_gains(kp=100, ki=32, kd=0, k=0, b=0, ff=0)
                print("  ✅ Command sent successfully")
            except Exception as e:
                print(f"  ❌ Command send failed: {e}")
            
            # Clean shutdown
            device.stop_motor()
            device.close()
            print(f"  ✅ Connection successful with log level {log_level}")
            return True
            
        except Exception as e:
            print(f"  ❌ Connection failed with log level {log_level}: {e}")
            continue
    
    return False

def main():
    """Main communication diagnostic"""
    
    print("=== ExoBoot Communication Diagnostic ===")
    print("This tool diagnoses serial communication issues.")
    print("Based on DebugLog errors showing communication failures.")
    print()
    
    # Step 1: Check serial ports
    ports = check_serial_ports()
    if not ports:
        return
    
    # Step 2: Test basic serial communication
    print(f"\nTesting basic serial communication on {PORT}...")
    test_basic_serial_communication(PORT)
    
    # Step 3: Test FlexSEA connection with recovery
    print(f"\nTesting FlexSEA connection...")
    success = test_flexsea_connection_with_recovery()
    
    # Step 4: Recommendations
    print("\n" + "="*50)
    print("DIAGNOSTIC RECOMMENDATIONS")
    print("="*50)
    
    if success:
        print("✅ Communication working with modified settings!")
        print("\n🔧 Try these fixes in your main code:")
        print("   1. Use logLevel=6 in Device constructor (disable logging)")
        print("   2. Use lower streaming frequency (50Hz instead of 100Hz)")  
        print("   3. Add delays between commands")
        
    else:
        print("❌ Communication still failing")
        print("\n🔧 Hardware troubleshooting steps:")
        print("   1. Check USB cable connection")
        print("   2. Try a different USB port")
        print("   3. Restart the ExoBoot (power cycle)")
        print("   4. Check ExoBoot battery level")
        print("   5. Verify firmware version compatibility")
        
        print("\n🔧 Software troubleshooting steps:")
        print("   1. Try a different USB cable")
        print("   2. Check for other programs using the serial port")
        print("   3. Run with sudo if on Linux")
        print("   4. Try different firmware versions")
        
        print("\n⚡ Emergency fixes to try:")
        print("   - Unplug and replug ExoBoot USB")
        print("   - Close all other FlexSEA programs")
        print("   - Restart your computer")

if __name__ == "__main__":
    main()