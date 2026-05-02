# Geometric Information Extraction

## Overview

The enhanced IFC viewer now extracts geometric information from IFC files, including dimensions, areas, and volumes for different element types.

## Extracted Geometric Properties

### 🚪 **Doors (IfcDoor)**
- **Width (mm)**: Overall width of the door opening
- **Height (mm)**: Overall height of the door opening
- Extracted from: `OverallWidth` and `OverallHeight` attributes

### 🪟 **Windows (IfcWindow)**
- **Width (mm)**: Overall width of the window
- **Height (mm)**: Overall height of the window
- Extracted from: `OverallWidth` and `OverallHeight` attributes

### 🏠 **Spaces/Rooms (IfcSpace)**
- **Area (m²)**: Gross floor area of the space
- **Volume (m³)**: Gross volume of the space
- Extracted from: Property Sets (`Pset_SpaceCommon`, `Qto_SpaceBaseQuantities`, etc.)
- Common property names: `GrossFloorArea`, `Area`, `GrossVolume`, `Volume`

### 🧱 **Walls (IfcWall)**
- **Thickness (mm)**: Wall thickness
- **Length (m)**: Wall length
- Extracted from: Property Sets (`Pset_WallCommon`, `Qto_WallBaseQuantities`, etc.)

### 🏗️ **Slabs (IfcSlab)**
- **Thickness (mm)**: Slab thickness
- **Area (m²)**: Slab area
- Extracted from: Property Sets (`Pset_SlabCommon`, `Qto_SlabBaseQuantities`, etc.)

### 📏 **Beams (IfcBeam)**
- **Length (m)**: Beam length
- **Width (mm)**: Beam width
- **Height (mm)**: Beam height
- Extracted from: Property Sets (`Pset_BeamCommon`, `Qto_BeamBaseQuantities`, etc.)

### 🏛️ **Columns (IfcColumn)**
- **Width (mm)**: Column width/diameter
- **Height (mm)**: Column height
- Extracted from: Property Sets (`Pset_ColumnCommon`, `Qto_ColumnBaseQuantities`, etc.)

## How It Works

### 1. **Direct Attributes** (Doors & Windows)
```python
if "IfcDoor" in element_type:
    if hasattr(product, 'OverallWidth') and product.OverallWidth:
        geom['Width (mm)'] = f"{product.OverallWidth * 1000:.0f}"
```
- IFC stores door/window dimensions as direct attributes
- Values are in meters, converted to millimeters for display

### 2. **Property Sets** (Spaces, Walls, Slabs, etc.)
```python
psets = ifcopenshell.util.element.get_psets(product)
for pset_name, pset_props in psets.items():
    if 'GrossFloorArea' in pset_props:
        area = pset_props.get('GrossFloorArea')
        geom['Area (m²)'] = f"{float(area):.2f}"
```
- Uses `ifcopenshell.util.element.get_psets()` to extract property sets
- Searches common property set names for geometric data
- Handles different property naming conventions

## Property Set Naming Variations

IFC files may use different property set names. The code searches for common variations:

### Space Properties:
- `Pset_SpaceCommon`
- `Qto_SpaceBaseQuantities`
- `Pset_Revit_Dimensions`
- Property names: `GrossFloorArea`, `Area`, `GrossVolume`, `Volume`

### Wall Properties:
- `Pset_WallCommon`
- `Qto_WallBaseQuantities`
- Property names: `Thickness`, `Length`, `Width`, `Height`

### Slab Properties:
- `Pset_SlabCommon`
- `Qto_SlabBaseQuantities`
- Property names: `Thickness`, `Area`, `Length`, `Width`

## Display Features

### 1. **Element Tables**
Geometric properties are added as columns to the element tables:
```
Type | Name | GlobalId | Tag | Level | Width (mm) | Height (mm)
```

### 2. **Geometric Summary Section**
Shows aggregated statistics:
- **Doors**: Count, average width, width range
- **Spaces**: Count, total area, average area

### 3. **Column Ordering**
Geometric columns are displayed after basic information columns for better readability.

## Limitations

1. **Property Set Variations**: Different BIM software may use different property set names
2. **Missing Data**: Not all IFC files contain complete geometric information
3. **Geometry Calculation**: Some properties require complex geometry calculations (not implemented)
4. **Units**: Assumes standard IFC units (meters for lengths, square meters for areas)

## Future Enhancements

Possible improvements:
- Calculate dimensions from geometry representation
- Extract more properties (e.g., wall height, slab perimeter)
- Support for custom property sets
- Export geometric data to CSV/Excel
- Visual charts for geometric data distribution

## Example Output

### Door with Geometric Info:
```
Type: IfcDoor
Name: Main Entrance Door
Width (mm): 900
Height (mm): 2100
```

### Space with Geometric Info:
```
Type: IfcSpace
Name: Office 101
Area (m²): 25.50
Volume (m³): 76.50
```

### Wall with Geometric Info:
```
Type: IfcWall
Name: Exterior Wall 01
Thickness (mm): 200
Length (m): 10.50
```



