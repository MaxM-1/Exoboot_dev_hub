"""
ExoBoot Cable Tension Diagnostic Tool

This script helps diagnose cable tension and mechanical connection issues.
Use this when motor current is high but ankle torque is zero.
"""

import time
from exoboot_1 import ExoBootController, LEFT, RIGHT

# =====================================================
# CONFIGURATION:
# =====================================================
PORT = "/dev/ttyACM0"
FIRMWARE_VERSION = "7.2.0" 
SIDE = RIGHT
USER_WEIGHT = 90

# Diagnostic parameters
TENSION_CURRENT = 5000  # mA - Higher current for tensioning
DIAGNOSTIC_CURRENT = 2000  # mA - Test current
HOLD_TIME = 3  # seconds

def main():
    """Cable tension diagnostic"""
    
    print("=== ExoBoot Cable Tension Diagnostic ===")
    print("This tool helps diagnose mechanical connection issues.")
    print()
    
    # Create controller
    exoboot = ExoBootController(
        side=SIDE, port=PORT, firmware_version=FIRMWARE_VERSION,
        user_weight=USER_WEIGHT, frequency=100, should_log=True
    )
    
    try:
        # Connect
        print("Connecting...")
        if not exoboot.connect():
            print("✗ Connection failed!")
            return
        print("✓ Connected!")
        
        # Initial readings
        print("\n=== INITIAL STATE ===")
        exoboot.read_data()
        print(f"Initial Ankle Angle: {exoboot.ankle_angle}")
        print(f"Initial Motor Current: {exoboot.motor_current}mA")
        
        # STEP 1: Cable Tensioning
        print("\n=== STEP 1: CABLE TENSIONING ===")
        print("This will apply high current to tension the cables properly.")
        input("Make sure your foot is relaxed and press Enter...")
        
        print(f"Applying {TENSION_CURRENT}mA for cable tensioning...")
        exoboot.device.command_motor_current(TENSION_CURRENT * exoboot.side)
        
        start_time = time.time()
        while (time.time() - start_time) < HOLD_TIME:
            exoboot.read_data()
            print(f"  Current: {exoboot.motor_current:.0f}mA, Angle: {exoboot.ankle_angle:.1f}", end='\r')
            time.sleep(0.1)
        
        exoboot.device.stop_motor()
        print(f"\n✓ Tensioning complete")
        time.sleep(1)
        
        # STEP 2: Mechanical Connection Test
        print("\n=== STEP 2: MECHANICAL CONNECTION TEST ===")
        print("Testing if motor current produces ankle torque...")
        
        # Test positive direction
        print(f"\nTesting positive direction ({DIAGNOSTIC_CURRENT}mA)...")
        input("Keep foot relaxed, feel for ankle movement. Press Enter...")
        
        baseline_angle = None
        exoboot.device.command_motor_current(DIAGNOSTIC_CURRENT * exoboot.side)
        
        start_time = time.time()
        while (time.time() - start_time) < HOLD_TIME:
            exoboot.read_data()
            if baseline_angle is None:
                baseline_angle = exoboot.ankle_angle
            
            angle_change = exoboot.ankle_angle - baseline_angle
            print(f"  Current: {exoboot.motor_current:.0f}mA, Angle Change: {angle_change:.1f}", end='\r')
            time.sleep(0.1)
        
        final_angle_pos = exoboot.ankle_angle
        angle_change_pos = final_angle_pos - baseline_angle
        
        exoboot.device.stop_motor()
        print(f"\nPositive direction result: {angle_change_pos:.1f} angle change")
        time.sleep(1)
        
        # Test negative direction  
        print(f"\nTesting negative direction (-{DIAGNOSTIC_CURRENT}mA)...")
        input("Keep foot relaxed, feel for ankle movement. Press Enter...")
        
        baseline_angle = exoboot.ankle_angle
        exoboot.device.command_motor_current(-DIAGNOSTIC_CURRENT * exoboot.side)
        
        start_time = time.time()
        while (time.time() - start_time) < HOLD_TIME:
            exoboot.read_data()
            angle_change = exoboot.ankle_angle - baseline_angle
            print(f"  Current: {exoboot.motor_current:.0f}mA, Angle Change: {angle_change:.1f}", end='\r')
            time.sleep(0.1)
        
        final_angle_neg = exoboot.ankle_angle
        angle_change_neg = final_angle_neg - baseline_angle
        
        exoboot.device.stop_motor()
        print(f"\nNegative direction result: {angle_change_neg:.1f} angle change")
        
        # DIAGNOSTIC RESULTS
        print("\n" + "="*50)
        print("DIAGNOSTIC RESULTS")
        print("="*50)
        
        total_range = abs(angle_change_pos) + abs(angle_change_neg)
        print(f"Total ankle movement range: {total_range:.1f} encoder units")
        
        if total_range < 50:
            print("❌ PROBLEM DETECTED:")
            print("   - Very little ankle movement despite motor current")
            print("   - Likely cable tension or mechanical connection issue")
            print("\n🔧 RECOMMENDED ACTIONS:")
            print("   1. Check cable connections at ankle and motor")
            print("   2. Inspect for cable slipping on pulleys") 
            print("   3. Verify cable routing through boot structure")
            print("   4. Try higher tensioning current if safe")
            print("   5. Check for mechanical binding or obstructions")
            
        elif total_range < 200:
            print("⚠️  MARGINAL CONNECTION:")
            print("   - Some movement but less than expected")
            print("   - May need better cable tensioning")
            print("\n🔧 RECOMMENDED ACTIONS:")
            print("   1. Repeat tensioning procedure")
            print("   2. Check for partial cable slipping")
            print("   3. Verify proper attachment points")
            
        else:
            print("✅ GOOD MECHANICAL CONNECTION:")
            print("   - Motor current producing ankle movement")
            print("   - Cable tension appears adequate")
            print("\n💡 If you still don't feel assistance during gait:")
            print("   1. Check torque profile timing parameters")
            print("   2. Verify gait detection is working")  
            print("   3. Consider increasing assistance magnitude")
        
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        
    finally:
        # Safety shutdown
        try:
            if exoboot.connected and exoboot.device:
                exoboot.device.stop_motor()
                print("\n✓ Motor stopped")
        except:
            pass
        
        if exoboot.disconnect():
            print("✓ Disconnected")

if __name__ == "__main__":
    main()