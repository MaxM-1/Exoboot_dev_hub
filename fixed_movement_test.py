"""
Fixed ExoBoot Movement Test

This version includes communication error handling and recovery based on 
DebugLog analysis showing serial communication failures.
"""

import time
from flexsea.device import Device

# =====================================================
# CONFIGURATION - CHANGE THESE VALUES:
# =====================================================
PORT = "/dev/ttyACM0"
FIRMWARE_VERSION = "7.2.0"
SIDE = -1  # RIGHT = -1, LEFT = 1

# Movement test parameters
TEST_CURRENT = 3000  # mA - Safe test current
TEST_DURATION = 2    # seconds
REST_DURATION = 1    # seconds

def main():
    """Fixed movement test with communication error handling"""
    
    print("=== Fixed ExoBoot Movement Test ===")
    print("Includes communication error recovery")
    print(f"Port: {PORT}")
    print(f"Side: {'Left' if SIDE == 1 else 'Right'}")
    print()
    
    device = None
    
    try:
        # Step 1: Create device with minimal logging to avoid serial buffer issues
        print("Creating device connection...")
        device = Device(port=PORT, firmwareVersion=FIRMWARE_VERSION, logLevel=6)  # Disable logging
        
        # Step 2: Open with error handling
        print("Opening device...")
        device.open()
        print("✓ Device opened")
        
        # Step 3: Start streaming at lower frequency to reduce data load
        print("Starting data stream at reduced frequency...")
        device.start_streaming(frequency=50)  # Lower frequency = less data = fewer buffer issues
        print("✓ Streaming started at 50Hz")
        
        # Step 4: Wait for initial data stabilization
        print("Waiting for data stabilization...")
        time.sleep(2)
        
        # Step 5: Set gains with error handling
        print("Setting control gains...")
        try:
            device.set_gains(kp=100, ki=32, kd=0, k=0, b=0, ff=0)
            print("✓ Gains set successfully")
        except Exception as e:
            print(f"⚠️ Gain setting failed: {e}, continuing anyway...")
        
        # Step 6: Test basic data reading
        print("Testing data reading...")
        for i in range(5):
            try:
                data = device.read()
                if data and 'ank_ang' in data and 'mot_cur' in data:
                    print(f"✓ Data read {i+1}: Ankle={data['ank_ang']:.1f}, Current={data['mot_cur']:.0f}mA")
                    break
                else:
                    print(f"⚠️ Data read {i+1}: Incomplete data")
            except Exception as e:
                print(f"❌ Data read {i+1} failed: {e}")
            time.sleep(0.2)
        
        # Step 7: Movement test with robust error handling
        print(f"\n=== MOVEMENT TEST ===")
        print("Performing 2 movement cycles with error recovery...")
        
        for cycle in range(2):
            print(f"\n--- Cycle {cycle + 1} ---")
            
            try:
                # Positive current test
                print(f"Applying +{TEST_CURRENT}mA...")
                device.command_motor_current(TEST_CURRENT * SIDE)
                
                # Monitor for movement with error recovery
                start_time = time.time()
                while (time.time() - start_time) < TEST_DURATION:
                    try:
                        data = device.read()
                        if data:
                            print(f"  Ankle: {data.get('ank_ang', 'N/A'):.1f}, "
                                  f"Current: {data.get('mot_cur', 'N/A'):.0f}mA", end='\r')
                    except Exception as e:
                        print(f"\r  Data read error: {e}", end='\r')
                    time.sleep(0.1)
                
                print(f"\nStopping motor...")
                device.stop_motor()
                time.sleep(REST_DURATION)
                
                # Negative current test
                print(f"Applying -{TEST_CURRENT}mA...")
                device.command_motor_current(-TEST_CURRENT * SIDE)
                
                start_time = time.time()
                while (time.time() - start_time) < TEST_DURATION:
                    try:
                        data = device.read()
                        if data:
                            print(f"  Ankle: {data.get('ank_ang', 'N/A'):.1f}, "
                                  f"Current: {data.get('mot_cur', 'N/A'):.0f}mA", end='\r')
                    except Exception as e:
                        print(f"\r  Data read error: {e}", end='\r')
                    time.sleep(0.1)
                
                print(f"\nStopping motor...")
                device.stop_motor()
                time.sleep(REST_DURATION)
                
            except Exception as e:
                print(f"\n❌ Cycle {cycle + 1} failed: {e}")
                try:
                    device.stop_motor()
                except:
                    pass
                continue
        
        print(f"\n✅ Movement test completed!")
        print("\nWhat to check:")
        print("- Did you feel ankle movement?")
        print("- Did you hear motor sounds?")
        print("- Did ankle angle readings change?")
        print("- Check DebugLog for fewer communication errors")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check USB connection")
        print("2. Restart ExoBoot")
        print("3. Try different USB port")
        print("4. Run communication_diagnostic.py")
        
    finally:
        # Robust cleanup
        print("\nSafety shutdown...")
        if device:
            try:
                device.stop_motor()
                print("✓ Motor stopped")
                time.sleep(0.5)
                device.close()
                print("✓ Device closed")
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")

if __name__ == "__main__":
    main()