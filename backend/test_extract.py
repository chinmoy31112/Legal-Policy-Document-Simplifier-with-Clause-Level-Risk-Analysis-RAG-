import asyncio
from pathlib import Path
from app.document_processing import extract_document
from app.config import get_settings

def test_extract():
    print("Extracting...")
    try:
        # Create a dummy PDF
        import fpdf
        pdf = fpdf.FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="This is a test PDF.", ln=1, align="C")
        pdf_path = Path("test.pdf")
        pdf.output(str(pdf_path))
        
        result = extract_document(pdf_path)
        print("Success!", len(result.raw_text))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_extract()
