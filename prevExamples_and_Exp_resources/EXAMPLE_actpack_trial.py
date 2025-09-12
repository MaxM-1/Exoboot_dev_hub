VERSION = 4
import platform
import subprocess as sub
import sys
from time import sleep
import keyboard
from math import sqrt
import numpy as np
import matplotlib.pyplot as plt
from flexsea.device import Device
from flexsea.utilities.firmware import get_available_firmware_versions

# Constants from Peng's research
MAX_TORQUE_NORM = 0.225  # Nm/kg from Peng's paper
ZEROING_CURRENT = 1800    # mA
NO_SLACK_CURRENT = 1200   # mA
PEAK_CURRENT = 28000      # mA

# Fixed parameters
ACTUATION_START = 26.0    # % stride
ACTUATION_END = 61.6      # % stride

# Torque conversion functions
def NM_TO_MNM(torque):
    """Convert Nm to mNm"""
    return torque * 1000

def A_TO_MA(current):
    """Convert Amps to mA"""
    return current * 1000

def ankle_torque_to_current(torque, user_weight=70):
    """
    Convert torque (Nm/kg) to current (mA)
    Based on Xiangyu Peng's implementation in Exo_Init.py
    
    Parameters:
    torque - torque in Nm/kg
    user_weight - user weight in kg
    
    Returns:
    current in mA
    """
    # Convert Nm/kg to Nm
    torque_normalized = torque * user_weight
    
    # Convert Nm to mNm
    torque_mnm = NM_TO_MNM(torque_normalized)
    
    # Convert to q-axis current (A)
    kt = 0.14  # q-axis torque constant (Nm/A)
    q_axis_current = torque_mnm / 1000.0 / kt
    
    # Convert to Dephy current (A)
    dephy_current = q_axis_current * sqrt(2) / 0.537
    
    # Convert to mA
    dephy_current_ma = A_TO_MA(dephy_current)
    
    # Ensure current is within limits
    dephy_current_ma = max(min(dephy_current_ma, PEAK_CURRENT), NO_SLACK_CURRENT)
    
    return dephy_current_ma

def generate_cubic_spline_coefficients(rise_time, fall_time):
    """
    Generate cubic spline coefficients for the torque profile
    Based on Peng's implementation in Exo_Init.py
    
    Parameters:
    rise_time - Rise time as percentage of stride
    fall_time - Fall time as percentage of stride
    
    Returns:
    Cubic spline coefficients for ascending and descending portions
    """
    onset_torque = 0
    t0 = ACTUATION_START
    t_peak = ACTUATION_START + rise_time
    t1 = ACTUATION_END
    peak_torque = MAX_TORQUE_NORM
    
    # Coefficients for ascending cubic spline (t0 to t_peak)
    a1 = (2 * (onset_torque - peak_torque)) / (rise_time ** 3)
    b1 = (3 * (peak_torque - onset_torque) * (t_peak + t0)) / (rise_time ** 3)
    c1 = (6 * (onset_torque - peak_torque) * t_peak * t0) / (rise_time ** 3)
    d1 = (t_peak ** 3 * onset_torque - 3 * t0 * t_peak ** 2 * onset_torque + 
          3 * t0 ** 2 * t_peak * peak_torque - t0 ** 3 * peak_torque) / (rise_time ** 3)
    
    # Coefficients for descending cubic spline (t_peak to t1)
    a2 = (peak_torque - onset_torque) / (2 * fall_time ** 3)
    b2 = (3 * (onset_torque - peak_torque) * t1) / (2 * fall_time ** 3)
    c2 = (3 * (peak_torque - onset_torque) * (- t_peak ** 2 + 2 * t1 * t_peak)) / (2 * fall_time ** 3)
    d2 = (2 * peak_torque * t1 ** 3 - 6 * peak_torque * t1 ** 2 * t_peak + 
          3 * peak_torque * t1 * t_peak ** 2 + 3 * onset_torque * t1 * t_peak ** 2 - 
          2 * onset_torque * t_peak ** 3) / (2 * fall_time ** 3)
    
    return (a1, b1, c1, d1), (a2, b2, c2, d2)

