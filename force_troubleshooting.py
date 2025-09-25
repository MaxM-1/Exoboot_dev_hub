"""
ExoBoot Force/Torque Troubleshooting Tool

Since communication is working but you can't feel movement, this tool will:
1. Test progressively higher currents
2. Monitor actual torque output  
3. Check mechanical coupling
4. Provide specific recommendations
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

# Progressive current test levels (mA)
TEST_CURRENTS = [1000, 2000, 3000, 5000, 7000, 10000, 12000]
TEST_DURATION = 3  # seconds per test
MONITORING_FREQUENCY = 10  # Hz

def main():
    """Progressive force testing to diagnose torque issues"""
    
    print("=== ExoBoot Force/Torque Troubleshooting ===")
    print("Since communication is working, testing force output progressively.")
    print("Listen and feel for changes at each current level.")
    print()
    
    # Create controller with working communication settings
    exoboot = ExoBootController(
        side=SIDE,
        port=PORT,
        firmware_version=FIRMWARE_VERSION,
        user_weight=USER_WEIGHT,
        frequency=50,  # Working frequency
        should_log=True  # Enable logging to check actual torque
    )
    
    try:
        # Connect
        print("Connecting with fixed communication settings...")
        if not exoboot.connect():
            print("❌ Connection failed!")
            return
        print("✅ Connected successfully!")
        
        # Initial data check
        print("\n=== BASELINE MEASUREMENTS ===")
        time.sleep(1)
        if exoboot.read_data():
            print(f"Baseline Ankle Angle: {exoboot.ankle_angle:.1f}")
            print(f"Baseline Motor Current: {exoboot.motor_current:.0f}mA")
            baseline_angle = exoboot.ankle_angle
        else:
            print("⚠️  Could not read baseline data")
            baseline_angle = 0
        
        # Progressive current testing
        print(f"\n=== PROGRESSIVE CURRENT TESTING ===")
        print("We'll test increasing current levels.")
        print("Report what you feel/hear at each level.")
        input("Make sure your foot is relaxed and press Enter to start...")
        
        results = []
        
        for i, test_current in enumerate(TEST_CURRENTS):
            print(f"\n--- Test {i+1}: {test_current}mA ---")
            
            # Safety check
            if test_current > 8000:
                response = input(f"⚠️  High current test ({test_current}mA). Continue? (y/n): ")
                if response.lower() != 'y':
                    print("Skipping high current tests for safety")
                    break
            
            try:
                # Apply current and monitor
                print(f"Applying {test_current}mA for {TEST_DURATION}s...")
                exoboot.device.command_motor_current(test_current * exoboot.side)
                
                # Monitor data during test
                start_time = time.time()
                max_angle_change = 0
                current_readings = []
                
                while (time.time() - start_time) < TEST_DURATION:
                    if exoboot.read_data():
                        angle_change = abs(exoboot.ankle_angle - baseline_angle)
                        max_angle_change = max(max_angle_change, angle_change)
                        current_readings.append(abs(exoboot.motor_current))
                        
                        print(f"  Current: {exoboot.motor_current:+5.0f}mA, "
                              f"Angle Change: {angle_change:+6.1f}, "
                              f"Max Change: {max_angle_change:6.1f}", end='\r')
                    
                    time.sleep(1.0 / MONITORING_FREQUENCY)
                
                # Stop motor and analyze
                exoboot.device.stop_motor()
                avg_current = sum(current_readings) / len(current_readings) if current_readings else 0
                
                print(f"\n  Results: Max angle change = {max_angle_change:.1f}, Avg current = {avg_current:.0f}mA")
                
                # Store results
                results.append({
                    'commanded_current': test_current,
                    'actual_current': avg_current,
                    'max_angle_change': max_angle_change,
                    'current_achieved': abs(avg_current - test_current) < (test_current * 0.2)  # Within 20%
                })
                
                # Get user feedback
                print("  What did you observe?")
                print("    1 = Nothing felt/heard")
                print("    2 = Motor sound only") 
                print("    3 = Slight resistance felt")
                print("    4 = Clear ankle assistance/resistance")
                
                try:
                    feedback = int(input("  Your rating (1-4): "))
                    results[-1]['user_feedback'] = feedback
                except:
                    results[-1]['user_feedback'] = 1
                
                time.sleep(1)  # Rest between tests
                
            except Exception as e:
                print(f"\n❌ Test {i+1} failed: {e}")
                try:
                    exoboot.device.stop_motor()
                except:
                    pass
                continue
        
        # Analysis and recommendations
        print("\n" + "="*60)
        print("FORCE/TORQUE ANALYSIS RESULTS")
        print("="*60)
        
        # Analyze results
        max_user_feedback = max([r.get('user_feedback', 1) for r in results])
        max_angle_change_overall = max([r['max_angle_change'] for r in results])
        current_control_working = any([r['current_achieved'] for r in results])
        
        print(f"\nTest Summary:")
        print(f"  Max user feedback score: {max_user_feedback}/4")
        print(f"  Max ankle angle change: {max_angle_change_overall:.1f} encoder units")
        print(f"  Current control working: {'✅' if current_control_working else '❌'}")
        
        # Detailed recommendations
        print(f"\n🔍 DIAGNOSIS:")
        
        if max_user_feedback >= 4:
            print("✅ SUCCESS: You can feel clear assistance!")
            print("   - ExoBoot is working properly")
            print("   - Communication and mechanical systems are functional")
            
        elif max_user_feedback >= 3:
            print("⚠️  PARTIAL SUCCESS: Some assistance felt")
            print("   - System is working but may need optimization")
            print("   - Consider: Higher currents, better cable tension, or timing adjustments")
            
        elif max_angle_change_overall > 200:
            print("🤔 SENSOR MOVEMENT WITHOUT FEELING:")
            print("   - Motor is moving ankle joint (sensor detects it)")
            print("   - But you can't feel it - possible causes:")
            print("     • Ankle attachment not tight enough to your foot")
            print("     • Movement too small/slow to perceive")
            print("     • Foot position allowing free movement")
            
        elif current_control_working and max_angle_change_overall < 100:
            print("❌ MECHANICAL DISCONNECTION:")
            print("   - Motor draws commanded current (electrical system OK)")
            print("   - But minimal ankle movement (mechanical issue)")
            print("   - Likely causes:")
            print("     • Cable slipping on pulleys")
            print("     • Loose cable connections")
            print("     • Insufficient cable tension")
            print("     • Mechanical binding somewhere in transmission")
            
        else:
            print("❌ ELECTRICAL/CONTROL ISSUE:")
            print("   - Motor not drawing expected current")
            print("   - Possible causes:")
            print("     • Motor control gains need adjustment")
            print("     • Motor hardware issue")
            print("     • Power supply limitations")
        
        print(f"\n🔧 NEXT STEPS:")
        
        if max_user_feedback < 3:
            print("1. 🔧 Mechanical checks:")
            print("   - Ensure ankle attachment is snug against your foot")
            print("   - Check all cable connections are tight")
            print("   - Verify cables are properly seated in pulleys")
            print("   - Try manual cable tensioning procedure")
            
            print("2. 🎛️  Parameter adjustments:")
            print("   - Try higher current levels (if safe)")
            print("   - Adjust control gains (increase kp, ki)")
            print("   - Consider different ankle positions")
            
            print("3. 🧪 Advanced testing:")
            print("   - Test with foot in different positions")
            print("   - Try holding ankle in specific position")
            print("   - Test with/without shoe")
        
        else:
            print("✅ System appears to be working!")
            print("   - Try running full gait-based assistance")
            print("   - Experiment with different torque profiles")
            print("   - Test during actual walking")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        # Safety cleanup
        try:
            if exoboot.connected and exoboot.device:
                exoboot.device.stop_motor()
                print("\n✅ Motor stopped")
        except:
            pass
        
        if exoboot.disconnect():
            print("✅ Disconnected safely")

if __name__ == "__main__":
    main()