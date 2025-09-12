# Exoboot Perception Experiment

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive package for conducting human perception experiments using the Dephy Exoboot powered ankle exoskeleton, focusing on rise and fall time parameters in torque profiles.

## 🎯 Overview

This software enables researchers to investigate how humans perceive changes in the rise and fall time parameters of torque profiles delivered by a Dephy Exoboot powered ankle exoskeleton. The experiment protocol is based on research by Xiangyu Peng, adapted to focus on different temporal parameters of the assistance profile.

### Key Features

- **Real-time Control**: Direct control of Dephy Exoboot devices using the FlexSEA API
- **Gait Detection**: Automatic heel strike detection using IMU data for precise timing
- **Adaptive Protocols**: Staircase methodology for systematic parameter exploration
- **User-Friendly GUI**: Comprehensive interface for experiment control and data collection
- **Cross-Platform**: Compatible with Windows 11 and Linux (Raspberry Pi 5)
- **Data Management**: Automated logging, visualization, and export capabilities

## 🖥️ System Requirements

### Hardware
- Dephy Exoboot powered ankle exoskeleton(s)
- Windows 11 PC or Raspberry Pi 5 with Ubuntu 25
- USB connectivity for device communication

### Software
- **Python**: 3.11+ (tested on 3.11.3-3.11.9)
- **FlexSEA**: Dephy's actuator control library
- **GUI Framework**: Tkinter (included with Python)

## 🚀 Quick Start

### Option 1: Automated Installation (Recommended)

**Windows 11:**
```cmd
# Run as Administrator
git clone https://github.com/yourusername/exoboot-perception-experiment.git
cd exoboot-perception-experiment
scripts\install_windows.bat
```

**Linux/Raspberry Pi:**
```bash
git clone https://github.com/yourusername/exoboot-perception-experiment.git
cd exoboot-perception-experiment
chmod +x scripts/install_linux.sh
bash scripts/install_linux.sh
```

### Option 2: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/exoboot-perception-experiment.git
   cd exoboot-perception-experiment
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate.bat
   
   # Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install FlexSEA package:**
   ```bash
   pip install -e ./Actuator-Package-develop
   ```

4. **Install project dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

## 🎮 Usage

### Starting the Experiment

```bash
# Method 1: Direct module execution
python -m exoboot_perception.gui

# Method 2: Console script
exoboot-experiment

# Method 3: Legacy launcher (for backward compatibility)
python launch_experiment.py
```

### Experiment Workflow

1. **Setup Phase:**
   - Connect Exoboot devices via USB
   - Configure COM ports and firmware versions
   - Zero the devices (participant should stand still)
   - Set experiment parameters and participant information

2. **Experiment Phase:**
   - Start the experiment protocol
   - Participant walks with the exoboots
   - Record perceptual responses ("Earlier," "Same," "Later")
   - Software automatically adjusts parameters based on responses

3. **Data Collection:**
   - Real-time visualization of gait phases and torque profiles
   - Automatic logging of sensor data and responses
   - Export results in multiple formats (CSV, JSON)

## 📊 Experiment Protocol

The software implements a **staircase protocol** for psychophysical parameter estimation:

- **Initialization**: Start with default rise/fall time parameters
- **Adaptive Adjustment**: Modify parameters based on participant responses
- **Reversal Detection**: Change direction when perception threshold is crossed
- **Convergence**: Continue until specified number of reversals completed

### Configurable Parameters

| Parameter | Description | Units | Default Range |
|-----------|-------------|-------|---------------|
| Rise Time | Duration from actuation start to peak torque | % stride | 10-40% |
| Fall Time | Duration from peak torque to actuation end | % stride | 5-30% |
| Actuation Start | When torque assistance begins | % stride | 20-35% |
| Actuation End | When torque assistance ends | % stride | 55-70% |
| Peak Torque | Maximum assistance magnitude | Nm/kg | 0.1-0.4 |

## 📁 Project Structure

