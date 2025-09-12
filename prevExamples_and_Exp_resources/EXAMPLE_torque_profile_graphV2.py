import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, FancyArrowPatch
import matplotlib as mpl

# Set basic matplotlib parameters without relying on specific styles
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.size'] = 18          # Increased from 14
mpl.rcParams['axes.labelsize'] = 18     # Increased from 12
mpl.rcParams['axes.titlesize'] = 20     # Increased from 14
mpl.rcParams['xtick.labelsize'] = 14    # Increased from 10
mpl.rcParams['ytick.labelsize'] = 14    # Increased from 10
mpl.rcParams['legend.fontsize'] = 17    # Increased from 14
mpl.rcParams['figure.titlesize'] = 22   # Increased from 16

# Constants from Peng's research
MAX_TORQUE_NORM = 0.225  # Nm/kg - Maximum torque value
ACTUATION_START = 26.0   # % stride - Fixed actuation start timing
ACTUATION_END = 61.6     # % stride - Fixed actuation end timing

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

def calculate_torque(percent_stride, a1, b1, c1, d1, a2, b2, c2, d2, rise_time):
    """
    Calculate torque at a given percent of stride based on cubic spline coefficients
    
    Parameters:
    percent_stride - Current position in the gait cycle (as percentage)
    a1, b1, c1, d1 - Coefficients for ascending portion
    a2, b2, c2, d2 - Coefficients for descending portion
    rise_time - Rise time as percentage of stride (for calculating peak time)
    
    Returns:
    Torque value at the given percent of stride
    """
    peak_time = ACTUATION_START + rise_time
    
    if percent_stride < ACTUATION_START:
        # Early stance - Position control
        return 0
    elif ACTUATION_START <= percent_stride <= peak_time:
        # Ascending curve - Current control with cubic spline
        t = percent_stride
        return a1 * (t**3) + b1 * (t**2) + c1 * t + d1
    elif peak_time < percent_stride <= ACTUATION_END:
        # Descending curve - Current control with cubic spline
        t = percent_stride
        return a2 * (t**3) + b2 * (t**2) + c2 * t + d2
    else:
        # Late stance - Position control
        return 0

