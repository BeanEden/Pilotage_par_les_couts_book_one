import os
import datetime
import pandas as pd
import streamlit as st
from fpdf import FPDF

def create_export_dir():
    """Crée le répertoire export s'il n'existe pas."""
    if not os.path.exists("export"):
        os.makedirs("export")

class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        # Utiliser un tiret standard au lieu du tiret cadratin pour éviter les erreurs d'encodage
        self.cell(0, 10, "Rapport de Pilotage - Amazon Beta Mobile", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | Genere le {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, "C")

def safe_text(text):
    """Nettoie le texte pour éviter les erreurs d'encodage FPDF (Latin-1)."""
    if text is None: return ""
    s = str(text)
    s = s.replace("—", "-").replace("–", "-")
    s = s.replace("€", "EUR")
    s = s.replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e")
    s = s.replace("à", "a").replace("â", "a")
    s = s.replace("ô", "o").replace("û", "u").replace("ï", "i").replace("î", "i")
    s = s.replace("ç", "c")
    # On peut aussi encoder/décoder pour supprimer tout ce qui n'est pas latin-1
    return s.encode('latin-1', 'replace').decode('latin-1')

def export_page_to_pdf(page_title, kpis, tables=None, config=None):
    """
    Génère un PDF pour la page actuelle.
    """
    create_export_dir()
    
    pdf = PDFReport()
    pdf.add_page()
    
    # Titre de la page
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, safe_text(page_title.upper()), 0, 1, "L")
    pdf.ln(5)
    
    # Paramètres
    if config:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Configuration :", 0, 1, "L")
        pdf.set_font("Arial", "", 9)
        conf_str = " | ".join([f"{k}: {v}" for k, v in config.items()])
        pdf.multi_cell(0, 5, safe_text(conf_str))
        pdf.ln(5)

    # KPIs
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Indicateurs Cles (KPIs)", 0, 1, "L")
    pdf.set_font("Arial", "", 10)
    
    items = list(kpis.items())
    for i in range(0, len(items), 2):
        k1, v1 = items[i]
        line = f"- {k1} : {v1}"
        if i + 1 < len(items):
            k2, v2 = items[i+1]
            line += f"    |    - {k2} : {v2}"
        pdf.cell(0, 8, safe_text(line), 0, 1, "L")
    
    pdf.ln(10)
    
    # Tables
    if tables:
        for title, df in tables:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, safe_text(title), 0, 1, "L")
            pdf.set_font("Arial", "", 8)
            
            cols = df.columns.tolist()
            cw = 190 / max(1, len(cols))
            
            pdf.set_fill_color(240, 240, 240)
            for col in cols:
                pdf.cell(cw, 8, safe_text(col), 1, 0, "C", fill=True)
            pdf.ln()
            
            pdf.set_fill_color(255, 255, 255)
            for _, row in df.head(40).iterrows():
                for val in row:
                    pdf.cell(cw, 7, safe_text(val)[:20], 1, 0, "C")
                pdf.ln()
            pdf.ln(5)

    return bytes(pdf.output())