```
exoboot-perception-experiment/
├── src/exoboot_perception/          # Main package
│   ├── __init__.py                  # Package initialization
│   ├── constants.py                 # Configuration constants
│   ├── controller.py                # Exoboot control logic
│   └── gui.py                       # Graphical user interface
├── scripts/                         # Installation and utility scripts
├── tests/                           # Unit and integration tests
├── docs/                            # Documentation
├── data/                            # Experimental data (created at runtime)
├── results/                         # Analysis results (created at runtime)
├── settings/                        # Saved configurations (created at runtime)
├── Actuator-Package-develop/        # FlexSEA library
├── pyproject.toml                   # Project configuration
├── requirements.txt                 # Core dependencies
├── requirements-dev.txt             # Development dependencies
└── README.md                        # This file
```

## 🧪 Development

### Setting Up Development Environment

```bash
# Install with development dependencies
bash scripts/install_linux.sh dev      # Linux
scripts\install_windows.bat dev        # Windows

# Or manually:
pip install -r requirements-dev.txt
pre-commit install
```

### Code Quality Tools

- **Formatting**: Black, isort
- **Linting**: Flake8, mypy
- **Testing**: pytest with coverage
- **Pre-commit**: Automated code quality checks

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/exoboot_perception --cov-report=html

# Run specific test
pytest tests/test_controller.py
```

## 📈 Data Analysis

### Data Organization

- **Raw Sensor Data**: `data/` - Timestamped CSV files with IMU, encoder, and control data
- **Experiment Results**: `results/` - JSON/CSV files with participant responses and metadata
- **Configuration Files**: `settings/` - Saved experiment configurations

### Data Format Examples

**Sensor Data (CSV):**
```csv
timestamp,percent_gait,onset_timing,peak_timing,torque,current,gyroz
1694528400000,45.2,26.0,51.3,0.15,2400,-145.2
```

**Response Data (JSON):**
```json
{
  "trial": 1,
  "condition": "Rise Time",
  "parameter": "rise_time",
  "value": 25.3,
  "response": "Earlier",
  "timestamp": "2024-09-11 14:30:15",
  "participant_id": "P01"
}
```

## 🔧 Troubleshooting

### Common Issues

**Connection Problems:**
- Verify USB connections and device power
- Check COM port assignments in Device Manager (Windows) or `ls /dev/tty*` (Linux)
- Ensure FlexSEA firmware compatibility

**Permission Issues (Linux):**
- Add user to dialout group: `sudo usermod -a -G dialout $USER`
- Log out and back in for changes to take effect

**Performance Issues:**
- Reduce control frequency if experiencing lag
- Close unnecessary applications during experiments
- Ensure adequate system resources (RAM, CPU)

### Getting Help

1. Check the [documentation](docs/)
2. Review [common issues](https://github.com/yourusername/exoboot-perception-experiment/issues)
3. Open a [new issue](https://github.com/yourusername/exoboot-perception-experiment/issues/new)

## 📚 Scientific Background

This work builds upon research in human-robot interaction and motor learning:

- **Base Research**: Peng et al. - Perception of actuation timing in powered exoskeletons
- **Focus Area**: Rise and fall time parameter perception in torque profiles
- **Methodology**: Psychophysical staircase protocols for threshold estimation

### Key References

- Collins, S. H., et al. (2015). Reducing the energy cost of human walking using an unpowered ankle exoskeleton. *Nature*, 522(7555), 212-215.
- Peng, X., et al. (2023). Human perception of actuation timing in powered ankle exoskeletons. *Journal of Biomechanics*.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with appropriate tests
4. Run quality checks (`pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- **Xiangyu Peng**: Original research and methodology inspiration
- **Dephy Inc**: FlexSEA API and Exoboot hardware
- **Scientific Community**: Ongoing research in human-robot interaction

## 📞 Contact

**Max M** - your.email@example.com

**Project Link**: https://github.com/yourusername/exoboot-perception-experiment

---

*For detailed technical documentation, see the [docs/](docs/) directory.*
