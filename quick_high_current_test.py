"""
Quick High Current Test

Since you heard motor humming, let's test if the issue is simply 
insufficient current magnitude. This tests higher current levels.
"""

import time
from exoboot_1 import ExoBootController, LEFT, RIGHT

PORT = "/dev/ttyACM0"
FIRMWARE_VERSION = "7.2.0"
SIDE = RIGHT
USER_WEIGHT = 90

def main():
    print("=== Quick High Current Test ===")
    print("Testing if higher currents produce noticeable movement")
    
    exoboot = ExoBootController(SIDE, PORT, FIRMWARE_VERSION, USER_WEIGHT, 50, False)
    
    try:
        if not exoboot.connect():
            print("Connection failed")
            return
            
        print("✅ Connected! Testing higher currents...")
        
        # Test progressively higher currents
        test_currents = [5000, 8000, 10000, 12000]
        
        for current in test_currents:
            print(f"\n🔋 Testing {current}mA:")
            response = input(f"Apply {current}mA? (y/n): ")
            if response.lower() != 'y':
                continue
                
            print(f"Applying {current}mA for 3 seconds...")
            exoboot.device.command_motor_current(current * exoboot.side)
            
            # Monitor for 3 seconds
            start_time = time.time()
            baseline_angle = None
            
            while (time.time() - start_time) < 3:
                if exoboot.read_data():
                    if baseline_angle is None:
                        baseline_angle = exoboot.ankle_angle
                    
                    angle_change = exoboot.ankle_angle - baseline_angle
                    print(f"  Current: {exoboot.motor_current:.0f}mA, Angle Change: {angle_change:+.1f}", end='\r')
                
                time.sleep(0.1)
            
            exoboot.device.stop_motor()
            print(f"\nStopped. Did you feel movement? (Note the angle change)")
            time.sleep(1)
        
        print("\n✅ High current test complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        try:
            exoboot.device.stop_motor()
            exoboot.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()