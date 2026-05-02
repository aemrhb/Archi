from fpdf import FPDF

def create_hoai_german_contract(filename, costs, fee, difficult=False):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, text="ARCHITEKTENVERTRAG", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 10, text="Gegenstand der Vereinbarung gemäss HOAI 2013", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    # Project Info
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="1. Gegenstand des Projekts", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", '', 11)
    pdf.multi_cell(0, 7, text="Gegenstand dieses Vertrages ist die Objektplanung fuer den Neubau eines Buerogebaeudes in Berlin (Leistungsbild Gebaeude und Innenraeume gem. § 34 HOAI).")
    pdf.ln(5)
    
    # Costs and Fee
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="2. Honorargrundlagen und Vereinbarung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", '', 11)
    
    # Using .replace to avoid encoding issues with Euro symbol in some environments, but fpdf2 supports it
    data = [
        ["Anrechenbare Kosten (Netto)", f"{costs:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")],
        ["Honorarzone", "III (Mittelschwer)"],
        ["Leistungsphasen (LPH)", "1 bis 5 (Teilbeauftragung)"],
        ["Vereinbartes Pauschalhonorar", f"{fee:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")]
    ]
    
    for row in data:
        pdf.cell(90, 10, text=row[0], border=1)
        pdf.cell(70, 10, text=row[1], border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Details on Phases
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, text="Aufschluesselung der beauftragten Leistungsphasen:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", '', 10)
    pdf.multi_cell(0, 7, text="LPH 1: Grundlagenermittlung (2%)\nLPH 2: Vorplanung (7%)\nLPH 3: Entwurfsplanung (15%)\nLPH 4: Genehmigungsplanung (3%)\nLPH 5: Ausfuehrungsplanung (25%)\nSumme der Anteile: 52% der Grundleistungen.")
    pdf.ln(5)
    
    # Special Clues
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="3. Besondere Umstaende / Erschwernisse", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", '', 11)
    if difficult:
        pdf.multi_cell(0, 7, text="Besondere Anforderungen: Das Bauvorhaben unterliegt strengen Auflagen des Denkmalschutzes (Ensembleschutz). Zudem erschweren die extreme Hanglage des Grundstuecks und die unmittelbare Naehe zu einer Bahntrasse die Planungs- und Genehmigungsprozesse erheblich.")
    else:
        pdf.multi_cell(0, 7, text="Besondere Erschwernisse sind zum Zeitpunkt des Vertragsschlusses nicht bekannt. Das Grundstueck ist eben und frei von Altlasten.")
        
    pdf.ln(10)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.cell(90, 10, text="________________________", new_x="RIGHT", new_y="TOP")
    pdf.cell(90, 10, text="________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 10, text="Ort, Datum, Auftraggeber", new_x="RIGHT", new_y="TOP")
    pdf.cell(90, 10, text="Ort, Datum, Architekt", new_x="LMARGIN", new_y="NEXT")
    
    pdf.output(filename)

# LEGAL CALCULATION CHECK:
# Costs 2.5M, Zone III, 100% Fee is approx 218k.
# 52% of 218k = 113.360 EUR.

# CLEAN
create_hoai_german_contract("e:/check-my/archi/hoai_test_deutsch_korrekt.pdf", costs=2500000, fee=113360, difficult=False)

# SUSPICIOUS
create_hoai_german_contract("e:/check-my/archi/hoai_test_deutsch_fehlerhaft.pdf", costs=2500000, fee=90000, difficult=True)

print("Deutschsprachige Testvertraege wurden erstellt.")
