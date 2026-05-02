"""
Generate demo IFC files for the Building Code Compliance demo.
Requires: ifcopenshell (available in the 'archi' conda env)
"""
import ifcopenshell
import uuid, os, math

OUT_DIR = "e:/check-my/archi/files/demo"
os.makedirs(OUT_DIR, exist_ok=True)


# ── helpers ────────────────────────────────────────────────────────────────────

def new_guid():
    return ifcopenshell.guid.new()


def make_model():
    """Create a minimal IFC4 model with project/site/building/storey."""
    m = ifcopenshell.file(schema="IFC4")

    # Units
    unit_assignment = m.createIfcUnitAssignment([
        m.createIfcSIUnit(None, "LENGTHUNIT", None, "METRE"),
        m.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE"),
        m.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE"),
    ])

    # Geometric representation context
    ctx = m.createIfcGeometricRepresentationContext(
        None, "Model", 3, 1.0e-5,
        m.createIfcAxis2Placement3D(
            m.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
        None)

    # Owner history
    person  = m.createIfcPerson(None, "Demo", "User", None, None, None, None, None)
    org     = m.createIfcOrganization(None, "Demo Org", None, None, None)
    p_and_o = m.createIfcPersonAndOrganization(person, org, None)
    app     = m.createIfcApplication(org, "1.0", "DemoGen", "DemoGen")
    owner   = m.createIfcOwnerHistory(p_and_o, app, None, "ADDED", None, p_and_o, app, 0)

    # Project hierarchy
    project  = m.createIfcProject(new_guid(), owner, "Demo Project", None,
                                   None, None, None, [ctx], unit_assignment)
    site     = m.createIfcSite(new_guid(), owner, "Demo Site", None, None,
                                None, None, None, "ELEMENT", None, None, None, None, None)
    building = m.createIfcBuilding(new_guid(), owner, "Demo Building", None, None,
                                    None, None, None, "ELEMENT", None, None, None)
    storey   = m.createIfcBuildingStorey(new_guid(), owner, "Ground Floor", None, None,
                                          None, None, None, "ELEMENT", 0.0)

    # Aggregate relations
    m.createIfcRelAggregates(new_guid(), owner, None, None, project,  [site])
    m.createIfcRelAggregates(new_guid(), owner, None, None, site,     [building])
    m.createIfcRelAggregates(new_guid(), owner, None, None, building, [storey])

    return m, owner, storey, ctx


def add_pset(m, owner, element, pset_name, props: dict):
    """Add a property set with IfcPropertySingleValue entries."""
    pset_props = []
    for name, value in props.items():
        if isinstance(value, float):
            val = m.createIfcReal(value)
        elif isinstance(value, int):
            val = m.createIfcInteger(value)
        elif isinstance(value, bool):
            val = m.createIfcBoolean(value)
        else:
            val = m.createIfcLabel(str(value))
        pset_props.append(m.createIfcPropertySingleValue(name, None, val, None))

    pset = m.createIfcPropertySet(new_guid(), owner, pset_name, None, pset_props)
    m.createIfcRelDefinesByProperties(new_guid(), owner, None, None, [element], pset)
    return pset


def add_qto(m, owner, element, qto_name, quantities: dict):
    """Add a quantity set with IfcQuantityArea / IfcQuantityLength."""
    qto_items = []
    for name, value in quantities.items():
        if "Area" in name or "area" in name:
            qto_items.append(m.createIfcQuantityArea(name, None, None, float(value), None))
        elif "Volume" in name or "volume" in name:
            qto_items.append(m.createIfcQuantityVolume(name, None, None, float(value), None))
        else:
            qto_items.append(m.createIfcQuantityLength(name, None, None, float(value), None))

    qto = m.createIfcElementQuantity(new_guid(), owner, qto_name, None, None, qto_items)
    m.createIfcRelDefinesByProperties(new_guid(), owner, None, None, [element], qto)
    return qto


def place(m, x=0.0, y=0.0, z=0.0):
    origin = m.createIfcCartesianPoint((x, y, z))
    axis   = m.createIfcDirection((0.0, 0.0, 1.0))
    ref    = m.createIfcDirection((1.0, 0.0, 0.0))
    return m.createIfcLocalPlacement(None, m.createIfcAxis2Placement3D(origin, axis, ref))


def contain(m, owner, storey, *elements):
    m.createIfcRelContainedInSpatialStructure(
        new_guid(), owner, None, None, list(elements), storey)


def add_door(m, owner, storey, name, width_m, height_m, x=0.0, y=0.0):
    """Add an IfcDoor with OverallWidth/OverallHeight (in metres for IFC4)."""
    door = m.createIfcDoor(
        new_guid(), owner, name, None, None,
        place(m, x, y, 0.0), None, None,
        height_m, width_m)
    contain(m, owner, storey, door)
    add_pset(m, owner, door, "Pset_DoorCommon", {
        "IsExternal": False,
        "FireRating": "none",
        "Reference": "D-{}".format(name),
    })
    return door


def add_window(m, owner, storey, name, width_m, height_m, x=0.0, y=0.0):
    win = m.createIfcWindow(
        new_guid(), owner, name, None, None,
        place(m, x, y, 1.0), None, None,
        height_m, width_m)
    contain(m, owner, storey, win)
    add_pset(m, owner, win, "Pset_WindowCommon", {
        "IsExternal": True,
        "Reference": "W-{}".format(name),
    })
    return win


def add_wall(m, owner, storey, name, thickness_m, length_m=3.0, height_m=3.0, x=0.0, y=0.0):
    wall = m.createIfcWall(new_guid(), owner, name, None, None,
                           place(m, x, y, 0.0), None, None)
    contain(m, owner, storey, wall)
    add_pset(m, owner, wall, "Pset_WallCommon", {
        "IsExternal": True,
        "Thickness": thickness_m,
        "Reference": "W-{}".format(name),
    })
    add_qto(m, owner, wall, "Qto_WallBaseQuantities", {
        "Length": length_m,
        "Height": height_m,
        "Width":  thickness_m,
        "GrossFootprintArea": round(length_m * thickness_m, 4),
    })
    return wall


def add_space(m, owner, storey, name, area_m2, height_m=2.6, x=0.0, y=0.0):
    space = m.createIfcSpace(new_guid(), owner, name, None, None,
                              place(m, x, y, 0.0), None, None, "ELEMENT", None)
    m.createIfcRelAggregates(new_guid(), owner, None, None, storey, [space])
    add_pset(m, owner, space, "Pset_SpaceCommon", {
        "IsExternal": False,
        "ReferenceID": name,
    })
    add_qto(m, owner, space, "Qto_SpaceBaseQuantities", {
        "NetFloorArea": area_m2,
        "GrossFloorArea": round(area_m2 * 1.05, 2),
        "NetVolume": round(area_m2 * height_m, 2),
    })
    return space


def add_slab(m, owner, storey, name, thickness_m, area_m2=25.0, x=0.0, y=0.0):
    slab = m.createIfcSlab(new_guid(), owner, name, None, None,
                            place(m, x, y, 0.0), None, None, "FLOOR")
    contain(m, owner, storey, slab)
    add_pset(m, owner, slab, "Pset_SlabCommon", {
        "IsExternal": False,
        "LoadBearing": True,
        "Reference": name,
    })
    add_qto(m, owner, slab, "Qto_SlabBaseQuantities", {
        "GrossArea": area_m2,
        "NetArea": area_m2,
        "Depth": thickness_m,
    })
    return slab


def add_stair(m, owner, storey, name, width_m, x=0.0, y=0.0):
    stair = m.createIfcStair(new_guid(), owner, name, None, None,
                              place(m, x, y, 0.0), None, None, "STRAIGHT_RUN_STAIR")
    contain(m, owner, storey, stair)
    flight = m.createIfcStairFlight(new_guid(), owner, name + "_Flight", None, None,
                                    place(m, x, y, 0.0), None, None,
                                    14, 13, None, None, "STRAIGHT")
    contain(m, owner, storey, flight)
    add_pset(m, owner, flight, "Pset_StairFlightCommon", {
        "Reference": name,
        "RiserHeight": 0.175,
        "TreadLength": 0.280,
    })
    add_qto(m, owner, flight, "Qto_StairFlightBaseQuantities", {
        "Length": width_m,   # Width stored as Length in QTO for stair flights
        "Width": width_m,
    })
    return stair, flight


def save(m, filename):
    path = f"{OUT_DIR}/{filename}"
    m.write(path)
    print(f"Saved: {path}")


# ── Building definitions ────────────────────────────────────────────────────────

def make_compliant():
    m, owner, storey, ctx = make_model()
    # Doors: 0.92m wide (≥ 0.90m ✓), 2.05m tall (≥ 2.00m ✓)
    for i in range(4):
        add_door(m, owner, storey, f"Door-{i+1:02d}", width_m=0.92, height_m=2.05, x=float(i*2))
    # Windows: 1.20m wide, 1.20m tall ✓
    for i in range(4):
        add_window(m, owner, storey, f"Win-{i+1:02d}", width_m=1.20, height_m=1.20, x=float(i*2))
    # Walls: 0.25m thick (≥ 0.24m ✓)
    for i in range(3):
        add_wall(m, owner, storey, f"Wall-Ext-{i+1:02d}", thickness_m=0.25, length_m=5.0, x=float(i*5))
    # Spaces: 14m² living ✓, 10m² bedroom ✓, 12m² bedroom ✓
    add_space(m, owner, storey, "Living Room",  area_m2=16.0, x=0.0)
    add_space(m, owner, storey, "Bedroom 1",    area_m2=12.0, x=5.0)
    add_space(m, owner, storey, "Bedroom 2",    area_m2=10.0, x=10.0)
    add_space(m, owner, storey, "Kitchen",      area_m2=8.0,  x=15.0)
    # Slabs: 0.20m thick (≥ 0.18m ✓)
    add_slab(m, owner, storey, "Floor-Slab-01", thickness_m=0.20, area_m2=60.0)
    # Stairs: 1.10m wide (≥ 1.00m ✓)
    add_stair(m, owner, storey, "Main-Stair", width_m=1.10)
    save(m, "demo_compliant_building.ifc")


def make_narrow_doors():
    m, owner, storey, ctx = make_model()
    # Doors: 0.75m wide (< 0.90m ✗), height fine
    for i in range(5):
        add_door(m, owner, storey, f"Door-Narrow-{i+1:02d}", width_m=0.75, height_m=2.05, x=float(i*2))
    # One compliant door for contrast
    add_door(m, owner, storey, "Door-OK-01", width_m=0.92, height_m=2.05, x=12.0)
    # Windows compliant
    for i in range(3):
        add_window(m, owner, storey, f"Win-{i+1:02d}", width_m=1.10, height_m=1.10, x=float(i*2))
    # Walls compliant
    add_wall(m, owner, storey, "Wall-Ext-01", thickness_m=0.25, length_m=6.0)
    add_space(m, owner, storey, "Living Room", area_m2=15.0)
    add_slab(m, owner, storey, "Floor-Slab", thickness_m=0.20)
    save(m, "demo_narrow_doors.ifc")


def make_thin_walls():
    m, owner, storey, ctx = make_model()
    # Walls: 0.12m thick (< 0.24m ✗)
    for i in range(4):
        add_wall(m, owner, storey, f"Wall-Thin-{i+1:02d}", thickness_m=0.12, length_m=4.0, x=float(i*5))
    # One compliant wall
    add_wall(m, owner, storey, "Wall-OK-01", thickness_m=0.25, length_m=4.0, x=20.0)
    # Doors compliant
    for i in range(3):
        add_door(m, owner, storey, f"Door-{i+1:02d}", width_m=0.92, height_m=2.05, x=float(i*2))
    # Windows compliant
    for i in range(2):
        add_window(m, owner, storey, f"Win-{i+1:02d}", width_m=1.10, height_m=1.00, x=float(i*3))
    add_space(m, owner, storey, "Living Room", area_m2=14.0)
    add_slab(m, owner, storey, "Floor-Slab", thickness_m=0.20)
    save(m, "demo_thin_walls.ifc")


def make_small_rooms():
    m, owner, storey, ctx = make_model()
    # Rooms: 6m² (< 10m² ✗)
    for i, rname in enumerate(["Living Room", "Bedroom 1", "Bedroom 2", "Study"]):
        add_space(m, owner, storey, rname, area_m2=6.0, x=float(i*3))
    # One compliant room
    add_space(m, owner, storey, "Master Bedroom", area_m2=12.0, x=15.0)
    # Rest compliant
    for i in range(3):
        add_door(m, owner, storey, f"Door-{i+1:02d}", width_m=0.92, height_m=2.05, x=float(i*2))
    add_wall(m, owner, storey, "Wall-Ext-01", thickness_m=0.25)
    add_slab(m, owner, storey, "Floor-Slab", thickness_m=0.20)
    save(m, "demo_small_rooms.ifc")


def make_mixed_issues():
    m, owner, storey, ctx = make_model()
    # Narrow doors ✗
    for i in range(3):
        add_door(m, owner, storey, f"Door-Narrow-{i+1:02d}", width_m=0.70, height_m=2.05, x=float(i*2))
    # Thin walls ✗
    for i in range(3):
        add_wall(m, owner, storey, f"Wall-Thin-{i+1:02d}", thickness_m=0.11, length_m=4.0, x=float(i*5))
    # Small rooms ✗
    add_space(m, owner, storey, "Room A", area_m2=5.0)
    add_space(m, owner, storey, "Room B", area_m2=7.0, x=3.0)
    # Thin slab ✗
    add_slab(m, owner, storey, "Floor-Slab-Thin", thickness_m=0.12)
    # One compliant element of each
    add_door(m, owner, storey, "Door-OK", width_m=0.95, height_m=2.10, x=10.0)
    add_wall(m, owner, storey, "Wall-OK", thickness_m=0.25, x=25.0)
    add_space(m, owner, storey, "Good Room", area_m2=14.0, x=10.0)
    # Windows fine
    for i in range(2):
        add_window(m, owner, storey, f"Win-{i+1:02d}", width_m=1.20, height_m=1.10, x=float(i*2))
    save(m, "demo_mixed_issues.ifc")


if __name__ == "__main__":
    print("Generating IFC demo files...")
    make_compliant()
    make_narrow_doors()
    make_thin_walls()
    make_small_rooms()
    make_mixed_issues()
    print("Done! All IFC files saved to:", OUT_DIR)
