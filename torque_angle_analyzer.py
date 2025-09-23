"""
Simple ExoBoot Torque vs Ankle Angle Plotter

This script creates a torque profile vs ankle angle plot from ExoBoot data.
Just change the DATA_FILE variable below to specify which file to analyze.
"""

import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# CHANGE THIS TO YOUR DATA FILE NAME:
# =====================================================
DATA_FILE = "DataLog/Data2025-09-18_17h10m54s_.csv"

# No MATLAB conversions needed - using raw data directly

def load_and_plot_data(filename):
    """Load data and create torque vs angle plot."""
    
    print(f"Loading data from: {filename}")
    
    # Load the CSV file
    try:
        df = pd.read_csv(filename)
        print(f"Loaded {len(df)} data points")
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    # Check if required columns exist
    if 'ank_torque' not in df.columns or 'ank_ang' not in df.columns:
        print("Error: Required columns 'ank_torque' and 'ank_ang' not found in data file")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Use RAW data (no MATLAB conversions) - same approach as successful ankle plotter
    # Raw torque in mNm
    raw_torque = df['ank_torque']
    
    # Raw ankle angle (encoder units)
    raw_angle = df['ank_ang']
    
    # NO filtering - use all data just like the successful ankle plotter
    torque_filtered = raw_torque
    angle_filtered = raw_angle
    
    print(f"After filtering: {len(torque_filtered)} valid data points")
    
    if len(torque_filtered) == 0:
        print("No valid data points found after filtering!")
        return
    
    # Print raw data statistics
    print(f"\nRaw Data Statistics:")
    print(f"Raw Torque range: {torque_filtered.min():.0f} to {torque_filtered.max():.0f} mNm")
    print(f"Raw Angle range: {angle_filtered.min():.0f} to {angle_filtered.max():.0f} (encoder units)")
    print(f"Mean torque: {torque_filtered.mean():.0f} mNm")
    print(f"Peak |torque|: {torque_filtered.abs().max():.0f} mNm")
    
    # Create the plot - matching successful ankle plotter style
    plt.figure(figsize=(12, 8))
    
    # Scatter plot with better visibility
    plt.scatter(angle_filtered, torque_filtered, alpha=0.6, s=3, color='blue', label='Torque vs Angle')
    
    # Add formatting matching successful ankle plotter
    plt.xlabel('Raw Ankle Angle (encoder units)', fontsize=12, fontweight='bold')
    plt.ylabel('Raw Ankle Torque (mNm)', fontsize=12, fontweight='bold')
    plt.title('ExoBoot: Raw Torque vs Raw Ankle Angle', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Clean up the plot appearance
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    load_and_plot_data(DATA_FILE)