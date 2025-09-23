"""
Exoboot Controller for Rise & Fall Time Perception Experiment

This file contains the main controller for the Dephy Exoboot experiment
investigating human perception of rise and fall time parameters in a powered
ankle exoskeleton. Based on research by Xiangyu Peng but using the new FlexSEA API.

Author: Max M & GitHub Copilot
"""

import time
import math
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread, Lock
import json
import os
import csv
from datetime import datetime

from flexsea.device import Device
from flexsea.utilities.firmware import get_available_firmware_versions

# Constants
LEFT = 1
RIGHT = -1

# Current thresholds (in mA)
ZEROING_CURRENT = 1800      # mA - Current used during zeroing process
NO_SLACK_CURRENT = 1200     # mA - Minimum current to keep tension in the cable
PEAK_CURRENT = 28000        # mA - Maximum current (hardware limit)

# Gait detection constants
NUM_GAIT_TIMES_TO_AVERAGE = 3   # Number of gait cycles to average for stride time estimation
ARMED_DURATION_PERCENT = 10      # Percentage of stride duration required for arming
HEELSTRIKE_THRESHOLD_ABOVE = 150 / 32.8  # Gyro threshold for arming (deg/s)
HEELSTRIKE_THRESHOLD_BELOW = -300 / 32.8 # Gyro threshold for triggering (deg/s)

# Default torque profile parameters
DEFAULT_PEAK_TORQUE_NORM = 0.225  # Nm/kg - Maximum normalized torque value
DEFAULT_ACTUATION_START = 26.0    # % stride - Fixed actuation start timing
DEFAULT_ACTUATION_END = 61.6      # % stride - Fixed actuation end timing
DEFAULT_RISE_TIME = 25.3          # % stride - Time from actuation start to peak torque
DEFAULT_FALL_TIME = 10.3          # % stride - Time from peak torque to actuation end

# Conversion functions
def nm_to_mnm(torque):
    """Convert Nm to mNm"""
    return torque * 1000

def a_to_ma(current):
    """Convert Amps to mA"""
    return current * 1000

