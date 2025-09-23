# ExoBoot Data Analysis - Key Findings and Fixes

## Problem Identified
The MATLAB-based data conversions were causing incorrect visualization of ExoBoot sensor data. The original code was applying conversions that were specific to Peng's MATLAB analysis but didn't match the actual raw sensor output.

## Root Cause
- **MATLAB Conversions**: The original code used `MAPPING_FACTOR = 3640` and applied conversions like:
  - Ankle angle: `(ank_ang - 3640) / 100`  
  - Torque: `ank_torque / 1000`
- **Result**: These conversions produced flat, unrealistic data that didn't show actual ankle movement

## Solution Applied
**Use RAW sensor data directly** - no conversions needed:
- **Ankle angle**: Use `df['ank_ang']` directly (encoder units)
- **Torque**: Use `df['ank_torque']` directly (mNm)
- **No filtering**: Plot all data points like LibreOffice does

## Files Fixed

### 1. ankle_angle_plotter.py ✅
- **Before**: Flat line at ~12.5 degrees due to MATLAB conversions
- **After**: Clear ankle flexion cycles from ~1700 to ~8000 encoder units
- **Changes**: Removed all MATLAB conversions, used raw `ank_ang` data

### 2. torque_angle_analyzer.py ✅
- **Before**: Used converted torque (Nm) and angle (degrees) with MATLAB factors
- **After**: Uses raw torque (mNm) vs raw ankle angle (encoder units)
- **Changes**: 
  - Removed `MAPPING_FACTOR` and related conversions
  - Updated labels to show raw units
  - Removed excessive filtering

### 3. exoboot_1.py ✅
- **Fixed**: Dictionary access issue in `read_data()` method
- **Before**: `data.accelx` (treating dict as object)
- **After**: `data['accelx']` (proper dictionary access)

## Key Lessons

1. **Raw data is often better**: The sensor outputs are already in meaningful units
2. **MATLAB conversions don't always translate**: Different analysis tools may need different approaches
3. **Match reference plots**: When you have a working visualization (LibreOffice), match its approach exactly
4. **Minimal filtering**: Often, plotting all data points gives the clearest picture

## Verification Methods

- **Visual comparison**: Compare Python plots with LibreOffice/Excel plots of same data
- **Data range checking**: Ensure output ranges match expected sensor values
- **Pattern recognition**: Look for expected patterns (ankle flexion cycles, torque profiles)

## Future Data Analysis

When creating new analysis scripts:
1. **Start with raw data** - apply conversions only if absolutely necessary
2. **Test against known good visualizations** (Excel, LibreOffice)
3. **Use minimal filtering** initially
4. **Check data ranges** make sense for the sensor type

## Applied To

- ✅ `ankle_angle_plotter.py` - Now shows correct ankle movement
- ✅ `torque_angle_analyzer.py` - Now uses raw data for torque vs angle plots  
- ✅ `exoboot_1.py` - Fixed dictionary access in data reading
- ✅ Other Python files checked - no additional issues found

The raw sensor data approach should now provide accurate, meaningful visualizations that match the actual ExoBoot sensor outputs.