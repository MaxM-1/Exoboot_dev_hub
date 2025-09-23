"""
Simple Ankle Angle Plotter

This script plots raw ankle angle data from ExoBoot DataLog files.
Just change the DATA_FILE variable to specify which file to plot.
"""

import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# CHANGE THIS TO YOUR DATA FILE NAME:
# =====================================================
DATA_FILE = "DataLog/Data2025-09-23_17h53m12s_.csv"

def plot_ankle_angle(filename):
    """Load data and plot ankle angle over time."""
    
    print(f"Loading data from: {filename}")
    
    # Load the CSV file
    try:
        df = pd.read_csv(filename)
        print(f"Loaded {len(df)} data points")
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    # Check if required columns exist
    if 'ank_ang' not in df.columns or 'state_time' not in df.columns:
        print("Error: Required columns 'ank_ang' and 'state_time' not found in data file")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Use RAW ankle angle data (no conversions) - exactly like LibreOffice
    raw_angle = df['ank_ang']
    
    # Convert time from milliseconds to seconds for readability  
    time_sec = df['state_time'] / 1000.0
    
    # NO filtering - use all data just like LibreOffice does
    angle_filtered = raw_angle
    time_filtered = time_sec
    
    print(f"After filtering: {len(angle_filtered)} valid data points")
    
    if len(angle_filtered) == 0:
        print("No valid data points found after filtering!")
        return
    
    # Print raw data statistics
    print(f"\nRaw Ankle Angle Statistics:")
    print(f"Raw Range: {angle_filtered.min():.0f} to {angle_filtered.max():.0f} (raw units)")
    print(f"Raw Mean: {angle_filtered.mean():.0f} (raw units)")
    print(f"Raw Variation: {angle_filtered.std():.0f} (standard deviation)")
    print(f"Time range: {time_filtered.min():.1f} to {time_filtered.max():.1f} seconds")
    print(f"Duration: {(time_filtered.max() - time_filtered.min()):.1f} seconds")
    
    # Create a single plot that matches LibreOffice output
    plt.figure(figsize=(15, 8))
    
    # Plot exactly like LibreOffice - simple line plot with thicker line
    plt.plot(time_filtered, angle_filtered, 'b-', linewidth=2, label='Ankle Angle')
    
    # Match LibreOffice formatting
    plt.xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    plt.ylabel('Ankle Angle (encoder units)', fontsize=12, fontweight='bold') 
    plt.title('ExoBoot: Ankle Angle Over Time (Matching LibreOffice)', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Set y-axis to match the range you see in LibreOffice (roughly 0-9000)
    plt.ylim(0, 9000)
    
    # Clean up appearance
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    
    print(f"\nPlot complete! This should now match the LibreOffice output.")

if __name__ == "__main__":
    plot_ankle_angle(DATA_FILE)