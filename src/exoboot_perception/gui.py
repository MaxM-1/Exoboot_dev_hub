"""
Exoboot Experiment GUI Module

This module contains the graphical user interface for the Exoboot experiment on 
rise and fall time perception. It provides a comprehensive interface for experiment 
control, data collection, and real-time visualization.

Classes:
    ExoBootExperimentApp: Main GUI application class

Author: Max M
"""

import csv
import json
import os
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import our controller class and constants
from .controller import ExoBootController
from .constants import *

# Try to import serial port scanning
try:
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not available. Port scanning will be limited.")

try:
    import glob
    GLOB_AVAILABLE = True
except ImportError:
    GLOB_AVAILABLE = False


class ExoBootExperimentApp:
    """
    Main application class for the Exoboot experiment GUI.
    
    This class provides a comprehensive interface for conducting perception
    experiments with the Dephy Exoboot system, including device control,
    parameter adjustment, data collection, and visualization.
    
    Attributes:
        root: Tkinter root window
        left_boot: Controller for left exoboot
        right_boot: Controller for right exoboot
        experiment_running: Flag indicating if experiment is active
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI application.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Exoboot Rise & Fall Time Perception Experiment")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Controller instances
        self.left_boot: Optional[ExoBootController] = None
        self.right_boot: Optional[ExoBootController] = None
        
        # Experiment state
        self.experiment_running = False
        self.controller_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Experiment parameters
        self.participant_id = tk.StringVar(value="P01")
        self.user_weight = tk.DoubleVar(value=DEFAULT_USER_WEIGHT)
        self.current_condition = tk.StringVar(value="Rise Time")
        
        # Torque profile parameters
        self.rise_time = tk.DoubleVar(value=DEFAULT_RISE_TIME)
        self.fall_time = tk.DoubleVar(value=DEFAULT_FALL_TIME)
        self.actuation_start = tk.DoubleVar(value=DEFAULT_ACTUATION_START)
        self.actuation_end = tk.DoubleVar(value=DEFAULT_ACTUATION_END)
        self.peak_torque = tk.DoubleVar(value=DEFAULT_PEAK_TORQUE_NORM)
        
        # Perception test parameters
        self.parameter_delta = tk.DoubleVar(value=DEFAULT_PARAMETER_DELTA)
        self.block_length = tk.IntVar(value=DEFAULT_BLOCK_LENGTH)
        self.current_sweep_count = 0
        self.current_direction = 1  # 1 for increasing, -1 for decreasing
        
        # Status variables
        self.left_status = tk.StringVar(value="Not Connected")
        self.right_status = tk.StringVar(value="Not Connected")
        self.experiment_status = tk.StringVar(value="Ready")
        
        # Data storage
        self.participant_responses: List[Dict[str, Any]] = []
        
        # GUI elements (initialized in create_widgets)
        self.left_port_combo: Optional[ttk.Combobox] = None
        self.right_port_combo: Optional[ttk.Combobox] = None
        self.left_firmware_combo: Optional[ttk.Combobox] = None
        self.right_firmware_combo: Optional[ttk.Combobox] = None
        self.data_tree: Optional[ttk.Treeview] = None
        self.results_tree: Optional[ttk.Treeview] = None
        self.plot_canvas: Optional[FigureCanvasTkAgg] = None
        self.viz_frame: Optional[ttk.Frame] = None
        self.direction_label: Optional[ttk.Label] = None
        self.earlier_button: Optional[ttk.Button] = None
        self.same_button: Optional[ttk.Button] = None
        self.later_button: Optional[ttk.Button] = None
        self.style: Optional[ttk.Style] = None
        
        # Visualization parameters
        self.viz_rise_time = tk.DoubleVar(value=DEFAULT_RISE_TIME)
        self.viz_fall_time = tk.DoubleVar(value=DEFAULT_FALL_TIME)
        
        # Build the UI
        self.create_widgets()
        
        # Initialize hardware detection
        self.scan_ports()
        self.load_firmware_versions()
    
    def create_widgets(self) -> None:
        """Create and layout all the GUI widgets."""
        
        # Create a notebook with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Setup tab
        setup_frame = ttk.Frame(notebook)
        notebook.add(setup_frame, text="Setup")
        
        # Experiment tab
        experiment_frame = ttk.Frame(notebook)
        notebook.add(experiment_frame, text="Experiment")
        
        # Results tab
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="Results")
        
        # Visualization tab
        visualization_frame = ttk.Frame(notebook)
        notebook.add(visualization_frame, text="Visualization")
        
        # Setup the contents of each tab
        self.setup_setup_tab(setup_frame)
        self.setup_experiment_tab(experiment_frame)
        self.setup_results_tab(results_frame)
        self.setup_visualization_tab(visualization_frame)
        
        # Status bar at the bottom
        self.create_status_bar()
    
    def create_status_bar(self) -> None:
        """Create the status bar at the bottom of the window."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        ttk.Label(status_frame, text="Left Boot:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.left_status).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_frame, text="Right Boot:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.right_status).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_frame, text="Experiment:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(status_frame, textvariable=self.experiment_status).pack(side=tk.LEFT)
    
    def setup_setup_tab(self, parent: ttk.Frame) -> None:
        """
        Setup the contents of the Setup tab.
        
        Args:
            parent: Parent frame for the setup widgets
        """
        
        # Connection settings frame
        left_frame = ttk.LabelFrame(parent, text="Connection Settings")
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Left boot settings
        ttk.Label(left_frame, text="Left Boot Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.left_port_combo = ttk.Combobox(left_frame, width=15)
        self.left_port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(left_frame, text="Firmware Version:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.left_firmware_combo = ttk.Combobox(left_frame, width=15)
        self.left_firmware_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Button(left_frame, text="Connect Left Boot", 
                  command=self.connect_left_boot).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Button(left_frame, text="Zero Left Boot", 
                  command=lambda: self.zero_boot("left")).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Right boot settings
        ttk.Label(left_frame, text="Right Boot Port:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.right_port_combo = ttk.Combobox(left_frame, width=15)
        self.right_port_combo.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        ttk.Label(left_frame, text="Firmware Version:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.right_firmware_combo = ttk.Combobox(left_frame, width=15)
        self.right_firmware_combo.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        ttk.Button(left_frame, text="Connect Right Boot", 
                  command=self.connect_right_boot).grid(row=2, column=2, columnspan=2, padx=5, pady=5, sticky="ew")
        ttk.Button(left_frame, text="Zero Right Boot", 
                  command=lambda: self.zero_boot("right")).grid(row=3, column=2, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Scan for ports button
        ttk.Button(left_frame, text="Scan for Ports", 
                  command=self.scan_ports).grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        # Experiment settings frame
        right_frame = ttk.LabelFrame(parent, text="Experiment Settings")
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ttk.Label(right_frame, text="Participant ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(right_frame, textvariable=self.participant_id).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(right_frame, text="User Weight (kg):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(right_frame, textvariable=self.user_weight).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(right_frame, text="Condition:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        condition_combo = ttk.Combobox(right_frame, textvariable=self.current_condition, 
                                     values=["Rise Time", "Fall Time"])
        condition_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(right_frame, text="Parameter Delta (%):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(right_frame, textvariable=self.parameter_delta).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(right_frame, text="Block Length (strides):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(right_frame, textvariable=self.block_length).grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(right_frame, text="Save Settings", 
                  command=self.save_settings).grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(right_frame, text="Load Settings", 
                  command=self.load_settings).grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        # Torque profile parameters frame
        profile_frame = ttk.LabelFrame(parent, text="Torque Profile Parameters")
        profile_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        ttk.Label(profile_frame, text="Actuation Start (%):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(profile_frame, textvariable=self.actuation_start).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(profile_frame, text="Rise Time (%):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(profile_frame, textvariable=self.rise_time).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        ttk.Label(profile_frame, text="Fall Time (%):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(profile_frame, textvariable=self.fall_time).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(profile_frame, text="Actuation End (%):").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(profile_frame, textvariable=self.actuation_end).grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        
        ttk.Label(profile_frame, text="Peak Torque (Nm/kg):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(profile_frame, textvariable=self.peak_torque).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(profile_frame, text="Update Torque Profile", 
                  command=self.update_torque_profile).grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        # Configure grid weights
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
    
    def setup_experiment_tab(self, parent: ttk.Frame) -> None:
        """
        Setup the contents of the Experiment tab.
        
        Args:
            parent: Parent frame for the experiment widgets
        """
        
        # Control panel
        control_frame = ttk.LabelFrame(parent, text="Experiment Control")
        control_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        ttk.Button(control_frame, text="Start Experiment", 
                  command=self.start_experiment).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Stop Experiment", 
                  command=self.stop_experiment).grid(row=0, column=1, padx=5, pady=5)
        
        # Response buttons
        response_frame = ttk.LabelFrame(parent, text="Participant Responses")
        response_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        # Response instruction
        ttk.Label(response_frame, text="When did you feel the torque assistance?").pack(pady=5)
        
        button_frame = ttk.Frame(response_frame)
        button_frame.pack(pady=10)
        
        # Configure button style
        self.style = ttk.Style()
        self.style.configure("Large.TButton", font=("Arial", 14))
        
        self.earlier_button = ttk.Button(button_frame, text="Earlier", style="Large.TButton", 
                                        command=lambda: self.record_response("Earlier"))
        self.earlier_button.grid(row=0, column=0, padx=10, pady=10, ipadx=20, ipady=10)
        
        self.same_button = ttk.Button(button_frame, text="Same", style="Large.TButton", 
                                     command=lambda: self.record_response("Same"))
        self.same_button.grid(row=0, column=1, padx=10, pady=10, ipadx=20, ipady=10)
        
        self.later_button = ttk.Button(button_frame, text="Later", style="Large.TButton", 
                                      command=lambda: self.record_response("Later"))
        self.later_button.grid(row=0, column=2, padx=10, pady=10, ipadx=20, ipady=10)
        
        # Parameter change direction indicator
        self.direction_label = ttk.Label(response_frame, text="", font=("Arial", 12))
        self.direction_label.pack(pady=10)
        
        # Live data display
        data_frame = ttk.LabelFrame(parent, text="Live Data")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create data table
        columns = ("Time", "Gait %", "Left State", "Right State", "Parameter", "Value")
        self.data_tree = ttk.Treeview(data_frame, columns=columns, show="headings")
        
        # Define column headings
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        self.data_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def setup_results_tab(self, parent: ttk.Frame) -> None:
        """
        Setup the contents of the Results tab.
        
        Args:
            parent: Parent frame for the results widgets
        """
        
        # Results display
        results_frame = ttk.LabelFrame(parent, text="Experiment Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create results table
        columns = ("Trial", "Condition", "Parameter", "Value", "Response", "Timestamp")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        
        # Define column headings
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Management buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save Results", command=self.save_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Results", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export to CSV", command=self.export_results).pack(side=tk.LEFT, padx=5)
    
    def setup_visualization_tab(self, parent: ttk.Frame) -> None:
        """
        Setup the contents of the Visualization tab.
        
        Args:
            parent: Parent frame for the visualization widgets
        """
        
        # Settings for visualization
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
        
        ttk.Label(settings_frame, text="Rise Time (%):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(settings_frame, textvariable=self.viz_rise_time).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(settings_frame, text="Fall Time (%):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(settings_frame, textvariable=self.viz_fall_time).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        ttk.Button(settings_frame, text="Generate Plot", 
                  command=self.generate_plot).grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        # Visualization frame
        self.viz_frame = ttk.Frame(parent)
        self.viz_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initially create an empty plot
        self.create_empty_plot()
    
    def create_empty_plot(self) -> None:
        """Create an empty plot in the visualization tab."""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_title("Torque Profile Visualization")
        ax.set_xlabel("Gait Cycle (%)")
        ax.set_ylabel("Torque (Nm/kg)")
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # Embed the plot in the Tkinter window
        self.plot_canvas = FigureCanvasTkAgg(fig, self.viz_frame)
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.plot_canvas.draw()
    
    def scan_ports(self) -> None:
        """Scan for available COM ports."""
        try:
            ports = []
            
            # Platform-specific port detection
            if sys.platform.startswith('win') and SERIAL_AVAILABLE:
                ports = [port.device for port in serial.tools.list_ports.comports()]
            elif sys.platform.startswith('linux') and GLOB_AVAILABLE:
                ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
            
            # Update comboboxes if they exist
            if self.left_port_combo is not None:
                self.left_port_combo['values'] = ports
                if ports:
                    self.left_port_combo.set(ports[0])
            
            if self.right_port_combo is not None:
                self.right_port_combo['values'] = ports
                if len(ports) > 1:
                    self.right_port_combo.set(ports[1])
                elif ports:
                    self.right_port_combo.set(ports[0])
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan for ports: {e}")
    
    def load_firmware_versions(self) -> None:
        """Load available firmware versions from FlexSEA."""
        try:
            # Import here to handle cases where FlexSEA is not available
            from flexsea.utilities.firmware import get_available_firmware_versions
            versions = get_available_firmware_versions()
            
            if versions:
                # Update comboboxes if they exist
                if self.left_firmware_combo is not None:
                    self.left_firmware_combo['values'] = versions
                    self.left_firmware_combo.set(versions[0])
                
                if self.right_firmware_combo is not None:
                    self.right_firmware_combo['values'] = versions
                    self.right_firmware_combo.set(versions[0])
            else:
                messagebox.showwarning("Warning", "No firmware versions found")
        
        except ImportError:
            # FlexSEA not available - set default values
            default_versions = ["1.0.0", "1.1.0", "1.2.0"]
            if self.left_firmware_combo is not None:
                self.left_firmware_combo['values'] = default_versions
                self.left_firmware_combo.set(default_versions[0])
            if self.right_firmware_combo is not None:
                self.right_firmware_combo['values'] = default_versions
                self.right_firmware_combo.set(default_versions[0])
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load firmware versions: {e}")
    
    def connect_left_boot(self) -> None:
        """Connect to the left boot."""
        if self.left_boot is not None:
            messagebox.showinfo("Info", "Left boot already connected")
            return
        
        if self.left_port_combo is None or self.left_firmware_combo is None:
            messagebox.showerror("Error", "GUI not properly initialized")
            return
        
        port = self.left_port_combo.get()
        firmware = self.left_firmware_combo.get()
        
        if not port:
            messagebox.showerror("Error", "No port selected for left boot")
            return
        
        if not firmware:
            messagebox.showerror("Error", "No firmware version selected for left boot")
            return
        
        try:
            self.left_boot = ExoBootController(
                side=LEFT, 
                port=port, 
                firmware_version=firmware,
                user_weight=self.user_weight.get(),
                frequency=DEFAULT_CONTROL_FREQUENCY,
                should_log=True
            )
            
            if self.left_boot.connect():
                self.left_status.set("Connected")
                messagebox.showinfo("Success", "Left boot connected successfully")
            else:
                self.left_boot = None
                messagebox.showerror("Error", "Failed to connect to left boot")
        
        except Exception as e:
            self.left_boot = None
            messagebox.showerror("Error", f"Failed to connect to left boot: {e}")
    
    def connect_right_boot(self) -> None:
        """Connect to the right boot."""
        if self.right_boot is not None:
            messagebox.showinfo("Info", "Right boot already connected")
            return
        
        if self.right_port_combo is None or self.right_firmware_combo is None:
            messagebox.showerror("Error", "GUI not properly initialized")
            return
        
        port = self.right_port_combo.get()
        firmware = self.right_firmware_combo.get()
        
        if not port:
            messagebox.showerror("Error", "No port selected for right boot")
            return
        
        if not firmware:
            messagebox.showerror("Error", "No firmware version selected for right boot")
            return
        
        try:
            self.right_boot = ExoBootController(
                side=RIGHT, 
                port=port, 
                firmware_version=firmware,
                user_weight=self.user_weight.get(),
                frequency=DEFAULT_CONTROL_FREQUENCY,
                should_log=True
            )
            
            if self.right_boot.connect():
                self.right_status.set("Connected")
                messagebox.showinfo("Success", "Right boot connected successfully")
            else:
                self.right_boot = None
                messagebox.showerror("Error", "Failed to connect to right boot")
        
        except Exception as e:
            self.right_boot = None
            messagebox.showerror("Error", f"Failed to connect to right boot: {e}")
    
    def zero_boot(self, side: str) -> None:
        """
        Zero the specified boot.
        
        Args:
            side: "left" or "right"
        """
        if side == "left":
            if self.left_boot is None:
                messagebox.showerror("Error", "Left boot not connected")
                return
            
            if self.left_boot.zero_boot():
                messagebox.showinfo("Success", "Left boot zeroed successfully")
            else:
                messagebox.showerror("Error", "Failed to zero left boot")
        
        else:  # right
            if self.right_boot is None:
                messagebox.showerror("Error", "Right boot not connected")
                return
            
            if self.right_boot.zero_boot():
                messagebox.showinfo("Success", "Right boot zeroed successfully")
            else:
                messagebox.showerror("Error", "Failed to zero right boot")
    
    def save_settings(self) -> None:
        """Save current settings to a JSON file."""
        try:
            settings = {
                'participant_id': self.participant_id.get(),
                'user_weight': self.user_weight.get(),
                'current_condition': self.current_condition.get(),
                'rise_time': self.rise_time.get(),
                'fall_time': self.fall_time.get(),
                'actuation_start': self.actuation_start.get(),
                'actuation_end': self.actuation_end.get(),
                'peak_torque': self.peak_torque.get(),
                'parameter_delta': self.parameter_delta.get(),
                'block_length': self.block_length.get(),
            }
            
            # Ask for filename
            filename = simpledialog.askstring("Save Settings", "Enter settings name:")
            if not filename:
                return
            
            # Create settings directory if it doesn't exist
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            
            # Save to file
            with open(f"{SETTINGS_DIR}/{filename}.json", 'w') as f:
                json.dump(settings, f, indent=4)
            
            messagebox.showinfo("Success", f"Settings saved to {SETTINGS_DIR}/{filename}.json")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def load_settings(self) -> None:
        """Load settings from a JSON file."""
        try:
            # Create settings directory if it doesn't exist
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            
            # Get list of JSON files in settings directory
            files = [f for f in os.listdir(SETTINGS_DIR) if f.endswith('.json')]
            
            if not files:
                messagebox.showinfo("Info", "No settings files found")
                return
            
            # Ask user to select a file
            file = simpledialog.askstring(
                "Load Settings",
                "Enter settings file name:",
                initialvalue=files[0].replace('.json', '')
            )
            
            if not file:
                return
            
            # Add .json extension if not provided
            if not file.endswith('.json'):
                file += '.json'
            
            # Load settings
            with open(f"{SETTINGS_DIR}/{file}", 'r') as f:
                settings = json.load(f)
            
            # Update GUI variables
            self.participant_id.set(settings['participant_id'])
            self.user_weight.set(settings['user_weight'])
            self.current_condition.set(settings['current_condition'])
            self.rise_time.set(settings['rise_time'])
            self.fall_time.set(settings['fall_time'])
            self.actuation_start.set(settings['actuation_start'])
            self.actuation_end.set(settings['actuation_end'])
            self.peak_torque.set(settings['peak_torque'])
            self.parameter_delta.set(settings['parameter_delta'])
            self.block_length.set(settings['block_length'])
            
            messagebox.showinfo("Success", f"Settings loaded from {SETTINGS_DIR}/{file}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")
    
    def update_torque_profile(self) -> None:
        """Update torque profile parameters for both boots."""
        if self.left_boot is None and self.right_boot is None:
            messagebox.showerror("Error", "No boots connected")
            return
        
        try:
            # Update left boot if connected
            if self.left_boot is not None:
                self.left_boot.init_torque_profile(
                    rise_time=self.rise_time.get(),
                    fall_time=self.fall_time.get(),
                    actuation_start=self.actuation_start.get(),
                    actuation_end=self.actuation_end.get(),
                    user_weight=self.user_weight.get(),
                    peak_torque_norm=self.peak_torque.get()
                )
            
            # Update right boot if connected
            if self.right_boot is not None:
                self.right_boot.init_torque_profile(
                    rise_time=self.rise_time.get(),
                    fall_time=self.fall_time.get(),
                    actuation_start=self.actuation_start.get(),
                    actuation_end=self.actuation_end.get(),
                    user_weight=self.user_weight.get(),
                    peak_torque_norm=self.peak_torque.get()
                )
            
            messagebox.showinfo("Success", "Torque profile updated")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update torque profile: {e}")
    
    def start_experiment(self) -> None:
        """Start the experiment."""
        if self.experiment_running:
            messagebox.showinfo("Info", "Experiment already running")
            return
        
        if self.left_boot is None and self.right_boot is None:
            messagebox.showerror("Error", "No boots connected")
            return
        
        # Initialize torque profile before starting
        self.update_torque_profile()
        
        # Reset experiment parameters
        self.current_sweep_count = 0
        self.current_direction = 1
        
        # Update status
        self.experiment_status.set("Running")
        self.experiment_running = True
        
        # Clear previous data
        if self.data_tree is not None:
            for i in self.data_tree.get_children():
                self.data_tree.delete(i)
        
        # Set initial parameter value based on current condition
        if self.current_condition.get() == "Rise Time":
            self.initial_value = self.rise_time.get()
        else:  # Fall Time
            self.initial_value = self.fall_time.get()
        
        # Start the controller thread
        self.stop_event.clear()
        self.controller_thread = threading.Thread(target=self.controller_loop)
        self.controller_thread.daemon = True
        self.controller_thread.start()
        
        # Enable response buttons
        if self.earlier_button is not None:
            self.earlier_button.state(['!disabled'])
        if self.same_button is not None:
            self.same_button.state(['!disabled'])
        if self.later_button is not None:
            self.later_button.state(['!disabled'])
    
    def stop_experiment(self) -> None:
        """Stop the experiment."""
        if not self.experiment_running:
            return
        
        # Signal the controller thread to stop
        self.stop_event.set()
        if self.controller_thread:
            self.controller_thread.join(timeout=2.0)
        
        # Update status
        self.experiment_status.set("Stopped")
        self.experiment_running = False
        
        # Disable response buttons
        if self.earlier_button is not None:
            self.earlier_button.state(['disabled'])
        if self.same_button is not None:
            self.same_button.state(['disabled'])
        if self.later_button is not None:
            self.later_button.state(['disabled'])
        
        # Save data logs
        self.save_data_logs()
        
        messagebox.showinfo("Info", "Experiment stopped")
    
    def controller_loop(self) -> None:
        """Main controller loop for the experiment."""
        try:
            # Wait for 10 strides to stabilize before applying assistance
            if self.left_boot:
                while self.left_boot.num_gait < 10 and not self.stop_event.is_set():
                    self.left_boot.read_data()
                    if self.left_boot.device:
                        self.left_boot.device.command_motor_current(600 * self.left_boot.side)
                    time.sleep(1 / self.left_boot.frequency)
            
            if self.right_boot:
                while self.right_boot.num_gait < 10 and not self.stop_event.is_set():
                    self.right_boot.read_data()
                    if self.right_boot.device:
                        self.right_boot.device.command_motor_current(-600 * self.right_boot.side)
                    time.sleep(1 / self.right_boot.frequency)
            
            print("Starting torque assistance...")
            
            # Main control loop
            counter = 0
            while not self.stop_event.is_set():
                # Run the torque profile on both boots
                if self.left_boot:
                    self.left_boot.run_torque_profile()
                
                if self.right_boot:
                    self.right_boot.run_torque_profile()
                
                # Periodically update the GUI (every 10 iterations to avoid overhead)
                counter += 1
                if counter % 10 == 0:
                    self.root.after_idle(self.update_data_display)
                
                # Sleep to maintain proper control frequency
                time.sleep(1 / DEFAULT_CONTROL_FREQUENCY)
        
        except Exception as e:
            print(f"Error in controller loop: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Controller error: {e}"))
        
        finally:
            # Ensure motors are stopped when the thread exits
            if self.left_boot and self.left_boot.device:
                self.left_boot.device.stop_motor()
            if self.right_boot and self.right_boot.device:
                self.right_boot.device.stop_motor()
    
    def update_data_display(self) -> None:
        """Update the data display in the GUI."""
        if not self.experiment_running or self.data_tree is None:
            return
        
        # Get current data
        timestamp = time.strftime("%H:%M:%S")
        
        left_percent = self.left_boot.percent_gait if self.left_boot else None
        left_state = self.get_boot_state(self.left_boot) if self.left_boot else "N/A"
        
        right_percent = self.right_boot.percent_gait if self.right_boot else None
        right_state = self.get_boot_state(self.right_boot) if self.right_boot else "N/A"
        
        # Determine which percent to use (prefer left if both connected)
        percent = left_percent if left_percent is not None else right_percent
        percent_str = f"{percent:.1f}" if percent is not None else "N/A"
        
        # Get current parameter value
        if self.current_condition.get() == "Rise Time":
            param_name = "Rise Time"
            param_value = (self.left_boot.rise_time if self.left_boot else 
                          (self.right_boot.rise_time if self.right_boot else "N/A"))
        else:  # Fall Time
            param_name = "Fall Time"
            param_value = (self.left_boot.fall_time if self.left_boot else 
                          (self.right_boot.fall_time if self.right_boot else "N/A"))
        
        param_value_str = f"{param_value:.1f}" if isinstance(param_value, (int, float)) else param_value
        
        # Add to tree view
        self.data_tree.insert("", tk.END, values=(
            timestamp, percent_str, left_state, right_state, param_name, param_value_str
        ))
        
        # Limit display to last 100 entries
        while len(self.data_tree.get_children()) > 100:
            self.data_tree.delete(self.data_tree.get_children()[0])
        
        # Scroll to see the last entry
        if self.data_tree.get_children():
            self.data_tree.see(self.data_tree.get_children()[-1])
    
    def get_boot_state(self, boot: Optional[ExoBootController]) -> str:
        """
        Get the current state of a boot based on gait percentage.
        
        Args:
            boot: Boot controller instance
            
        Returns:
            String description of current state
        """
        if not boot or boot.percent_gait < 0:
            return "Waiting"
        
        percent = boot.percent_gait
        peak_time = boot.actuation_start + boot.rise_time
        
        if 0 <= percent <= boot.actuation_start:
            return "Early Stance"
        elif boot.actuation_start < percent <= peak_time:
            return "Torque Increase"
        elif peak_time < percent <= boot.actuation_end:
            return "Torque Decrease"
        else:
            return "Late Stance"
    
    def record_response(self, response: str) -> None:
        """
        Record a participant response and adjust parameters.
        
        Args:
            response: Participant response ("Earlier", "Same", or "Later")
        """
        if not self.experiment_running:
            messagebox.showinfo("Info", "Experiment not running")
            return
        
        # Get current parameter value
        if self.current_condition.get() == "Rise Time":
            param_name = "Rise Time"
            param_value = (self.left_boot.rise_time if self.left_boot else 
                          (self.right_boot.rise_time if self.right_boot else None))
        else:  # Fall Time
            param_name = "Fall Time"
            param_value = (self.left_boot.fall_time if self.left_boot else 
                          (self.right_boot.fall_time if self.right_boot else None))
        
        if param_value is None:
            return
        
        # Record the response
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        trial_num = len(self.participant_responses) + 1
        
        response_data = {
            "trial": trial_num,
            "condition": self.current_condition.get(),
            "parameter": param_name,
            "value": param_value,
            "response": response,
            "timestamp": timestamp,
            "participant_id": self.participant_id.get(),
            "direction": "Increasing" if self.current_direction > 0 else "Decreasing"
        }
        
        self.participant_responses.append(response_data)
        
        # Add to results tree
        if self.results_tree is not None:
            self.results_tree.insert("", tk.END, values=(
                trial_num,
                self.current_condition.get(),
                param_name,
                f"{param_value:.1f}",
                response,
                timestamp
            ))
        
        # Change direction if the response indicates a threshold
        if response != "Same":
            # Change direction if response doesn't match current direction
            should_change = ((response == "Earlier" and self.current_direction > 0) or
                           (response == "Later" and self.current_direction < 0))
            
            if should_change:
                self.current_direction = -self.current_direction
                self.current_sweep_count += 0.5  # Each direction change is half a sweep
                
                # Update direction indicator
                if self.direction_label is not None:
                    self.direction_label.config(
                        text=f"Direction: {'Increasing' if self.current_direction > 0 else 'Decreasing'} "
                             f"({self.current_sweep_count:.1f}/{MAX_NUM_SWEEPS} sweeps)"
                    )
        
        # Apply parameter change
        delta = self.parameter_delta.get() * self.current_direction
        new_value = param_value + delta
        
        # Ensure values stay within reasonable ranges
        if self.current_condition.get() == "Rise Time":
            new_value = max(10.0, min(40.0, new_value))
            
            # Update both boots
            if self.left_boot:
                self.left_boot.init_torque_profile(rise_time=new_value)
            if self.right_boot:
                self.right_boot.init_torque_profile(rise_time=new_value)
            
            # Update UI
            self.rise_time.set(new_value)
        
        else:  # Fall Time
            new_value = max(5.0, min(30.0, new_value))
            
            # Update both boots
            if self.left_boot:
                self.left_boot.init_torque_profile(fall_time=new_value)
            if self.right_boot:
                self.right_boot.init_torque_profile(fall_time=new_value)
            
            # Update UI
            self.fall_time.set(new_value)
        
        # Check if we've completed the max number of sweeps
        if self.current_sweep_count >= MAX_NUM_SWEEPS:
            messagebox.showinfo("Info", f"Completed {MAX_NUM_SWEEPS} sweeps. Experiment ending.")
            self.stop_experiment()
    
    def save_data_logs(self) -> None:
        """Save data logs from both boots."""
        try:
            condition = self.current_condition.get().replace(" ", "_").lower()
            
            if self.left_boot:
                self.left_boot.save_data_log(self.participant_id.get(), condition)
            
            if self.right_boot:
                self.right_boot.save_data_log(self.participant_id.get(), condition)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data logs: {e}")
    
    def save_results(self) -> None:
        """Save experiment results to a JSON file."""
        if not self.participant_responses:
            messagebox.showinfo("Info", "No results to save")
            return
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            condition = self.current_condition.get().replace(" ", "_").lower()
            filename = f"{self.participant_id.get()}_{condition}_{timestamp}.json"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(self.participant_responses, f, indent=4)
            
            messagebox.showinfo("Success", f"Results saved to {filepath}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {e}")
    
    def clear_results(self) -> None:
        """Clear the results display and data."""
        if not self.participant_responses:
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all results?"):
            self.participant_responses = []
            if self.results_tree is not None:
                for i in self.results_tree.get_children():
                    self.results_tree.delete(i)
    
    def export_results(self) -> None:
        """Export results to CSV."""
        if not self.participant_responses:
            messagebox.showinfo("Info", "No results to export")
            return
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(RESULTS_DIR, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            condition = self.current_condition.get().replace(" ", "_").lower()
            filename = f"{self.participant_id.get()}_{condition}_{timestamp}.csv"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # Write data to CSV
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.participant_responses[0].keys())
                writer.writeheader()
                writer.writerows(self.participant_responses)
            
            messagebox.showinfo("Success", f"Results exported to {filepath}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")
    
    def generate_plot(self) -> None:
        """Generate a visualization of the torque profile."""
        if self.viz_frame is None:
            return
        
        try:
            # Get parameters from inputs
            rise_time = self.viz_rise_time.get()
            fall_time = self.viz_fall_time.get()
            actuation_start = self.actuation_start.get()
            actuation_end = self.actuation_end.get()
            peak_torque = self.peak_torque.get()
            
            # Calculate peak time
            peak_time = actuation_start + rise_time
            
            # Create a temporary controller to calculate the torque profile
            temp_controller = ExoBootController(LEFT, "DUMMY", "0.0.0")
            temp_controller.init_torque_profile(
                rise_time=rise_time,
                fall_time=fall_time,
                actuation_start=actuation_start,
                actuation_end=actuation_end,
                peak_torque_norm=peak_torque
            )
            
            # Generate time points for the plot
            time_points = np.linspace(0, 100, 1000)
            torque_values = [temp_controller.calculate_torque(t) for t in time_points]
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(time_points, torque_values, 'b-', linewidth=2, label='Torque Profile')
            
            # Add regions for different control phases
            ax.axvspan(0, actuation_start, alpha=0.08, color='lightgray', edgecolor=None)
            ax.axvspan(actuation_start, peak_time, alpha=0.15, color='lightgreen', edgecolor=None)
            ax.axvspan(peak_time, actuation_end, alpha=0.15, color='lightblue', edgecolor=None)
            ax.axvspan(actuation_end, 100, alpha=0.08, color='lightgray', edgecolor=None)
            
            # Add vertical lines for key timing points
            ax.axvline(x=actuation_start, color='red', linestyle='--', linewidth=2, label='Actuation Start')
            ax.axvline(x=peak_time, color='green', linestyle='--', linewidth=2, label='Peak Time')
            ax.axvline(x=actuation_end, color='red', linestyle='--', linewidth=2, label='Actuation End')
            
            # Add horizontal line at peak torque
            ax.axhline(y=peak_torque, color='gray', linestyle=':', linewidth=1.5, label='Peak Torque')
            
            # Set plot properties
            ax.set_title("Torque Profile Visualization")
            ax.set_xlabel("Gait Cycle (%)")
            ax.set_ylabel("Torque (Nm/kg)")
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.legend(loc='upper right')
            
            # Set axis limits
            ax.set_xlim(0, 100)
            ax.set_ylim(0, peak_torque * 1.1)
            
            # Add annotations for rise and fall time
            ax.annotate(f'Rise Time: {rise_time:.1f}%', 
                       xy=(actuation_start + rise_time/2, peak_torque/2),
                       ha='center', va='center', 
                       bbox=dict(boxstyle='round', fc='lightyellow', alpha=0.8))
            
            ax.annotate(f'Fall Time: {fall_time:.1f}%', 
                       xy=(peak_time + fall_time/2, peak_torque/2),
                       ha='center', va='center', 
                       bbox=dict(boxstyle='round', fc='lightyellow', alpha=0.8))
            
            # Clear previous plot and update
            for widget in self.viz_frame.winfo_children():
                widget.destroy()
            
            self.plot_canvas = FigureCanvasTkAgg(fig, self.viz_frame)
            self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.plot_canvas.draw()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plot: {e}")
    
    def on_closing(self) -> None:
        """Handle window closing."""
        if self.experiment_running:
            self.stop_experiment()
        
        # Disconnect from boots
        if self.left_boot:
            self.left_boot.disconnect()
        
        if self.right_boot:
            self.right_boot.disconnect()
        
        self.root.destroy()


def main() -> None:
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = ExoBootExperimentApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    
    except Exception as e:
        print(f"Fatal error: {e}")
        if tk._default_root:
            messagebox.showerror("Fatal Error", f"Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()