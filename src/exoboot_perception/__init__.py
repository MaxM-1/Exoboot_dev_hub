"""
Exoboot Perception Experiment Package

A comprehensive package for conducting human perception experiments using the 
Dephy Exoboot powered ankle exoskeleton, focusing on rise and fall time 
parameters in torque profiles.

Author: Max M
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Max M"
__email__ = "your.email@example.com"  # Replace with your actual email

from .controller import ExoBootController
from .gui import ExoBootExperimentApp
from .constants import *

__all__ = [
    "ExoBootController",
    "ExoBootExperimentApp",
    "LEFT",
    "RIGHT",
]