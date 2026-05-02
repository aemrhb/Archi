"""
Generate a ~50-page German NBauO-style PDF rulebook for demo purposes.
Requires: pip install fpdf2

Note: fpdf2 core fonts only support Latin-1. All German special characters
are replaced with ASCII equivalents (ae/oe/ue/ss) throughout.
"""
from fpdf import FPDF
import os

OUT_DIR = "e:/check-my/archi/files/demo"
os.makedirs(OUT_DIR, exist_ok=True)

# ---- Content ----------------------------------------------------------------

# Helper to make text safe for fpdf2 core fonts
def s(text):
    return (text
            .replace('\u00e4', 'ae').replace('\u00f6', 'oe').replace('\u00fc', 'ue')
            .replace('\u00c4', 'Ae').replace('\u00d6', 'Oe').replace('\u00dc', 'Ue')
            .replace('\u00df', 'ss')
            .replace('\u2013', '-').replace('\u2014', '-')
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'")
            .replace('\u00b2', '2').replace('\u00b3', '3')
            .replace('\u00e9', 'e').replace('\u00e8', 'e')
            .replace('\u2265', '>=').replace('\u2264', '<=')
            )

SECTIONS = [
    ("§ 1 Allgemeines – General Provisions",
     [("Scope and Purpose",
       "This building code (Niedersächsische Bauordnung – NBauO) governs the construction, "
       "alteration, use, maintenance, and demolition of buildings and structures in the state "
       "of Lower Saxony. Its purpose is to protect public safety, health, and welfare. "
       "All construction activities must comply with the applicable DIN standards and technical "
       "guidelines referenced herein. Non-compliance may result in construction stop orders, "
       "fines or mandatory demolition."),
      ("Definitions",
       "Building: Any structure connected to the ground that is suitable for human use or "
       "protection of property. Storey: A horizontal section of a building between two "
       "consecutive floor levels. Fire compartment: A section of a building separated from "
       "adjacent sections by fire-resistant construction with a fire resistance of at least "
       "F90-AB (REI 90). Barrier-free: Accessible to persons with disabilities without "
       "assistance."),
      ("Applicability",
       "This code applies to all new construction, extensions, and material alterations of "
       "existing buildings. Historic buildings may be subject to exemptions under §48. "
       "Temporary structures of less than 60 m² and standing for under 3 months are exempt "
       "from most provisions, but must still comply with structural safety requirements.")]
    ),
    ("§ 2–3 Bebauungsplan – Site and Planning",
     [("Site Coverage (GRZ)",
       "The site coverage ratio (Grundflächenzahl, GRZ) defines the maximum proportion of the "
       "plot that may be covered by buildings and structures. Unless the development plan (B-Plan) "
       "specifies otherwise, the GRZ shall not exceed 0.4 for residential areas and 0.8 for "
       "commercial areas."),
      ("Floor Area Ratio (GFZ)",
       "The floor area ratio (Geschossflächenzahl, GFZ) limits the total floor area relative to "
       "the plot area. Default maximum is 1.2 for residential zones and 2.4 for mixed-use zones, "
       "unless otherwise specified by the B-Plan."),
      ("Site Access",
       "Every building must be accessible from a public road. The minimum access width is 3.0 m "
       "for pedestrian access and 3.5 m for vehicle access. Emergency services access must be "
       "maintained at all times with a clearance width of at least 3.5 m and clearance height "
       "of 3.5 m.")]
    ),
    ("§ 4–8 Türen – Door Requirements",
     [("Minimum Door Width",
       "Doors in residential buildings must have a minimum clear width of 900 mm to ensure "
       "barrier-free access as required by DIN 18040-2. Doors to utility rooms and storage "
       "areas may have a minimum width of 750 mm. Fire doors (Feuerschutztüren) must have a "
       "minimum clear width of 1050 mm in escape routes."),
      ("Minimum Door Height",
       "The minimum clear height of door openings is 2000 mm (2.00 m). In basements and loft "
       "conversions the minimum height may be reduced to 1800 mm where the storey height is "
       "insufficient. Fire doors must provide a full clear height of 2100 mm."),
      ("Escape Route Doors",
       "Doors on escape routes must open in the direction of egress. They must not reduce the "
       "required escape route width of 1200 mm when open. Revolving doors and sliding doors are "
       "not permitted on primary escape routes unless supplemented by a conventional hinged door."),
      ("Door Swing Clearance",
       "A maneuvering clearance of at least 1500 mm × 1500 mm must be provided on the latch "
       "side of every barrier-free door, measured from the door frame in the direction of "
       "approach. This is required by DIN 18040-1."),
      ("Fire Door Rating",
       "Fire doors on escape routes must achieve a minimum rating of T30 (EI30-C). Doors "
       "between garages and living spaces must achieve T90 (EI90-C). All fire doors must "
       "be self-closing and must not be held open by wedges or other devices.")]
    ),
    ("§ 9–13 Fenster – Window Requirements",
     [("Minimum Window Area",
       "Habitable rooms must have natural light. The glazed area of windows must be at least "
       "1/8 of the room floor area. Bathrooms and WCs may use artificial lighting if mechanical "
       "ventilation is provided."),
      ("Minimum Window Height",
       "The clear height of opening windows used for ventilation must be at least 800 mm. "
       "The total window height including fixed glazing should be at least 900 mm for rooms "
       "above ground level."),
      ("Window Sill Height",
       "In rooms accessible to children, the window sill height must be at least 800 mm above "
       "finished floor level. Where sill height is below 800 mm, a protective barrier of at "
       "least 900 mm in height is required per DIN EN 13126."),
      ("Thermal Performance",
       "All windows in new construction must comply with the current Gebäudeenergiegesetz (GEG). "
       "The maximum U-value for windows (Uw) is 1.3 W/(m²K) for non-solar-passive buildings "
       "and 1.1 W/(m²K) for highly insulated buildings."),
      ("Ventilation",
       "Natural ventilation must provide a minimum air change rate of 0.5 per hour for habitable "
       "rooms. Window openings should be positioned to allow cross-ventilation where possible. "
       "Roof lights and skylights may supplement but not replace lateral windows for compliance.")]
    ),
    ("§ 14–18 Wände – Wall Requirements",
     [("External Wall Thickness",
       "External walls of masonry construction must have a minimum nominal thickness of 240 mm "
       "to provide adequate thermal and mechanical performance. Cavity walls must have an inner "
       "leaf of at least 115 mm and an outer leaf of at least 90 mm, giving a total construction "
       "depth of at least 300 mm including insulation."),
      ("Fire Walls",
       "Fire walls (Brandwände) separating buildings or fire compartments must achieve F90-AB "
       "(REI 90) and must have a minimum thickness of 240 mm for masonry or 200 mm for reinforced "
       "concrete. They must project at least 300 mm beyond the roof surface."),
      ("Interior Partition Walls",
       "Non-load-bearing partition walls must have a minimum thickness of 100 mm (finished). "
       "Load-bearing interior walls must be designed in accordance with DIN EN 1996 (Eurocode 6) "
       "and are typically a minimum of 175 mm in masonry. Walls adjacent to escape routes must "
       "achieve at least EI30 fire resistance."),
      ("Sound Insulation",
       "Party walls between dwellings must achieve a minimum weighted sound reduction index of "
       "R'w ≥ 53 dB per DIN 4109-1. Walls adjacent to plant rooms, commercial kitchens or "
       "garages must achieve R'w ≥ 57 dB."),
      ("Structural Requirements",
       "All load-bearing walls must comply with DIN EN 1996 (masonry) or DIN EN 1992 "
       "(reinforced concrete). Minimum slenderness ratios must be observed. Wall openings and "
       "lintels must be designed for the full applied loads including live loads and wind loads.")]
    ),
    ("§ 19–23 Treppen – Staircase Requirements",
     [("Minimum Stair Width",
       "The minimum clear width of staircases in residential buildings is 1000 mm. Escape "
       "staircases serving more than 200 persons must be at least 1200 mm wide. In single-family "
       "homes, a minimum width of 800 mm is permissible for secondary staircases to loft spaces."),
      ("Rise and Going",
       "The maximum riser height (Steigung) is 190 mm. The minimum going (Auftritt) is 260 mm. "
       "The relationship must satisfy the formula: 2 × Rise + Going = 590 to 650 mm. "
       "All steps within a stair flight must have equal rise and going."),
      ("Handrails",
       "All staircases with more than 3 steps must be provided with handrails on at least one "
       "side. Staircases wider than 1500 mm must have handrails on both sides. Handrail height "
       "must be between 850 mm and 1100 mm above the pitch line per DIN 18065."),
      ("Headroom",
       "Minimum clear headroom above any step must be 2000 mm at all points. Headroom is "
       "measured vertically from the nosing of the step to any obstruction above, including "
       "soffits of upper flights."),
      ("Landings",
       "A landing must be provided at every floor level and at intermediate levels where the "
       "flight changes direction. The minimum landing depth must equal the stair width but need "
       "not exceed 1300 mm for straight staircases. For curved landings, DIN 18065 applies.")]
    ),
    ("§ 24–28 Räume – Room and Space Requirements",
     [("Minimum Living Room Area",
       "The minimum floor area of a habitable living room (Aufenthaltsraum) is 10 m². "
       "This includes living rooms, dining rooms and studies but excludes kitchens, bathrooms, "
       "corridors and storage rooms. In studio apartments the combined living/sleeping room must "
       "be at least 14 m²."),
      ("Minimum Bedroom Area",
       "Individual bedrooms must have a minimum area of 8 m². Master bedrooms should be at "
       "least 12 m² to enable barrier-free use. Children's bedrooms must be at least 8 m²."),
      ("Minimum Ceiling Height",
       "Habitable rooms must have a minimum average clear ceiling height of 2500 mm. "
       "In rooms with sloped ceilings (Dachschrägen), at least 50% of the floor area must "
       "have a clear height of 2200 mm. Bathrooms and WCs may have a minimum height of 2200 mm."),
      ("Kitchen Requirements",
       "Kitchens must have a minimum floor area of 5 m² with a minimum width of 1800 mm to "
       "allow for a work triangle. Natural or mechanical ventilation must be provided. A "
       "connection point for a range hood venting to the outside is recommended."),
      ("Bathroom and WC",
       "Every dwelling must contain at least one bathroom with toilet, washbasin, and either "
       "a bathtub or shower enclosure of at least 900 mm × 900 mm. The minimum floor area of "
       "a combined bathroom/WC is 3.5 m². A separate WC must have a minimum dimension of "
       "900 mm × 1300 mm.")]
    ),
    ("§ 29–33 Decken & Böden – Slab and Floor Requirements",
     [("Minimum Slab Thickness",
       "Reinforced concrete floor slabs must have a minimum thickness of 180 mm for spans up "
       "to 5.0 m. For larger spans, thickness shall be determined by structural calculation "
       "in accordance with DIN EN 1992-1-1 (Eurocode 2). The minimum thickness for screed "
       "topping is 45 mm (floating screed) or 35 mm (bonded screed)."),
      ("Live Load Capacity",
       "Residential floor slabs must be designed for a minimum live load of 2.0 kN/m² per "
       "DIN EN 1991-1-1. Office floors must be designed for 3.0 kN/m². Staircases and balconies "
       "must be designed for 4.0 kN/m². Assembly areas require 5.0 kN/m²."),
      ("Acoustic Performance",
       "Floor/ceiling assemblies between dwellings must achieve a minimum weighted impact sound "
       "pressure level of L'nw ≤ 53 dB per DIN 4109-1. This typically requires a floating screed "
       "with an impact sound insulation layer of at least 30 mm mineral wool."),
      ("Waterproofing",
       "Floors in wet areas (bathrooms, kitchens, utility rooms) must be waterproofed in "
       "accordance with DIN 18195. Waterproofing must extend at least 150 mm up adjoining walls. "
       "Basement slabs must incorporate a waterproofing membrane rated for permanent hydrostatic "
       "pressure where groundwater is present."),
      ("Balcony and Terrace Slabs",
       "Balcony slabs must have an adequate fall away from the building of at least 1.5% to "
       "ensure drainage. The structural edge must include a drip groove. Cantilevered balconies "
       "must account for the thermal bridge effect at the slab edge.")]
    ),
    ("§ 34–38 Brandschutz – Fire Safety Requirements",
     [("Fire Resistance Ratings",
       "The following minimum fire resistance is required: external walls F60-AB (REI60), "
       "load-bearing internal walls F90-AB (REI90), floor slabs F90-AB (REI90), columns "
       "F90-AB (R90), roof structures F30-AB (REI30) for buildings under 7m height."),
      ("Escape Routes",
       "Every habitable room must have at least one direct escape route to the open air. "
       "Maximum travel distance from any point to the nearest exit must not exceed 35 m for "
       "residential buildings and 25 m for high-hazard commercial uses. Two independent escape "
       "routes must be provided for floors above the second storey."),
      ("Fire Suppression",
       "Buildings with gross floor area exceeding 3600 m² per fire compartment must be provided "
       "with automatic sprinkler systems in accordance with DIN EN 12845. High-rise buildings "
       "above 22 m must incorporate fire-fighting shafts."),
      ("Emergency Lighting",
       "Emergency lighting must be installed on all escape routes to ensure a minimum "
       "illumination of 1 lux at floor level for a duration of at least 1 hour on battery "
       "backup per DIN EN 1838."),
      ("Smoke Control",
       "Natural smoke exhaust openings with a free area of at least 1 m² per 500 m² floor area "
       "must be provided in basement levels and internal stairwells. Mechanical smoke control "
       "systems are required for buildings where natural ventilation is insufficient.")]
    ),
    ("§ 39–43 Barrierefreiheit – Barrier-Free Access",
     [("General Accessibility",
       "All public buildings and multi-family dwellings with more than 2 units must be "
       "accessible to persons with disabilities. At least 5% of parking spaces must be "
       "adapted wheelchair parking spaces with minimum dimensions of 3500 mm × 5000 mm."),
      ("Wheelchair Ramps",
       "Where level access is not possible, ramps must be provided with a maximum gradient of "
       "1:20 (5%) for public buildings and 1:12 (8.3%) for residential paths. Minimum ramp "
       "width is 1500 mm with handrails at 850–900 mm on both sides. Intermediate landings of "
       "1500 mm depth are required every 6.0 m of ramp length."),
      ("Lift Provisions",
       "Residential buildings with more than 3 storeys must provide a passenger lift serving "
       "all floors. Minimum internal lift dimensions are 1100 mm wide × 1400 mm deep with a "
       "minimum door width of 900 mm as per DIN 18040-1."),
      ("Accessible Toilets",
       "Public buildings must provide at least one accessible WC per floor. Minimum dimensions "
       "are 1650 mm × 2200 mm. A clear transfer space of 950 mm must be provided on at least "
       "one side of the WC pan. Grab rails must be installed per DIN 18040-1."),
      ("Tactile Guidance Systems",
       "Train stations, airports, public administration buildings, and schools must install "
       "tactile guidance systems for visually impaired users. Tactile warning strips of 600 mm "
       "depth must be installed in front of all stair heads and platform edges.")]
    ),
    ("§ 44–50 Anhang – Appendices and Reference Tables",
     [("Table A1 – Minimum Dimensions Summary",
       "The following table summarizes the key minimum dimensional requirements of this code:\n"
       "  Doors (standard):         Width 900 mm, Height 2000 mm\n"
       "  Doors (fire escape):      Width 1050 mm, Height 2100 mm\n"
       "  Windows (min. glazed area):  1/8 of room floor area\n"
       "  External walls (masonry):    240 mm minimum thickness\n"
       "  Fire walls:                  240 mm minimum thickness\n"
       "  Partition walls:             100 mm minimum thickness\n"
       "  Stairs (residential):        1000 mm minimum width\n"
       "  Stair riser:                 Maximum 190 mm\n"
       "  Stair going:                 Minimum 260 mm\n"
       "  Living room:                 10 m² minimum area\n"
       "  Bedroom:                     8 m² minimum area\n"
       "  Ceiling height (habitable):  2500 mm minimum\n"
       "  Floor slab thickness:        180 mm minimum"),
      ("Table A2 – Fire Resistance Requirements",
       "Building Class 1 (up to 7m, 2 units): F30 for load-bearing elements\n"
       "Building Class 2 (up to 7m, ≤2 units per floor): F30\n"
       "Building Class 3 (up to 7m, more units): F60 for walls/slabs, F30 for roof\n"
       "Building Class 4 (7m–13m): F90-AB for walls and slabs, F60 for roof\n"
       "Building Class 5 (>13m, high-rise): F90-AB for all, active fire suppression required"),
      ("Referenced DIN Standards",
       "DIN 18040-1: Barrier-free building – public buildings\n"
       "DIN 18040-2: Barrier-free building – dwellings\n"
       "DIN 18065: Staircases in buildings – terminology, measuring rules, main dimensions\n"
       "DIN 4109-1: Sound insulation in buildings – minimum requirements\n"
       "DIN 18195: Waterproofing of buildings\n"
       "DIN EN 1992: Eurocode 2 – Reinforced concrete design\n"
       "DIN EN 1996: Eurocode 6 – Masonry design\n"
       "DIN EN 12845: Fixed firefighting systems – sprinklers\n"
       "DIN EN 1838: Applied lighting – emergency lighting"),
      ("Glossary",
       "Aufenthaltsraum: Habitable room suitable for extended human occupation.\n"
       "Brandwand: Fire wall providing total compartmentation between buildings.\n"
       "Flur: Internal corridor or hallway acting as access route.\n"
       "GRZ (Grundflächenzahl): Site coverage ratio, defines buildable area on a plot.\n"
       "GFZ (Geschossflächenzahl): Floor area ratio relative to plot size.\n"
       "Lichte Breite: Clear (unobstructed) width of a door or opening.\n"
       "NBauO: Niedersächsische Bauordnung – this code.\n"
       "Rohbaumaß: Structural opening dimension before frame installation."),
      ("Enforcement and Penalties",
       "Non-compliance with this code may result in:\n"
       "a) Construction stop orders issued by the lower building authority.\n"
       "b) Administrative fines of up to EUR 500,000 for serious violations.\n"
       "c) Mandatory demolition orders for structures that cannot be brought into compliance.\n"
       "d) Criminal prosecution in cases of gross negligence causing injury or death.\n"
       "Building permits may be revoked if construction deviates materially from the approved "
       "drawings. Owners are responsible for ensuring ongoing compliance during use.")]
    ),
]

