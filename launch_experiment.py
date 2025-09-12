"""
Exoboot Experiment Launcher

This script launches the exoboot experiment GUI.
"""

import sys
import os
import tkinter as tk
from exoboot_gui import ExoBootExperimentApp

def main():
    """Launch the exoboot experiment application"""
    print("Starting Exoboot Experiment GUI...")
    
    # Create the Tkinter root window
    root = tk.Tk()
    
    # Initialize the application
    app = ExoBootExperimentApp(root)
    
    # Set the window close handler
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the main event loop
    print("GUI initialized. Ready for experiment.")
    root.mainloop()

if __name__ == "__main__":
    main()