def calculate_torque(percent_stride, a1, b1, c1, d1, a2, b2, c2, d2):
    """
    Calculate torque at a given percent of stride based on cubic spline coefficients
    
    Parameters:
    percent_stride - Current position in the gait cycle (as percentage)
    a1, b1, c1, d1 - Coefficients for ascending portion
    a2, b2, c2, d2 - Coefficients for descending portion
    
    Returns:
    Torque value at the given percent of stride
    """
    if percent_stride < ACTUATION_START:
        # Early stance - Position control
        return 0
    elif ACTUATION_START <= percent_stride <= ACTUATION_START + (ACTUATION_END - ACTUATION_START) * 0.5:
        # Ascending curve - Current control with cubic spline
        t = percent_stride
        return a1 * (t**3) + b1 * (t**2) + c1 * t + d1
    elif ACTUATION_START + (ACTUATION_END - ACTUATION_START) * 0.5 < percent_stride <= ACTUATION_END:
        # Descending curve - Current control with cubic spline
        t = percent_stride
        return a2 * (t**3) + b2 * (t**2) + c2 * t + d2
    else:
        # Late stance - Position control
        return 0

def generate_torque_profile(rise_time, user_weight=70, num_points=100):
    """
    Generate a torque profile with the given rise time
    
    Parameters:
    rise_time - Rise time as percentage of stride
    user_weight - User weight in kg
    num_points - Number of points to generate in the profile
    
    Returns:
    time - Array of time points (as percentage of stride)
    torque - Array of torque values at each time point
    """
    # Calculate fall time based on fixed actuation end
    fall_time = ACTUATION_END - (ACTUATION_START + rise_time)
    
    # Generate time points
    time = np.linspace(0, 100, num_points)
    
    # Generate cubic spline coefficients
    (a1, b1, c1, d1), (a2, b2, c2, d2) = generate_cubic_spline_coefficients(rise_time, fall_time)
    
    # Generate torque profile
    torque = np.zeros_like(time)
    for i, t in enumerate(time):
        torque[i] = calculate_torque(t, a1, b1, c1, d1, a2, b2, c2, d2)
    
    return time, torque, (a1, b1, c1, d1), (a2, b2, c2, d2)

def plot_torque_profile(time, torque, rise_time):
    """
    Visualize the torque profile
    
    Parameters:
    time - Array of time points
    torque - Array of torque values
    rise_time - Rise time used to generate the profile
    """
    fall_time = ACTUATION_END - (ACTUATION_START + rise_time)
    peak_time = ACTUATION_START + rise_time
    
    plt.figure(figsize=(10, 6))
    plt.plot(time, torque, 'b-', linewidth=2, label='Torque Profile')
    
    # Add vertical lines for key points
    plt.axvline(x=ACTUATION_START, color='r', linestyle='--', label='Actuation Start (26%)')
    plt.axvline(x=peak_time, color='g', linestyle='--', label=f'Peak Time ({peak_time:.1f}%)')
    plt.axvline(x=ACTUATION_END, color='m', linestyle='--', label='Actuation End (61.6%)')
    
    # Add annotations
    plt.annotate(f'Rise Time: {rise_time:.1f}%', xy=(ACTUATION_START + rise_time/2, MAX_TORQUE_NORM/2),
                 xytext=(ACTUATION_START + rise_time/2, MAX_TORQUE_NORM/2), 
                 ha='center', va='center', bbox=dict(boxstyle='round', fc='lightyellow', alpha=0.8))
    
    plt.annotate(f'Fall Time: {fall_time:.1f}%', xy=(peak_time + fall_time/2, MAX_TORQUE_NORM/2),
                 xytext=(peak_time + fall_time/2, MAX_TORQUE_NORM/2), 
                 ha='center', va='center', bbox=dict(boxstyle='round', fc='lightyellow', alpha=0.8))
    
    plt.xlabel('Time (% Stride)')
    plt.ylabel('Torque (Nm/kg)')
    plt.title(f'Ankle Exoskeleton Torque Profile (Rise Time: {rise_time:.1f}%, Fall Time: {fall_time:.1f}%)')
    plt.grid(True)
    plt.legend(loc='upper right')
    
    # Add regions for better visualization
    plt.axvspan(0, ACTUATION_START, alpha=0.1, color='gray', label='Position Control 1')
    plt.axvspan(ACTUATION_START, peak_time, alpha=0.1, color='green', label='Current Control - Ascending')
    plt.axvspan(peak_time, ACTUATION_END, alpha=0.1, color='blue', label='Current Control - Descending')
    plt.axvspan(ACTUATION_END, 100, alpha=0.1, color='gray', label='Position Control 2')
    
    plt.xlim(0, 100)
    plt.ylim(-0.05, MAX_TORQUE_NORM * 1.1)
    
    plt.show()