class ExoBootController:
    """
    Main controller class for the Exoboot experiment.
    This class handles the communication with the exoboot devices and implements 
    the torque profile control based on gait phase detection.
    """
    
    def __init__(self, side, port, firmware_version, user_weight=70, frequency=100, should_log=True):
        """
        Initialize the Exoboot controller.
        
        Args:
            side (int): LEFT (1) or RIGHT (-1)
            port (str): COM port for the device
            firmware_version (str): Firmware version for the device
            user_weight (float): User weight in kg
            frequency (int): Streaming frequency in Hz
            should_log (bool): Whether to log data
        """
        self.side = side
        self.port = port
        self.firmware_version = firmware_version
        self.frequency = frequency
        self.should_log = should_log
        self.user_weight = user_weight
        
        # Status variables
        self.device = None
        self.connected = False
        self.running = False
        
        # Gait detection variables
        self.num_gait = 0
        self.num_gait_in_block = 0
        self.percent_gait = -1
        self.past_stride_times = [-1] * NUM_GAIT_TIMES_TO_AVERAGE
        self.expected_duration = -1
        self.current_duration = -1
        self.heelstrike_timestamp_current = -1
        self.heelstrike_timestamp_previous = -1
        
        # Segmentation variables
        self.segmentation_trigger = False
        self.heelstrike_armed = False
        self.segmentation_arm_threshold = HEELSTRIKE_THRESHOLD_ABOVE
        self.segmentation_trigger_threshold = HEELSTRIKE_THRESHOLD_BELOW
        self.armed_timestamp = -1
        
        # Exo data
        self.current_time = -1
        self.accelx = -1
        self.accely = -1
        self.accelz = -1
        self.gyrox = -1
        self.gyroy = -1
        self.gyroz = -1
        self.ankle_angle = -1
        self.motor_angle = -1
        self.ankle_velocity = -1
        self.motor_current = -1
        
        # Torque profile parameters
        self.actuation_start = DEFAULT_ACTUATION_START
        self.actuation_end = DEFAULT_ACTUATION_END
        self.rise_time = DEFAULT_RISE_TIME
        self.fall_time = DEFAULT_FALL_TIME
        self.peak_torque_norm = DEFAULT_PEAK_TORQUE_NORM
        
        # Spline coefficients
        self.a1 = 0
        self.b1 = 0
        self.c1 = 0
        self.d1 = 0
        self.a2 = 0
        self.b2 = 0
        self.c2 = 0
        self.d2 = 0
        
        # Data logging
        self.data_log = {
            'timestamp': [],
            'percent_gait': [], 
            'onset_timing': [],
            'peak_timing': [], 
            'torque': [], 
            'current': [], 
            'gyroz': [],
            'expected_stride_duration': [],
            'actual_stride_duration': []
        }
        
    def connect(self):
        """Connect to the Exoboot device and start streaming"""
        try:
            print(f"\nConnecting to {'Left' if self.side == LEFT else 'Right'} Exoboot...")
            
            # Connect to the device using the new FlexSEA API
            self.device = Device(port=self.port, firmwareVersion=self.firmware_version)
            self.device.open()
            
            # Start streaming data
            self.device.start_streaming(frequency=self.frequency)
            
            # Set default gains for current control
            self.set_current_control_gains()
            
            self.connected = True
            print(f"{'Left' if self.side == LEFT else 'Right'} Exoboot connected successfully!")
            
            return True
        except Exception as e:
            print(f"Error connecting to {'Left' if self.side == LEFT else 'Right'} Exoboot: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the Exoboot device"""
        if self.connected and self.device:
            try:
                # Stop motor and close device
                self.device.stop_motor()
                time.sleep(0.1)
                self.device.close()
                self.connected = False
                print(f"{'Left' if self.side == LEFT else 'Right'} Exoboot disconnected successfully")
                return True
            except Exception as e:
                print(f"Error disconnecting from {'Left' if self.side == LEFT else 'Right'} Exoboot: {e}")
                return False
        return True
    
    def zero_boot(self):
        """
        Tighten the Exoboot and zero the encoders.
        This is equivalent to Peng's zero_boot function.
        """
        if not self.connected:
            print("Exoboot not connected")
            return False
        
        try:
            print(f"Tightening the {'Left' if self.side == LEFT else 'Right'} Boot...")
            self.set_current_control_gains()
            time.sleep(0.5)
            
            # Apply tightening current
            self.device.command_motor_current(ZEROING_CURRENT * self.side)
            time.sleep(3)
            
            # Read data and zero encoders (store offsets)
            self.read_data()
            
            # Stop motor
            self.device.stop_motor()
            time.sleep(0.1)
            
            print(f"{'Left' if self.side == LEFT else 'Right'} Boot zeroed successfully")
            return True
        except Exception as e:
            print(f"Error zeroing {'Left' if self.side == LEFT else 'Right'} Boot: {e}")
            return False
    
    def set_current_control_gains(self):
        """Set gains for current control mode"""
        if self.connected:
            self.device.set_gains(kp=100, ki=32, kd=0, k=0, b=0, ff=0)
    
    def set_position_control_gains(self):
        """Set gains for position control mode"""
        if self.connected:
            self.device.set_gains(kp=175, ki=50, kd=0, k=0, b=0, ff=0)
    
    def read_data(self):
        """Read and update data from the Exoboot"""
        if not self.connected:
            return False
        
        try:
            # Get the latest data from the device
            data = self.device.read()
            
            # Update IMU data
            self.current_time = time.time() * 1000  # ms
            self.accelx = data['accelx']
            self.accely = data['accely']
            self.accelz = data['accelz']
            self.gyrox = data['gyrox']
            self.gyroy = data['gyroy']
            self.gyroz = data['gyroz']
            
            # Update ankle and motor data
            self.ankle_angle = data['ank_ang']
            self.motor_angle = data['mot_ang']
            self.ankle_velocity = data['ank_vel']
            self.motor_current = data['mot_cur']
            
            # Process heel strike detection
            self.detect_heel_strike()
            
            # Update percent gait
            self.calculate_percent_gait()
            
            return True
        except Exception as e:
            print(f"Error reading data from {'Left' if self.side == LEFT else 'Right'} Exoboot: {e}")
            return False
    
    def detect_heel_strike(self):
        """
        Detect heel strike events based on gyro data.
        This is equivalent to Peng's HeelStrike_Detect function.
        """
        triggered = False
        armed_time = 0
        
        # Condition 1: gyroZ is over a threshold for a fixed time period
        if (self.gyroz >= self.segmentation_arm_threshold) and (not self.heelstrike_armed):
            self.heelstrike_armed = True
            self.armed_timestamp = self.current_time
        
        if self.armed_timestamp != -1:  # != -1 means gyroZ is over threshold and armed
            armed_time = self.current_time - self.armed_timestamp
        
        # Condition 2: gyroZ is below another threshold. Unarmed and potentially trigger heel strike
        if self.heelstrike_armed and (self.gyroz <= self.segmentation_trigger_threshold):
            self.heelstrike_armed = False
            self.armed_timestamp = -1
            
            # Only trigger if armed for long enough and we have an expected duration
            if (self.expected_duration == -1) or (armed_time > ARMED_DURATION_PERCENT / 100 * self.expected_duration):
                triggered = True
                
                # Update heel strike timestamps
                self.heelstrike_timestamp_previous = self.heelstrike_timestamp_current
                self.heelstrike_timestamp_current = self.current_time
                
                # Update expected duration based on previous stride times
                self.update_expected_duration()
                
                # Increment counters
                self.num_gait += 1
                self.num_gait_in_block += 1
                
                # Reset percent gait to start new stride
                self.percent_gait = 0
                
                print(f"{'Left' if self.side == LEFT else 'Right'} Heel Strike Detected! Num: {self.num_gait}, Expected Duration: {self.expected_duration:.0f} ms")
        
        self.segmentation_trigger = triggered
        return triggered
    
    def update_expected_duration(self):
        """
        Update the expected stride duration based on previous stride durations.
        This is equivalent to Peng's update_expected_duration function.
        """
        # Calculate current stride duration
        if self.heelstrike_timestamp_previous != -1:
            self.current_duration = self.heelstrike_timestamp_current - self.heelstrike_timestamp_previous
            
            # If not all values have been replaced
            if -1 in self.past_stride_times:
                # Insert the new value at the beginning and remove the last value
                self.past_stride_times.insert(0, self.current_duration)
                self.past_stride_times.pop()
            # Check if duration is within reasonable bounds
            elif ((self.current_duration <= 1.5 * max(self.past_stride_times)) and 
                  (self.current_duration >= 0.5 * min(self.past_stride_times))):
                # Insert the new value at the beginning and remove the last value
                self.past_stride_times.insert(0, self.current_duration)
                self.past_stride_times.pop()
                # Average the past stride times
                self.expected_duration = sum(self.past_stride_times) / len(self.past_stride_times)
    
    def calculate_percent_gait(self):
        """
        Calculate the current percent of gait cycle.
        This is equivalent to Peng's percent_gait_calc function.
        """
        # If expected_duration is not updated (= -1), no update on percent_gait
        if self.expected_duration != -1 and self.heelstrike_timestamp_current != -1:
            self.percent_gait = 100 * (self.current_time - self.heelstrike_timestamp_current) / self.expected_duration
            
            # If percent_gait is over 100, but still does not detect heel strike, hold it to 100
            if self.percent_gait > 100:
                self.percent_gait = 100
    
    def init_torque_profile(self, rise_time=None, fall_time=None, actuation_start=None, actuation_end=None, user_weight=None, peak_torque_norm=None):
        """
        Initialize the torque profile parameters and calculate spline coefficients.
        This is equivalent to Peng's init_collins_profile function but with more parameters.
        
        Args:
            rise_time (float): Rise time as percentage of stride
            fall_time (float): Fall time as percentage of stride
            actuation_start (float): Actuation start time as percentage of stride
            actuation_end (float): Actuation end time as percentage of stride
            user_weight (float): User weight in kg
            peak_torque_norm (float): Peak normalized torque in Nm/kg
        """
        # Update parameters if provided
        if rise_time is not None:
            self.rise_time = rise_time
        if fall_time is not None:
            self.fall_time = fall_time
        if actuation_start is not None:
            self.actuation_start = actuation_start
        if actuation_end is not None:
            self.actuation_end = actuation_end
        if user_weight is not None:
            self.user_weight = user_weight
        if peak_torque_norm is not None:
            self.peak_torque_norm = peak_torque_norm
        
        # Calculate peak time
        peak_time = self.actuation_start + self.rise_time
        
        # Calculate cubic spline coefficients for ascending curve
        onset_torque = 0
        t0 = self.actuation_start
        t_peak = peak_time
        t1 = self.actuation_end
        peak_torque = self.peak_torque_norm
        
        # Coefficients for ascending cubic spline (t0 to t_peak)
        self.a1 = (2 * (onset_torque - peak_torque)) / (self.rise_time ** 3)
        self.b1 = (3 * (peak_torque - onset_torque) * (t_peak + t0)) / (self.rise_time ** 3)
        self.c1 = (6 * (onset_torque - peak_torque) * t_peak * t0) / (self.rise_time ** 3)
        self.d1 = (t_peak ** 3 * onset_torque - 3 * t0 * t_peak ** 2 * onset_torque + 
                   3 * t0 ** 2 * t_peak * peak_torque - t0 ** 3 * peak_torque) / (self.rise_time ** 3)
        
        # Coefficients for descending cubic spline (t_peak to t1)
        self.a2 = (peak_torque - onset_torque) / (2 * self.fall_time ** 3)
        self.b2 = (3 * (onset_torque - peak_torque) * t1) / (2 * self.fall_time ** 3)
        self.c2 = (3 * (peak_torque - onset_torque) * (- t_peak ** 2 + 2 * t1 * t_peak)) / (2 * self.fall_time ** 3)
        self.d2 = (2 * peak_torque * t1 ** 3 - 6 * peak_torque * t1 ** 2 * t_peak + 
                  3 * peak_torque * t1 * t_peak ** 2 + 3 * onset_torque * t1 * t_peak ** 2 - 
                  2 * onset_torque * t_peak ** 3) / (2 * self.fall_time ** 3)
        
        print(f"{'Left' if self.side == LEFT else 'Right'} Boot Torque Profile Initialized:")
        print(f"  Actuation Start: {self.actuation_start:.1f}%")
        print(f"  Rise Time: {self.rise_time:.1f}%")
        print(f"  Peak Time: {peak_time:.1f}%")
        print(f"  Fall Time: {self.fall_time:.1f}%")
        print(f"  Actuation End: {self.actuation_end:.1f}%")
        print(f"  Peak Torque: {self.peak_torque_norm:.3f} Nm/kg")
    
    def calculate_torque(self, percent_gait):
        """
        Calculate torque at a given percent of stride based on cubic spline coefficients.
        
        Args:
            percent_gait (float): Current position in the gait cycle (as percentage)
            
        Returns:
            float: Torque value at the given percent of stride in Nm/kg
        """
        peak_time = self.actuation_start + self.rise_time
        
        if percent_gait < self.actuation_start:
            # Before actuation start, no torque
            return 0
        elif self.actuation_start <= percent_gait <= peak_time:
            # Ascending curve
            return self.a1 * percent_gait**3 + self.b1 * percent_gait**2 + self.c1 * percent_gait + self.d1
        elif peak_time < percent_gait <= self.actuation_end:
            # Descending curve
            return self.a2 * percent_gait**3 + self.b2 * percent_gait**2 + self.c2 * percent_gait + self.d2
        else:
            # After actuation end, no torque
            return 0
    
    def ankle_torque_to_current(self, torque_mnm):
        """
        Convert ankle torque (in mNm) to motor current (in mA).
        
        Args:
            torque_mnm (float): Torque in mNm
            
        Returns:
            float: Current in mA
        """
        # Convert to q-axis current (A)
        kt = 0.14  # q-axis torque constant (Nm/A)
        q_axis_current = torque_mnm / 1000.0 / kt
        
        # Convert to Dephy current (A)
        dephy_current = q_axis_current * math.sqrt(2) / 0.537
        
        # Convert to mA
        dephy_current_ma = a_to_ma(dephy_current)
        
        # Ensure current is within limits
        dephy_current_ma = max(min(dephy_current_ma, PEAK_CURRENT), NO_SLACK_CURRENT)
        
        return dephy_current_ma
    
    def run_torque_profile(self):
        """
        Run the torque profile based on the current gait phase.
        This is equivalent to Peng's run_collins_profile function.
        """
        if not self.connected:
            return False
        
        # Update data from the device
        self.read_data()
        
        # Check the gait phase and apply appropriate control
        peak_time = self.actuation_start + self.rise_time
        
        try:
            # Early stance - Before actuation start
            if 0 <= self.percent_gait <= self.actuation_start:
                # Position control or minimal current to maintain tension
                self.set_current_control_gains()
                current = NO_SLACK_CURRENT
                self.device.command_motor_current(current * self.side)
                
            # Ascending curve - From actuation start to peak
            elif self.actuation_start < self.percent_gait <= peak_time:
                # Current control with ascending torque curve
                self.set_current_control_gains()
                torque = self.calculate_torque(self.percent_gait)
                torque_nm = torque * self.user_weight
                torque_mnm = nm_to_mnm(torque_nm)
                current = self.ankle_torque_to_current(torque_mnm)
                self.device.command_motor_current(int(current) * self.side)
                
            # Descending curve - From peak to actuation end
            elif peak_time < self.percent_gait <= self.actuation_end:
                # Current control with descending torque curve
                self.set_current_control_gains()
                torque = self.calculate_torque(self.percent_gait)
                torque_nm = torque * self.user_weight
                torque_mnm = nm_to_mnm(torque_nm)
                current = self.ankle_torque_to_current(torque_mnm)
                self.device.command_motor_current(int(current) * self.side)
                
            # Late stance - After actuation end
            else:
                # Position control or minimal current to maintain tension
                self.set_current_control_gains()
                current = NO_SLACK_CURRENT
                self.device.command_motor_current(current * self.side)
            
            # Log data
            if self.should_log and self.percent_gait > 0:
                self.data_log['timestamp'].append(self.current_time)
                self.data_log['percent_gait'].append(self.percent_gait)
                self.data_log['onset_timing'].append(self.actuation_start)
                self.data_log['peak_timing'].append(peak_time)
                
                # Calculate torque for logging (can be 0 if outside actuation period)
                torque = self.calculate_torque(self.percent_gait)
                self.data_log['torque'].append(torque)
                self.data_log['current'].append(current if 'current' in locals() else 0)
                self.data_log['gyroz'].append(self.gyroz)
                self.data_log['expected_stride_duration'].append(self.expected_duration)
                self.data_log['actual_stride_duration'].append(self.current_duration)
            
            return True
        except Exception as e:
            print(f"Error in run_torque_profile for {'Left' if self.side == LEFT else 'Right'} Boot: {e}")
            # Ensure motor is stopped on error
            self.device.stop_motor()
            return False
    
    def save_data_log(self, participant_id, condition_name):
        """
        Save the data log to a CSV file.
        
        Args:
            participant_id (str): Participant ID
            condition_name (str): Condition name or identifier
        """
        if not self.data_log['timestamp']:
            print("No data to save")
            return False
        
        try:
            # Create data directory if it doesn't exist
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            side_str = "left" if self.side == LEFT else "right"
            filename = f"{participant_id}_{side_str}_{condition_name}_{timestamp}.csv"
            filepath = os.path.join(data_dir, filename)
            
            # Write data to CSV
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(self.data_log.keys())
                # Write data rows
                for i in range(len(self.data_log['timestamp'])):
                    row = [self.data_log[key][i] for key in self.data_log.keys()]
                    writer.writerow(row)
            
            print(f"Data saved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
    
    def clear_data_log(self):
        """Clear the data log"""
        for key in self.data_log:
            self.data_log[key] = []