def generate_torque_profile(rise_time, num_points=1000):
    """
    Generate a torque profile with the given rise time
    
    Parameters:
    rise_time - Rise time as percentage of stride
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
        torque[i] = calculate_torque(t, a1, b1, c1, d1, a2, b2, c2, d2, rise_time)
    
    return time, torque, fall_time

def create_torque_profile_plot(rise_time, save_path=None, dpi=300, figsize=(12, 8)):
    """
    Create a publication-quality plot of the torque profile
    
    Parameters:
    rise_time - Rise time as percentage of stride
    save_path - Optional path to save the figure
    dpi - Resolution of saved figure
    figsize - Size of the figure in inches
    
    Returns:
    fig, ax - The figure and axes objects
    """
    # Generate torque profile
    time, torque, fall_time = generate_torque_profile(rise_time)
    peak_time = ACTUATION_START + rise_time
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    ax.spines['top'].set_visible(False) #removing top border
    
    # Add grid before plotting data (so it's underneath)
    #ax.grid(True, linestyle='--', alpha=0.3)
    
    # Plot the torque profile
    line, = ax.plot(time, torque, 'b-', linewidth=3.5, label='Torque Profile')
    
    # Add regions for different control phases
    ax.axvspan(0, ACTUATION_START, alpha=0.08, color='lightgray', edgecolor=None)
    ax.axvspan(ACTUATION_START, peak_time, alpha=0.15, color='lightgreen', edgecolor=None)
    ax.axvspan(peak_time, ACTUATION_END, alpha=0.15, color='lightblue', edgecolor=None)
    ax.axvspan(ACTUATION_END, 100, alpha=0.08, color='lightgray', edgecolor=None)
    
    # Add dashed vertical lines for key timing points
    ax.axvline(x=ACTUATION_START, color='red', linestyle='--', linewidth=2)
    ax.axvline(x=peak_time, color='green', linestyle='--', linewidth=2)
    ax.axvline(x=ACTUATION_END, color='red', linestyle='--', linewidth=2)
    
    # Add heel strike vertical line at 100%
    ax.axvline(x=100, color='black', linestyle='-', linewidth=1.5)
    
    # Add horizontal line at peak torque
    ax.axhline(y=MAX_TORQUE_NORM, color='gray', linestyle=':', linewidth=1.5)
    
    # Get torque values at the key points
    actuation_start_torque = 0  # At actuation start, torque is 0
    peak_torque = MAX_TORQUE_NORM  # At peak time, torque is at maximum
    end_timing_torque = 0  # At end timing, torque is 0
    
    # Add dots at key intersection points
    ax.plot(ACTUATION_START, actuation_start_torque, 'ro', markersize=8)
    ax.plot(peak_time, peak_torque, 'go', markersize=8)
    ax.plot(ACTUATION_END, end_timing_torque, 'ro', markersize=8)
    
    # Add annotations
    text_props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
    
    # Actuation timing - raised higher to match bottom of End Timing label
    ax.annotate(f'Actuation\nStart\n{ACTUATION_START}%', 
                xy=(ACTUATION_START, actuation_start_torque), 
                xytext=(15, -0.04),  # Raised to be higher off the x-axis
                ha='center', va='top', fontsize=18, color='red', 
                bbox=text_props, arrowprops=dict(arrowstyle='->', color='red'))
    
    # End Timing - unchanged as requested
    ax.annotate(f'Actuation\nEnd\n{ACTUATION_END}%', 
                xy=(ACTUATION_END, end_timing_torque), 
                xytext=(70, -0.04),  # Kept at original position
                ha='center', va='top', fontsize=18, color='red',
                bbox=text_props, arrowprops=dict(arrowstyle='->', color='red'))
    
    # Rise time and fall time labels
    ax.annotate(f'Rise Time\n{rise_time:.1f}%', 
                xy=(ACTUATION_START + rise_time/2, 0.12), 
                xytext=(ACTUATION_START + rise_time/2, 0.12),
                ha='center', va='center', fontsize=18, bbox=text_props)
    
    ax.annotate(f'Fall Time\n{fall_time:.1f}%', 
                xy=(peak_time + fall_time/2, 0.12), 
                xytext=(peak_time + fall_time/2, 0.12),
                ha='center', va='center', fontsize=18, bbox=text_props)
    
    # Current Control labels - separate and placed below region numbers
    ax.text(ACTUATION_START + rise_time/2, -0.045, 'Current\nControl', ha='center', fontsize=16)
    ax.text(peak_time + fall_time/2, -0.045, 'Current\nControl', ha='center', fontsize=16)
    
    # Peak time annotation - moved to free space as shown in purple annotation
    ax.annotate(f'Peak Torque\n{peak_time:.1f}%', 
                xy=(peak_time, peak_torque), 
                xytext=(38, 0.24),  # Moved to upper middle area
                ha='center', va='center', fontsize=18, color='green',
                bbox=text_props, arrowprops=dict(arrowstyle='->', color='green'))
    
    # Position control labels
    ax.text(ACTUATION_START/2, 0.04, 'Position\nControl', ha='center', fontsize=16)
    ax.text((ACTUATION_END + 100)/2, 0.04, 'Position\nControl', ha='center', fontsize=16)
    
    # Region numbering
    ax.text(ACTUATION_START/2, -0.02, '①', ha='center', fontsize=24, fontweight='bold')
    ax.text(ACTUATION_START + rise_time/2, -0.02, '②', ha='center', fontsize=24, fontweight='bold')
    ax.text(peak_time + fall_time/2, -0.02, '③', ha='center', fontsize=24, fontweight='bold')
    ax.text((ACTUATION_END + 100)/2, -0.02, '④', ha='center', fontsize=24, fontweight='bold')
    
    # Add heel strike annotation with arrow - moved farther from curve as shown in purple annotation
    ax.annotate('Heel Strike', 
                xy=(100, 0), 
                xytext=(93, 0.04),  # Moved to upper right free space
                ha='center', va='center', fontsize=14,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'),
                arrowprops=dict(arrowstyle='->', color='black'))
    
    # Add legend - moved back to top right
    legend_elements = [
        Patch(facecolor='lightgray', alpha=0.5, label='Position Control'),
        Patch(facecolor='lightgreen', alpha=0.5, label='Current Control - Ascending'),
        Patch(facecolor='lightblue', alpha=0.5, label='Current Control - Descending'),
        Patch(facecolor='white', label=f'Peak Torque: {MAX_TORQUE_NORM} Nm/kg')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)
    
    # Set labels and title - adjusted title padding to avoid overlap
    ax.set_xlabel('Time (% stride period)')
    ax.set_ylabel('Desired Ankle Torque (Nm/kg)')
    ax.set_title(f'Ankle Exoskeleton Torque Profile\nRise Time: {rise_time:.1f}%, Fall Time: {fall_time:.1f}%', 
                 pad=20)  # Increased padding to avoid overlap
    
    # Set axis limits
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.1, MAX_TORQUE_NORM * 1.2)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save if requested
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax

def generate_comparison_plot(rise_times, save_path=None, dpi=300, figsize=(14, 10)):
    """
    Create a comparison plot showing multiple torque profiles with different rise times
    
    Parameters:
    rise_times - List of rise times to compare
    save_path - Optional path to save the figure
    dpi - Resolution of saved figure
    figsize - Size of the figure in inches
    
    Returns:
    fig, ax - The figure and axes objects
    """
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    ax.spines['top'].set_visible(False) #removing top border
    
    # Add grid
    #ax.grid(True, linestyle='--', alpha=0.3)
    
    # Color map for different profiles
    colors = plt.cm.viridis(np.linspace(0, 0.8, len(rise_times)))
    
    # Generate and plot each profile
    for i, rise_time in enumerate(rise_times):
        time, torque, fall_time = generate_torque_profile(rise_time)
        peak_time = ACTUATION_START + rise_time
        
        # Plot the torque profile
        ax.plot(time, torque, color=colors[i], linewidth=3.5, 
                label=f'Rise: {rise_time:.1f}%, Fall: {fall_time:.1f}%')
        
        # Add vertical line for peak time
        ax.axvline(x=peak_time, color=colors[i], linestyle=':', linewidth=1.5)
        
        # Add dots at peak points
        ax.plot(peak_time, MAX_TORQUE_NORM, 'o', color=colors[i], markersize=8)
    
    # Add vertical lines for actuation start and end
    ax.axvline(x=ACTUATION_START, color='red', linestyle='--', linewidth=2)
    ax.axvline(x=ACTUATION_END, color='red', linestyle='--', linewidth=2)
    ax.axvline(x=100, color='black', linestyle='-', linewidth=1.5)
    
    # Add annotations - adjusted similarly to single plot
    ax.annotate(f'Actuation Start\n{ACTUATION_START}%', 
                xy=(ACTUATION_START, 0), 
                xytext=(15, -0.02),  # Raised higher
                ha='center', va='top', fontsize=18, color='red',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'),
                arrowprops=dict(arrowstyle='->'))
    
    ax.annotate(f'Actuation End\n{ACTUATION_END}%', 
                xy=(ACTUATION_END, 0), 
                xytext=(75, -0.02),  # Kept at original position
                ha='center', va='top', fontsize=18, color='red',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'),
                arrowprops=dict(arrowstyle='->'))
    
    # Add heel strike annotation
    ax.annotate('Heel Strike', 
                xy=(100, 0), 
                xytext=(85, 0.05),
                ha='center', va='center', fontsize=20,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'),
                arrowprops=dict(arrowstyle='->', color='black'))
    
    # Set labels and title
    ax.set_xlabel('Time (% stride period)', fontsize = 20)
    ax.set_ylabel('Desired Ankle Torque (Nm/kg)', fontsize = 20)
    ax.set_title('Comparison of Ankle Exoskeleton Torque Profiles\nWith Different Rise Times',
                pad=20)
    
    # Add legend
    ax.legend(loc='upper right', framealpha=0.9, fontsize=22)
    
    # Set axis limits
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.05, MAX_TORQUE_NORM * 1.1)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save if requested
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Comparison figure saved to {save_path}")
    
    return fig, ax

def interactive_torque_profile():
    """
    Interactive function to generate torque profiles with different rise times
    """
    print("\n1. Generate single torque profile")
    print("2. Generate comparison of multiple profiles")
    print("3. Exit")
    
    choice = input("Select an option (1-3): ")
    
    if choice == '1':
        # Single profile generation
        while True:
            try:
                rise_time = float(input(f"Enter rise time (% stride, between 1 and {ACTUATION_END - ACTUATION_START - 1}): "))
                
                # Validate rise time
                fall_time = ACTUATION_END - (ACTUATION_START + rise_time)
                if rise_time <= 0 or fall_time <= 0:
                    print(f"Error: Rise time must be between 1 and {ACTUATION_END - ACTUATION_START - 1}")
                    continue
                    
                # Ask for file name if saving
                save_option = input("Save figure? (y/n): ").lower()
                if save_option == 'y':
                    file_name = input("Enter file name (without extension): ")
                    save_path = f"{file_name}.png"
                else:
                    save_path = None
                
                # Create and display plot
                fig, ax = create_torque_profile_plot(rise_time, save_path)
                plt.show()
                
                # Ask if user wants to try another rise time
                if input("Generate another profile? (y/n): ").lower() != 'y':
                    break
                    
            except ValueError:
                print("Please enter a valid number for rise time.")
            except Exception as e:
                print(f"An error occurred: {e}")
    
    elif choice == '2':
        # Comparison plot generation
        try:
            # Get rise times to compare
            rise_times_input = input("Enter rise times to compare (comma-separated, e.g., 5,10,15): ")
            rise_times = [float(x.strip()) for x in rise_times_input.split(',')]
            
            # Validate rise times
            valid_rise_times = []
            for rt in rise_times:
                fall_time = ACTUATION_END - (ACTUATION_START + rt)
                if rt > 0 and fall_time > 0:
                    valid_rise_times.append(rt)
                else:
                    print(f"Warning: Rise time {rt}% is invalid and will be skipped")
            
            if not valid_rise_times:
                print("No valid rise times provided")
                return
            
            # Ask for file name if saving
            save_option = input("Save comparison figure? (y/n): ").lower()
            if save_option == 'y':
                file_name = input("Enter file name (without extension): ")
                save_path = f"{file_name}.png"
            else:
                save_path = None
            
            # Create and display comparison plot
            fig, ax = generate_comparison_plot(valid_rise_times, save_path)
            plt.show()
            
        except ValueError:
            print("Please enter valid numbers for rise times.")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    elif choice == '3':
        return
    
    else:
        print("Invalid choice. Please select 1, 2, or 3.")
        interactive_torque_profile()

if __name__ == "__main__":
    print("=== Ankle Exoskeleton Torque Profile Visualization ===")
    print(f"Fixed Parameters:")
    print(f"  - Actuation Start: {ACTUATION_START}% stride period")
    print(f"  - Actuation End: {ACTUATION_END}% stride period")
    print(f"  - Maximum Torque: {MAX_TORQUE_NORM} Nm/kg\n")
    
    interactive_torque_profile()