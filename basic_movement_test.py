"""
Basic ExoBoot Movement Test
CURRENT CONTROL SCHEME 
This script builds off basic_exoboot_connect.py and adds simple current control
to make the ExoBoot move. Used for troubleshooting connectivity and verifying
the boot can generate movement.
"""

import time
from exoboot_1 import ExoBootController, LEFT, RIGHT

# =====================================================
# CONFIGURATION - CHANGE THESE VALUES:
# =====================================================
PORT = "/dev/ttyACM0"  # Change to your actual COM port
FIRMWARE_VERSION = "7.2.0"  # Change to your firmware version
SIDE = RIGHT  # LEFT or RIGHT 
USER_WEIGHT = 90  # Your weight in kg

# Movement test parameters
TEST_CURRENT = 3000  # mA - Safe test current (adjust as needed)
TEST_DURATION = 2    # seconds - How long to apply current
REST_DURATION = 1    # seconds - Rest between movements

def main():
    """Basic movement test for ExoBoot"""
    
    print("=== Basic ExoBoot Movement Test ===")
    print(f"Port: {PORT}")
    print(f"Side: {'Left' if SIDE == LEFT else 'Right'}")
    print(f"Test Current: {TEST_CURRENT}mA")
    print(f"Test Duration: {TEST_DURATION}s")
    print()
    
    # Create the ExoBoot controller with FIXED communication settings
    exoboot = ExoBootController(
        side=SIDE,
        port=PORT,
        firmware_version=FIRMWARE_VERSION,
        user_weight=USER_WEIGHT,
        frequency=50,  # REDUCED from 100Hz to fix buffer issues
        should_log=False  # No logging for basic test
    )
    
    try:
        # Connect to the boot
        print("Attempting to connect...")
        if not exoboot.connect():
            print("✗ Connection failed!")
            return
        
        print("✓ Connection successful!")
        
        # Optional: Zero the boot (tighten cables)
        input("\nPress Enter to zero/tighten the boot (or Ctrl+C to skip)...")
        print("Zeroing boot...")
        if exoboot.zero_boot():
            print("✓ Boot zeroed successfully!")
        else:
            print("⚠ Boot zeroing failed, but continuing...")
        
        # Test basic data reading
        print(f"\nReading initial data...")
        time.sleep(0.5)
        
        if exoboot.read_data():
            print(f"Initial Ankle Angle: {exoboot.ankle_angle:.1f}")
            print(f"Initial Motor Current: {exoboot.motor_current:.0f}mA")
        
        # Movement Test Sequence
        print(f"\n=== MOVEMENT TEST SEQUENCE ===")
        print("The boot will perform 3 movement cycles:")
        print("1. Apply positive current (plantarflexion)")
        print("2. Rest")  
        print("3. Apply negative current (dorsiflexion)")
        print("4. Rest")
        print("\nWatch for ankle movement and listen for motor sounds.")
        
        input("Press Enter to start movement test (or Ctrl+C to cancel)...")
        
        # Perform movement cycles
        for cycle in range(3):
            print(f"\n--- Cycle {cycle + 1} ---")
            
            # Positive current (plantarflexion direction)
            print(f"Applying +{TEST_CURRENT}mA for {TEST_DURATION}s...")
            exoboot.device.command_motor_current(TEST_CURRENT * exoboot.side)
            
            start_time = time.time()
            while (time.time() - start_time) < TEST_DURATION:
                if exoboot.read_data():
                    print(f"  Ankle: {exoboot.ankle_angle:.1f}, Current: {exoboot.motor_current:.0f}mA", end='\r')
                time.sleep(0.1)
            
            # Stop motor
            print(f"\nStopping motor... (rest {REST_DURATION}s)")
            exoboot.device.stop_motor()
            time.sleep(REST_DURATION)
            
            # Negative current (dorsiflexion direction)  
            print(f"Applying -{TEST_CURRENT}mA for {TEST_DURATION}s...")
            exoboot.device.command_motor_current(-TEST_CURRENT * exoboot.side)
            
            start_time = time.time()
            while (time.time() - start_time) < TEST_DURATION:
                if exoboot.read_data():
                    print(f"  Ankle: {exoboot.ankle_angle:.1f}, Current: {exoboot.motor_current:.0f}mA", end='\r')
                time.sleep(0.1)
            
            # Stop motor
            print(f"\nStopping motor... (rest {REST_DURATION}s)")
            exoboot.device.stop_motor()
            time.sleep(REST_DURATION)
        
        print(f"\n=== MOVEMENT TEST COMPLETE ===")
        print("✓ Movement test completed successfully!")
        print("\nDid you observe:")
        print("- Ankle movement in both directions?")
        print("- Motor sounds during current application?") 
        print("- Changes in ankle angle readings?")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        
    finally:
        # Always ensure motor is stopped and disconnect safely
        print("\nSafety shutdown...")
        try:
            if exoboot.connected and exoboot.device:
                exoboot.device.stop_motor()
                time.sleep(0.2)
                print("✓ Motor stopped")
        except:
            pass
            
        print("Disconnecting...")
        if exoboot.disconnect():
            print("✓ Disconnected successfully")
        else:
            print("✗ Disconnect failed")

if __name__ == "__main__":
    main()