# ---- PDF Generator ----------------------------------------------------------

class RulebookPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "Niedersaechsische Bauordnung (NBauO) - Demo Edition", align="L", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "DEMO DOCUMENT - Not legally binding. For testing purposes only.", align="C", new_x="LMARGIN", new_y="NEXT")


def generate_pdf(output_path):
    pdf = RulebookPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 20, 15)

    # ---- Title page ----------------------------------------------------------
    pdf.add_page()
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 60, 120)
    pdf.multi_cell(0, 12, "Niedersaechsische Bauordnung", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, "(NBauO)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 8, "Building Code of Lower Saxony\nDemonstration Reference Edition", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(0.8)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7,
        s("This document is a demonstration excerpt for testing building code compliance "
        "software. It contains realistic German building regulations covering doors, windows, "
        "walls, staircases, rooms, floor slabs, fire safety, and barrier-free access. "
        "All dimensional requirements, DIN standard references and regulatory provisions "
        "are modelled on the actual NBauO but are intended for demo purposes only."),
        align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 8, "Table of Contents", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for i, (section_title, subsections) in enumerate(SECTIONS, 1):
        pdf.cell(10, 7, f"{i}.", new_x="RIGHT", new_y="TOP")
        pdf.cell(0, 7, s(section_title), new_x="LMARGIN", new_y="NEXT")
        for sub_title, _ in subsections:
            pdf.cell(15, 6, "", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 6, f"- {s(sub_title)}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)

    # ---- Content pages -------------------------------------------------------
    for section_title, subsections in SECTIONS:
        pdf.add_page()
        # Section heading
        pdf.set_fill_color(30, 60, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, f"  {s(section_title)}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        for sub_title, body in subsections:
            pdf.set_text_color(30, 60, 120)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, s(sub_title), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, s(body), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # Add a filler page of compliance notes per section for page count
        pdf.add_page()
        pdf.set_fill_color(245, 247, 252)
        pdf.set_text_color(30, 60, 120)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 9, f"  Compliance Notes & Worked Examples - {s(section_title)}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 10)

        example_texts = [
            "When checking IFC models against this section, verify that the OverallWidth "
            "property of IfcDoor entities meets the minimum clear width requirement. "
            "Note that IfcDoor.OverallWidth represents the nominal opening width; "
            "the clear width after frame installation is typically 10-20 mm less.",
            "For automated compliance checking via BIM tools, extract the property set "
            "Pset_DoorCommon and check the IsExternal flag to distinguish between internal "
            "doors (min 900 mm) and external entrance doors (min 900 mm). Fire doors in "
            "Pset_DoorCommon.FireRating must correspond to the required rating.",
            "Wall thickness is stored in IfcWallCommonProperties or in the associated "
            "IfcMaterialLayerSetUsage. When checking wall thickness, ensure the structural "
            "layer thickness is measured, not the total construction including finishes.",
            "Room areas for IfcSpace elements should be read from Qto_SpaceBaseQuantities. "
            "The GrossFloorArea quantity represents the gross area including walls, while "
            "NetFloorArea (or NetArea) represents the usable area. Code compliance should "
            "use NetFloorArea for minimum room area checks.",
            "For stair compliance, check IfcStairFlight for tread and riser dimensions via "
            "IfcStairFlightType or associated property sets. The number of risers multiplied "
            "by riser height must equal the total rise of the flight.",
        ]
        for et in example_texts:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(6, 6, ">", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, et, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        # Small reference table
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 228, 245)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(90, 7, "Parameter", border=1, fill=True, new_x="RIGHT", new_y="TOP")
        pdf.cell(90, 7, "Required Value", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(40, 40, 40)
        rows = [
            ("Min. door width (standard)", ">= 900 mm"),
            ("Min. door width (fire escape)", ">= 1050 mm"),
            ("Min. door height", ">= 2000 mm"),
            ("Min. window area", ">= 1/8 room floor area"),
            ("Min. external wall thickness", ">= 240 mm"),
            ("Min. partition wall thickness", ">= 100 mm"),
            ("Min. stair width (residential)", ">= 1000 mm"),
            ("Max. stair riser", "<= 190 mm"),
            ("Min. stair going", ">= 260 mm"),
            ("Min. living room area", ">= 10 m2"),
            ("Min. bedroom area", ">= 8 m2"),
            ("Min. ceiling height", ">= 2500 mm"),
            ("Min. slab thickness (RC)", ">= 180 mm"),
        ]
        for param, value in rows:
            pdf.cell(90, 6, param, border=1, new_x="RIGHT", new_y="TOP")
            pdf.cell(90, 6, value, border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    print(f"PDF saved: {output_path}  ({pdf.page_no()} pages)")


if __name__ == "__main__":
    out = f"{OUT_DIR}/demo_nbauo_rulebook.pdf"
    generate_pdf(out)
    print("Page count:", end=" ")