def send_torque_profile(device, coeffs, user_weight, num_points=100, command_delay=0.01):
    """
    Send the torque profile to the ActPack device
    
    Parameters:
    device - Device instance
    coeffs - Cubic spline coefficients (a1, b1, c1, d1), (a2, b2, c2, d2)
    user_weight - User weight in kg
    num_points - Number of points to use
    command_delay - Delay between commands (seconds)
    """
    (a1, b1, c1, d1), (a2, b2, c2, d2) = coeffs
    
    # Generate time points for the profile
    stride_percents = np.linspace(0, 100, num_points)
    
    print("Sending torque profile...")
    
    # Send commands for each point in the profile
    for percent in stride_percents:
        # Calculate torque at current stride percent
        torque = calculate_torque(percent, a1, b1, c1, d1, a2, b2, c2, d2)
        
        # Convert torque to current
        current = int(ankle_torque_to_current(torque, user_weight))
        
        # Send current command to device
        device.command_motor_current(current)
        
        # Wait for the specified delay
        sleep(command_delay)
    
    # Stop the motor after sending the profile
    device.stop_motor()
    print("Torque profile complete")

def adjust_torque_curve(device, rise_time, user_weight, gains):
    """
    Adjust the torque curve based on rise time
    
    Parameters:
    device - Device instance
    rise_time - Rise time as percentage of stride
    user_weight - User weight in kg
    gains - Controller gains dictionary
    """
    # Calculate fall time based on fixed actuation end
    fall_time = ACTUATION_END - (ACTUATION_START + rise_time)
    
    # Ensure valid rise and fall times
    if rise_time <= 0 or fall_time <= 0:
        print("Error: Invalid rise or fall time. Adjust parameters.")
        return
    
    # Generate the torque profile
    time, torque, coeffs_asc, coeffs_desc = generate_torque_profile(rise_time, user_weight)
    
    # Visualize the torque profile
    plot_torque_profile(time, torque, rise_time)
    
    # Set gains for the device
    device.set_gains(**gains)
    
    # Prompt user to confirm sending profile
    if input("Send this torque profile to the device? (y/n): ").lower() == 'y':
        send_torque_profile(device, (coeffs_asc, coeffs_desc), user_weight)

def main():
    """Main function to run the script"""
    # Clear terminal
    def clear():
        if platform.system().lower() == "windows":
            sub.run(["cls"], check=True, shell=True)
        else:
            sub.run(["clear"], check=True)
    
    clear()
    
    # Warning for Windows users
    if "windows" == platform.system().lower():
        print("WARNING: these demos may not function properly on Windows")
        print("due to the way the OS handles timing. They are best run on Linux.")
    
    # Confirm device is power cycled
    confirmed = input("Please power cycle the device before continuing. Then hit 'y': ")
    if confirmed.lower() != "y":
        print("Quitting.")
        sys.exit(1)
    
    # Get available firmware versions
    print(get_available_firmware_versions())
    
    # Get device connection information
    port = input("Enter device port (e.g., /dev/ttyACM0): ")
    firmware_version = input("Enter firmware version (e.g., 7.2.0): ")
    
    # Initialize device
    print("Initializing device...")
    device = Device(port=port, firmwareVersion=firmware_version)
    device.open()
    device.start_streaming(frequency=1000)  # 1000 Hz sample rate
    
    # Set current controller gains
    gains = {
        "kp": 40,     # Proportional gain
        "ki": 400,    # Integral gain
        "kd": 0,      # Differential gain
        "k": 0,       # Stiffness (impedance)
        "b": 0,       # Damping (impedance)
        "ff": 128,    # Feed-forward
    }
    
    # Set user weight
    user_weight = float(input("Enter user weight in kg (default 70): ") or "70")
    
    try:
        while True:
            # Get rise time from user
            rise_time = float(input(f"Enter rise time (% stride, between 1 and {ACTUATION_END - ACTUATION_START - 1}): "))
            
            # Validate rise time
            fall_time = ACTUATION_END - (ACTUATION_START + rise_time)
            if rise_time <= 0 or fall_time <= 0:
                print(f"Error: Rise time must be between 1 and {ACTUATION_END - ACTUATION_START - 1}")
                continue
            
            # Adjust torque curve
            adjust_torque_curve(device, rise_time, user_weight, gains)
            
            # Ask if user wants to try another rise time
            if input("Try another rise time? (y/n): ").lower() != 'y':
                break
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
    finally:
        # Stop motor and close device
        print("Stopping motor and closing device...")
        device.stop_motor()
        device.stop_streaming()
        device.close()
        print("Device closed successfully.")

#look at prompt notes 
if __name__ == "__main__":
    main()