# Contributing to Exoboot Perception Experiment

Thank you for your interest in contributing to the Exoboot Perception Experiment project! This document provides guidelines and information for contributors.

## 🎯 How to Contribute

### Reporting Issues

Before creating a new issue:
- Search existing issues to avoid duplicates
- Use the issue template if available
- Provide detailed information including:
  - Operating system and version
  - Python version
  - Steps to reproduce the issue
  - Expected vs actual behavior
  - Error messages and stack traces

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
- Create an issue with the "enhancement" label
- Provide a clear description of the proposed feature
- Explain the use case and benefits
- Consider implementation complexity and maintenance burden

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Access to Dephy Exoboot hardware (for hardware-related development)

### Setting Up Your Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/yourusername/exoboot-perception-experiment.git
   cd exoboot-perception-experiment
   ```

2. **Create a development environment:**
   ```bash
   # Linux/Mac
   bash scripts/install_linux.sh dev
   
   # Windows
   scripts\install_windows.bat dev
   ```

3. **Verify the setup:**
   ```bash
   # Activate environment
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate.bat  # Windows
   
   # Run tests
   pytest
   
   # Check code quality
   pre-commit run --all-files
   ```

## 📝 Development Guidelines

### Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **flake8**: Linting and style checks
- **mypy**: Type checking
- **pytest**: Testing framework

### Coding Standards

1. **Follow PEP 8**: Use Black for consistent formatting
2. **Type Hints**: Add type annotations for function signatures
3. **Docstrings**: Use Google-style docstrings for all public functions/classes
4. **Comments**: Write clear, concise comments for complex logic
5. **Variable Names**: Use descriptive names, avoid abbreviations

### Example Code Style

```python
from typing import Optional, List, Dict, Any

def calculate_torque_profile(
    percent_gait: float,
    rise_time: float,
    fall_time: float,
    peak_torque: float = 0.225
) -> float:
    """
    Calculate torque value at specific gait phase percentage.
    
    Args:
        percent_gait: Current gait cycle percentage (0-100)
        rise_time: Duration of torque increase phase (% stride)
        fall_time: Duration of torque decrease phase (% stride)
        peak_torque: Maximum torque value (Nm/kg)
        
    Returns:
        Calculated torque value in Nm/kg
        
    Raises:
        ValueError: If percent_gait is outside valid range
    """
    if not 0 <= percent_gait <= 100:
        raise ValueError(f"Invalid gait percentage: {percent_gait}")
    
    # Implementation here...
    return calculated_torque
```

## 🧪 Testing

### Test Structure

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **Hardware Tests**: Test with actual Exoboot devices (when available)

### Writing Tests

1. **Test File Naming**: `test_<module_name>.py`
2. **Test Function Naming**: `test_<function_name>_<scenario>`
3. **Use Fixtures**: For setup/teardown of test data
4. **Mock Hardware**: Use mocks for hardware-dependent tests

### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from exoboot_perception.controller import ExoBootController

class TestExoBootController:
    """Test suite for ExoBootController class."""
    
    def test_init_default_parameters(self):
        """Test controller initialization with default parameters."""
        controller = ExoBootController(side=1, port="COM3", firmware_version="1.0.0")
        
        assert controller.side == 1
        assert controller.port == "COM3"
        assert controller.user_weight == 70  # default value
    
    @patch('exoboot_perception.controller.Device')
    def test_connect_success(self, mock_device):
        """Test successful device connection."""
        # Setup
        mock_device_instance = Mock()
        mock_device.return_value = mock_device_instance
        
        controller = ExoBootController(side=1, port="COM3", firmware_version="1.0.0")
        
        # Test
        result = controller.connect()
        
        # Verify
        assert result is True
        assert controller.connected is True
        mock_device_instance.open.assert_called_once()
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_controller.py

# Run with coverage
pytest --cov=src/exoboot_perception --cov-report=html

# Run only unit tests
pytest -m "not integration"

# Run with verbose output
pytest -v
```

## 🔄 Workflow

### Branch Strategy

- **main**: Stable, production-ready code
- **develop**: Integration branch for features
- **feature/**: Individual feature branches
- **hotfix/**: Critical bug fixes
- **release/**: Release preparation

### Pull Request Process

1. **Create Feature Branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes:**
   - Write code following style guidelines
   - Add/update tests as needed
   - Update documentation if necessary

3. **Quality Checks:**
   ```bash
   # Run tests
   pytest
   
   # Check code formatting
   black --check src/ tests/
   isort --check-only src/ tests/
   
   # Run linting
   flake8 src/ tests/
   
   # Type checking
   mypy src/
   
   # Or run all checks
   pre-commit run --all-files
   ```

4. **Commit Changes:**
   ```bash
   git add .
   git commit -m "feat: add new torque profile calculation method"
   ```

5. **Push and Create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

### Commit Message Format

Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation updates
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for bilateral exoboot control
fix: resolve heel strike detection timing issue
docs: update installation instructions for Raspberry Pi
test: add unit tests for torque profile calculation
```

## 📋 Review Criteria

Pull requests will be reviewed based on:

### Functionality
- ✅ Code works as intended
- ✅ Edge cases are handled
- ✅ No breaking changes to public APIs

### Code Quality
- ✅ Follows established coding standards
- ✅ Appropriate error handling
- ✅ Clear and maintainable code structure

### Testing
- ✅ Adequate test coverage (aim for >80%)
- ✅ Tests pass in CI environment
- ✅ New features include appropriate tests

### Documentation
- ✅ Code is well-documented
- ✅ README updated if needed
- ✅ API documentation reflects changes

### Performance
- ✅ No significant performance regressions
- ✅ Efficient use of resources
- ✅ Considers real-time requirements

## 🐛 Debugging

### Hardware Issues
- Use simulation mode for development without hardware
- Check device connections and permissions
- Verify FlexSEA library compatibility

### Software Issues
- Enable debug logging in configuration
- Use Python debugger (pdb) for step-through debugging
- Check system resource usage during experiments

### Common Problems

1. **Import Errors**: Verify virtual environment activation
2. **Permission Denied**: Check user permissions for device access
3. **GUI Issues**: Ensure Tkinter is properly installed
4. **Real-time Performance**: Monitor system load during experiments

## 🎓 Learning Resources

### Project-Specific
- [Dephy FlexSEA Documentation](https://dephy.com/flexsea-documentation/)
- [Exoboot User Guides](User_Guides/)
- Research papers in `docs/references/`

### General Python Development
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [pytest Documentation](https://docs.pytest.org/)

### Biomechanics and HCI
- Human-Robot Interaction principles
- Gait analysis fundamentals
- Psychophysical experimental methods

## 📞 Getting Help

1. **Check Documentation**: Start with project docs and README
2. **Search Issues**: Look for similar problems in GitHub issues
3. **Ask Questions**: Create a GitHub issue with the "question" label
4. **Contact Maintainers**: Reach out directly for complex issues

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Project acknowledgments

Thank you for contributing to advancing human-robot interaction research! 🤖🚶‍♂️