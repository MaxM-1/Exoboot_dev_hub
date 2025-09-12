# Exoboot Rise & Fall Time Perception Experiment

This codebase is designed for conducting experiments on human perception of rise and fall time parameters in a powered ankle exoskeleton. The experiment is based on research by Xiangyu Peng but focuses on different parameters.

## Overview

The experiment investigates how humans perceive changes in the rise and fall time parameters of the torque profile in a Dephy Exoboot powered ankle exoskeleton. The software provides:

1. Direct control of Dephy Exoboot devices using the FlexSEA API
2. Real-time gait phase detection using IMU data
3. Customizable torque profiles with adjustable parameters
4. A GUI for experiment control and participant response recording
5. Data logging and visualization capabilities

## Requirements

- Python 3.7+
- FlexSEA Python package (included in the Actuator-Package-develop folder)
- Tkinter for the GUI
- Matplotlib for visualization
- NumPy for numerical operations

## Setup

1. Ensure the FlexSEA Python package is installed:
   ```
   pip install -e ./Actuator-Package-develop
   ```

2. Install other required packages:
   ```
   pip install matplotlib numpy
   ```

3. Connect the Dephy Exoboot devices to your computer.

## Usage

1. Run the experiment launcher:
   ```
   python launch_experiment.py
   ```

2. In the Setup tab:
   - Select the correct COM ports for the left and right boots
   - Choose the appropriate firmware version
   - Connect to the boots
   - Zero the boots (ensure participant is standing still)
   - Configure the torque profile parameters
   - Enter participant information

3. In the Experiment tab:
   - Click "Start Experiment" to begin
   - The participant walks with the exoboots
   - Record responses using the "Earlier," "Same," or "Later" buttons
   - Click "Stop Experiment" when finished

4. In the Results tab:
   - View participant responses
   - Save or export results as needed

5. In the Visualization tab:
   - Generate visualizations of the torque profile with different parameters

## Files

- `exoboot_1.py`: Main controller class for the Exoboot
- `exoboot_gui.py`: GUI and experiment control interface
- `launch_experiment.py`: Simple launcher for the experiment

## Data

Data is saved in the following folders:
- `data/`: Raw data logs from the boots
- `results/`: Participant response data
- `settings/`: Saved experiment settings

## Experiment Protocol

The experiment follows a staircase protocol:
1. Start with default rise or fall time parameters
2. Adjust the parameter after each participant response
3. Change direction when the participant's response reverses
4. Continue until completing the specified number of sweeps

## Customization

Parameters that can be customized:
- Rise Time: Time from actuation start to peak torque (% of stride)
- Fall Time: Time from peak torque to actuation end (% of stride)
- Actuation Start: When torque begins (% of stride)
- Actuation End: When torque ends (% of stride)
- Peak Torque: Maximum torque value (Nm/kg)

## Troubleshooting

If you encounter issues:
1. Ensure the boots are properly connected and powered
2. Check that the correct COM ports are selected
3. Verify that the firmware version is compatible
4. Make sure the participant is walking with a consistent gait

For more details, refer to the Dephy Exoboot documentation and FlexSEA API documentation.
