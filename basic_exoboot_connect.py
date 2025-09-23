"""
Basic ExoBoot Connection Test

This is a minimal script to test basic connectivity with the ExoBoot
using the ExoBootController class from exoboot_1.py.
"""

import time
from exoboot_1 import ExoBootController, LEFT, RIGHT

# =====================================================
# CONFIGURATION - CHANGE THESE VALUES:
# =====================================================
PORT = "/dev/ttyACM0"  # Change to your actual COM port (e.g., "COM3" on Windows, "/dev/ttyACM0" on Linux)
FIRMWARE_VERSION = "7.2.0"  # Change to your firmware version
SIDE = RIGHT  # LEFT or RIGHT 
USER_WEIGHT = 90  # Your weight in kg
# All I should have to do is change these variables

def main():
    """Basic connection test for ExoBoot"""
    
    print("=== Basic ExoBoot Connection Test ===")
    print(f"Port: {PORT}")
    print(f"Side: {'Left' if SIDE == LEFT else 'Right'}")
    print(f"SIDE value: {SIDE}, LEFT value: {LEFT}, RIGHT value: {RIGHT}")
    print(f"Firmware: {FIRMWARE_VERSION}")
    print()
    
    # Create the ExoBoot controller
    exoboot = ExoBootController(
        side=SIDE,
        port=PORT,
        firmware_version=FIRMWARE_VERSION,
        user_weight=USER_WEIGHT,
        frequency=100,
        should_log=False  # No logging for basic test
    )
    
    try:
        # Connect to the boot
        print("Attempting to connect...")
        if exoboot.connect():
            print("✓ Connection successful!")
            
            # Test reading data for a few seconds
            print("\nReading data for 5 seconds...")
            start_time = time.time()
            
            while (time.time() - start_time) < 5:
                if exoboot.read_data():
                    print(f"Time: {exoboot.current_time:.0f}ms, "
                          f"Ankle Angle: {exoboot.ankle_angle:.1f}, "
                          f"Gyro Z: {exoboot.gyroz:.2f}, "
                          f"Motor Current: {exoboot.motor_current:.0f}mA")
                
                time.sleep(0.1)  # Read at 10Hz
            
            print("\n✓ Data reading successful!")
            
        else:
            print("✗ Connection failed!")
            return
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
    
    finally:
        # Always try to disconnect
        print("\nDisconnecting...")
        if exoboot.disconnect():
            print("✓ Disconnected successfully")
        else:
            print("✗ Disconnect failed")

if __name__ == "__main__":
    main()