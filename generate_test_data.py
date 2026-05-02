from fpdf import FPDF

def create_hoai_pdf(filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HOAI Section Excerpt (Sample)", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Section 34: Fees for Building Design (Gebaeude)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 10, txt="Rule: Fees are based on chargeable costs and complexity zones (I-V).")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, txt="Fee Table Summary (Zone III Central):", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 10, txt="Costs: 1,000,000 EUR", border=1)
    pdf.cell(100, 10, txt="Fee: 110,000 EUR", border=1, ln=True)
    pdf.cell(100, 10, txt="Costs: 2,500,000 EUR", border=1)
    pdf.cell(100, 10, txt="Fee: 245,000 EUR", border=1, ln=True)
    pdf.cell(100, 10, txt="Costs: 5,000,000 EUR", border=1)
    pdf.cell(100, 10, txt="Fee: 430,000 EUR", border=1, ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, txt="Section 35: Service Phases (Leistungsphasen):", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 10, txt="1. Basic Evaluation: 2%\n2. Preliminary Design: 7%\n3. Final Design: 15%\n4. Building Permit: 3%\n5. Execution Drawings: 25%\n6. Preparation: 10%\n7. Tendering: 4%\n8. Construction: 32%\n9. Handover: 2%")
    
    pdf.output(filename)

def create_contract_pdf(filename, costs, fee, difficult=False):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Project Contract: Office Renovation", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, txt=f"Project scope includes the renovation of the city center office block.")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, txt="Project Parameter", border=1)
    pdf.cell(100, 10, txt="Value", border=1, ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 10, txt="Estimated Baukosten (Costs)", border=1)
    pdf.cell(100, 10, txt=f"{costs} EUR", border=1, ln=True)
    pdf.cell(100, 10, txt="Agreed Architect Fee", border=1)
    pdf.cell(100, 10, txt=f"{fee} EUR", border=1, ln=True)
    pdf.cell(100, 10, txt="Service Phases", border=1)
    pdf.cell(100, 10, txt="1, 2, 3, 4, 5", border=1, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 11)
    if difficult:
        pdf.multi_cell(0, 10, txt="Special Conditions: The building is a historic landmark (Denkmalschutz) and is situated on a steep slope next to an active railway line.")
    else:
        pdf.multi_cell(0, 10, txt="Special Conditions: Standard flat terrain, no special constraints.")
        
    pdf.output(filename)

# Generate the files
create_hoai_pdf("e:/check-my/archi/test_hoai_ref.pdf")
create_contract_pdf("e:/check-my/archi/test_contract_clean.pdf", costs=2500000, fee=127400, difficult=False) # Roughly 52% of 245k
create_contract_pdf("e:/check-my/archi/test_contract_suspicious.pdf", costs=2500000, fee=80000, difficult=True) # Fee is too low for heritage difficulty
print("Generated 3 test files.")
