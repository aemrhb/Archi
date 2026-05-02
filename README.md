# IFC File Element Viewer

A Python-based web application to open and analyze IFC (Industry Foundation Classes) files and display all their elements.

## Features

- 📁 Upload IFC files via web interface
- 🔍 View all elements in the IFC file
- 📊 Display statistics (total elements, element types)
- 🔎 Search and filter elements by type or name
- 📈 Element type summary with counts
- 🎨 Modern Streamlit UI

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the URL shown (usually `http://localhost:8501`)
3. Click "Upload your IFC model" and select an IFC file
4. Browse the elements grouped by type
5. Use the search box to filter elements

## Technical Details

The application uses:
- **Streamlit** for the web interface
- **ifcopenshell** for parsing IFC files (industry-standard library)
- **pandas** for data manipulation and display

## File Format

Supports IFC files (.ifc). The parser extracts:
- Element types (IfcWall, IfcSlab, IfcBeam, IfcDoor, etc.)
- Element names
- GlobalIds
- Tags
- Level/Storey information

## Alternative: JavaScript Version

If you prefer a client-side only solution (no Python required), use `index.html` and `app.js` instead.

