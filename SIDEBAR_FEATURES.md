# Sidebar NBauO Rule Configuration

## Overview

The IFC Element Viewer now includes a **sidebar with NBauO (Niedersächsische Bauordnung) rule configuration** that allows you to set building code compliance requirements and automatically check elements against these rules.

## Sidebar Location

The sidebar appears on the left side of the application and contains all rule configuration options.

## Features

### 1. **Enable/Disable Compliance Checking**
- Checkbox to turn compliance checking on/off
- When disabled, the app works as a simple element viewer
- When enabled, elements are checked against configured rules

### 2. **Door Requirements**

#### Minimum Door Width
- **Default**: 900 mm (NBauO requirement for barrier-free access)
- **Range**: 0 - 5000 mm
- **Step**: 50 mm
- **Help Text**: "NBauO requires minimum 90 cm (900 mm) for barrier-free access"

#### Minimum Door Height
- **Default**: 2000 mm (standard minimum)
- **Range**: 0 - 5000 mm
- **Step**: 50 mm

### 3. **Window Requirements**

#### Minimum Window Width
- **Default**: 0 (disabled)
- **Range**: 0 - 5000 mm
- **Step**: 50 mm
- **Note**: Set to 0 to disable window width checking

#### Minimum Window Height
- **Default**: 0 (disabled)
- **Range**: 0 - 5000 mm
- **Step**: 50 mm
- **Note**: Set to 0 to disable window height checking

### 4. **Space/Room Requirements**

#### Minimum Room Area
- **Default**: 0.0 (disabled)
- **Range**: 0.0 - 1000.0 m²
- **Step**: 0.5 m²
- **Note**: Set to 0 to disable room area checking

#### Minimum Room Height
- **Default**: 0.0 (disabled)
- **Range**: 0.0 - 10.0 m
- **Step**: 0.1 m
- **Note**: Set to 0 to disable room height checking

### 5. **Wall Requirements**

#### Minimum Wall Thickness
- **Default**: 0 (disabled)
- **Range**: 0 - 1000 mm
- **Step**: 10 mm
- **Note**: Set to 0 to disable wall thickness checking

## How Compliance Checking Works

### 1. **Rule Configuration**
- Rules are configured in the sidebar before or after uploading the IFC file
- Rules are stored in session state and applied to all elements

### 2. **Element Checking**
For each element, the compliance checker:
- Extracts geometric properties (width, height, area, thickness, etc.)
- Compares against configured minimum values
- Flags violations if values are below minimums

### 3. **Violation Detection**
Elements are marked with:
- **✅ Pass**: Element meets all requirements
- **❌ VIOLATION**: Element fails one or more requirements
- **N/A**: Compliance checking is disabled or element type not checked

### 4. **Violation Details**
Each violation includes:
- Which rule was violated
- Actual value vs. required minimum
- Clear description of the issue

## Display Features

### Violation Summary
- **Alert Banner**: Shows total number of violations at the top
- **Violations Table**: Lists all violating elements with details
- **Violations by Type**: Breakdown showing which element types have violations

### Element Tables
- **Compliance Status Column**: Shows ✅ Pass or ❌ VIOLATION for each element
- **Violations Column**: Lists specific violation reasons
- **Highlighted Violations**: Violations are shown first in each element type section

### Example Violation Messages
- `"Door width 800 mm < minimum 900 mm"`
- `"Door height 1950 mm < minimum 2000 mm"`
- `"Room area 20.50 m² < minimum 25.00 m²"`
- `"Wall thickness 150 mm < minimum 200 mm"`

## Use Cases

### 1. **Barrier-Free Access Compliance**
Set minimum door width to 900 mm to check if all doors meet accessibility requirements.

### 2. **Building Code Compliance**
Configure multiple rules to check if the entire building model complies with NBauO requirements.

### 3. **Quality Control**
Use compliance checking to identify elements that don't meet design specifications.

### 4. **Custom Requirements**
Set custom minimum values for specific project requirements beyond standard building codes.

## Example Workflow

1. **Open the app** and configure rules in the sidebar
2. **Upload IFC file**
3. **Review violations** in the summary section at the top
4. **Examine details** in the element tables
5. **Adjust rules** in the sidebar if needed
6. **Re-upload** or refresh to see updated compliance status

## Technical Details

### Rule Storage
- Rules are stored in a dictionary: `compliance_rules`
- Keys: `min_door_width`, `min_door_height`, `min_window_width`, etc.
- Values are numeric (mm for dimensions, m² for areas, m for heights)

### Compliance Function
The `check_compliance()` function:
- Takes element type, geometric properties, and rules
- Returns status string and list of violations
- Handles missing geometric data gracefully

### Value Extraction
The `extract_numeric_value()` function:
- Parses formatted strings like "900.0" or "25.50 m²"
- Uses regex to extract numeric values
- Handles various formatting styles

## Future Enhancements

Possible additions:
- More rule types (maximum values, ratios, etc.)
- Rule presets (NBauO standard, DIN, etc.)
- Export violation reports
- Visual highlighting in 3D viewer
- Rule templates for different building types
- Custom rule definitions



