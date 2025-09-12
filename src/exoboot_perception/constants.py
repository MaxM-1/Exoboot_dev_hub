"""
Constants for the Exoboot Perception Experiment

This module contains all the constants used throughout the application,
including hardware parameters, default values, and thresholds.
"""

# Device side constants
LEFT = 1
RIGHT = -1

# Current thresholds (in mA)
ZEROING_CURRENT = 1800      # Current used during zeroing process
NO_SLACK_CURRENT = 1200     # Minimum current to keep tension in the cable
PEAK_CURRENT = 28000        # Maximum current (hardware limit)

# Gait detection constants
NUM_GAIT_TIMES_TO_AVERAGE = 3   # Number of gait cycles to average for stride time estimation
ARMED_DURATION_PERCENT = 10     # Percentage of stride duration required for arming
HEELSTRIKE_THRESHOLD_ABOVE = 150 / 32.8  # Gyro threshold for arming (deg/s)
HEELSTRIKE_THRESHOLD_BELOW = -300 / 32.8 # Gyro threshold for triggering (deg/s)

# Default torque profile parameters
DEFAULT_PEAK_TORQUE_NORM = 0.225  # Nm/kg - Maximum normalized torque value
DEFAULT_ACTUATION_START = 26.0    # % stride - Fixed actuation start timing
DEFAULT_ACTUATION_END = 61.6      # % stride - Fixed actuation end timing
DEFAULT_RISE_TIME = 25.3          # % stride - Time from actuation start to peak torque
DEFAULT_FALL_TIME = 10.3          # % stride - Time from peak torque to actuation end

# GUI defaults
DEFAULT_USER_WEIGHT = 70  # kg
DEFAULT_PARAMETER_DELTA = 2.0  # % stride
DEFAULT_BLOCK_LENGTH = 3  # Number of strides per block
MAX_NUM_SWEEPS = 8  # Max number of complete sweeps

# Control frequency
DEFAULT_CONTROL_FREQUENCY = 100  # Hz

# File extensions and directories
DATA_DIR = "data"
RESULTS_DIR = "results"  
SETTINGS_DIR = "settings"
LOG_DIR = "logs"

# Conversion functions
def nm_to_mnm(torque: float) -> float:
    """Convert Nm to mNm"""
    return torque * 1000

def a_to_ma(current: float) -> float:
    """Convert Amps to mA"""
    return current * 1000

def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians"""
    import math
    return degrees * math.pi / 180

def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees"""
    import math
    return radians * 180 / math.pi