# Geometric Properties Extraction Upgrade

## What Changed

The `get_geometric_properties` function has been upgraded to be much more robust, especially for Revit exports that may have inconsistent property naming.

## New 3-Tier Search Strategy

The function now searches for dimensions in **3 different places** (in order of priority):

### 1. **Geometry (Direct Attributes)**
- Checks direct IFC attributes like `OverallWidth`, `OverallHeight`
- Fastest and most reliable when available
- Example: `product.OverallWidth`

### 2. **Property Sets (Psets)**
- Searches through all property sets using `get_psets()`
- Handles various property set naming conventions
- Example: `Pset_DoorCommon`, `Pset_Revit_Dimensions`, etc.

### 3. **Quantities (Qto)**
- Searches through quantity sets using `get_qto()`
- Often contains calculated geometric quantities
- Example: `Qto_DoorBaseQuantities`, `Qto_WallBaseQuantities`, etc.

## Benefits

✅ **More Robust**: Works even if Revit export is inconsistent  
✅ **Better Coverage**: Finds dimensions even when they're in unexpected places  
✅ **Multiple Property Names**: Tries various property name variations  
✅ **Fallback Strategy**: If one source fails, tries the next

## How It Works

### The `find_property_value()` Helper Function

```python
def find_property_value(product, prop_names, multiplier=1.0, unit_suffix=""):
    # 1. Try Geometry (direct attributes)
    # 2. Try Property Sets (Psets)
    # 3. Try Quantities (Qto)
    # Returns first found value, or None
```

**Parameters:**
- `product`: The IFC element
- `prop_names`: List of property names to try (e.g., `['OverallWidth', 'Width', 'NominalWidth']`)
- `multiplier`: Conversion factor (e.g., `1000.0` to convert meters to mm)
- `unit_suffix`: Not used currently, reserved for future use

**Returns:** First found value (as float) or `None`

## Enhanced Element Support

### Doors & Windows
- Searches: `OverallWidth`, `Width`, `NominalWidth`
- Searches: `OverallHeight`, `Height`, `NominalHeight`

### Spaces/Rooms
- **Area**: `GrossFloorArea`, `NetFloorArea`, `Area`, `FloorArea`, `GrossArea`, `NetArea`, `BaseArea`
- **Volume**: `GrossVolume`, `NetVolume`, `Volume`, `EnclosedVolume`

### Walls
- **Thickness**: `Thickness`, `WallThickness`, `NominalThickness`, `Width`
- **Length**: `Length`, `WallLength`, `NominalLength`
- **Height**: `Height`, `WallHeight`, `NominalHeight`

### Slabs
- **Thickness**: `Thickness`, `SlabThickness`, `NominalThickness`, `Depth`
- **Area**: `Area`, `SlabArea`, `GrossArea`, `NetArea`, `BaseArea`
- **Length/Width**: `Length`, `Width`, `SlabLength`, `SlabWidth`, `NominalLength`, `NominalWidth`

### Beams
- **Length**: `Length`, `BeamLength`, `NominalLength`
- **Width**: `Width`, `BeamWidth`, `NominalWidth`, `FlangeWidth`
- **Height**: `Height`, `BeamHeight`, `NominalHeight`, `Depth`, `FlangeThickness`

### Columns
- **Width**: `Width`, `ColumnWidth`, `NominalWidth`, `Diameter`, `CrossSectionWidth`
- **Height**: `Height`, `ColumnHeight`, `NominalHeight`, `Length`
- **Depth**: `Depth`, `ColumnDepth`, `NominalDepth`, `CrossSectionDepth`
- **Area**: `CrossSectionArea`, `Area`, `BaseArea`

### Stairs
- **Width**: `Width`, `StairWidth`, `NominalWidth`
- **Height**: `Height`, `RiseHeight`, `TotalRiseHeight`
- **Length**: `Length`, `StairLength`, `NominalLength`, `RunLength`

### Roofs
- **Area**: `Area`, `RoofArea`, `GrossArea`, `NetArea`

## Example: Door Width Extraction

**Before (only checked geometry):**
```python
if hasattr(product, 'OverallWidth') and product.OverallWidth:
    geom['Width (mm)'] = f"{product.OverallWidth * 1000:.0f}"
```

**After (checks 3 places):**
```python
width = find_property_value(product, 
    ['OverallWidth', 'Width', 'NominalWidth'], 
    1000.0)
if width:
    geom['Width (mm)'] = f"{width:.0f}"
```

This will find the width even if:
- It's not in `OverallWidth` attribute
- It's in a property set like `Pset_DoorCommon.Width`
- It's in a quantity set like `Qto_DoorBaseQuantities.Width`
- It's named `NominalWidth` instead of `Width`

## Testing with Revit Exports

This upgrade is particularly useful for Revit exports because:
- Revit sometimes stores dimensions in property sets instead of attributes
- Property set names can vary (`Pset_Revit_Dimensions` vs `Pset_DoorCommon`)
- Some properties are only in quantity sets
- Property names may use different conventions

## Performance

The function is still efficient because:
- It stops searching once a value is found
- Geometry check is fastest (direct attribute access)
- Property sets are cached by ifcopenshell
- Only searches when needed (lazy evaluation)



