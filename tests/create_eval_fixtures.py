"""
Generate test PDF fixtures for Phase 2 Evaluation.

Generates 4 realistic legal test PDFs across 4 document types, plus
corrupt, empty, encrypted, and image-only scanned PDFs to test robustness.
"""

import json
from pathlib import Path
import fitz  # PyMuPDF

FIXTURES_DIR = Path(__file__).resolve().parent / "eval_data" / "segmentation_set"
CORRUPT_DIR = Path(__file__).resolve().parent / "eval_data" / "corrupt_set"

FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
CORRUPT_DIR.mkdir(parents=True, exist_ok=True)


DOCUMENTS = {
    "doc_tos.pdf": {
        "title": "TERMS OF SERVICE",
        "clauses": [
            ("1. ACCEPTANCE OF TERMS", "By accessing or using the platform, you agree to be bound by these Terms of Service and all applicable federal and state laws."),
            ("2. USER ACCOUNT AND SECURITY", "You are responsible for maintaining the confidentiality of your credentials and for all activities that occur under your user account."),
            ("3. LIMITATION OF LIABILITY", "IN NO EVENT SHALL THE COMPANY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, OR PUNITIVE DAMAGES ARISING FROM USE OF THE SERVICE."),
            ("4. TERMINATION", "We reserve the right to suspend or terminate your access to the service immediately without prior notice for any material breach of these terms."),
            ("5. GOVERNING LAW", "These terms shall be governed by and construed in accordance with the laws of the State of Delaware without regard to conflict of law principles."),
        ],
    },
    "doc_privacy.pdf": {
        "title": "PRIVACY POLICY",
        "clauses": [
            ("1. INFORMATION WE COLLECT", "We collect personal information that you provide directly, including name, email address, payment details, and device identifiers."),
            ("2. HOW WE USE YOUR INFORMATION", "We use your personal data to operate, maintain, enhance, and deliver the features of our service and communicate with you."),
            ("3. THIRD-PARTY DATA DISCLOSURE", "We do not sell your personal data. We disclose information to trusted cloud infrastructure providers under strict confidentiality agreements."),
            ("4. DATA RETENTION", "We retain personal data only for as long as necessary to fulfill the purposes outlined in this policy or comply with legal obligations."),
        ],
    },
    "doc_employment.pdf": {
        "title": "EXECUTIVE EMPLOYMENT AGREEMENT",
        "clauses": [
            ("Section 1. Position and Duties", "Employee shall serve as Vice President of Engineering and report directly to the Chief Executive Officer, devoting full business time and efforts."),
            ("Section 2. Compensation and Benefits", "The Company shall pay Employee a base annual salary of $220,000, payable in accordance with the standard payroll schedule."),
            ("Section 3. Restrictive Covenants and Non-Compete", "During employment and for twelve (12) months following termination, Employee shall not directly engage with any competing business in the territory."),
            ("Section 4. Intellectual Property Assignment", "All inventions, patent applications, and original works created by Employee during the course of employment are works-for-hire assigned exclusively to the Company."),
        ],
    },
    "doc_nda.pdf": {
        "title": "MUTUAL NON-DISCLOSURE AGREEMENT",
        "clauses": [
            ("Article 1. Definition of Confidential Information", "Confidential Information includes all non-public technical, financial, and business proprietary information disclosed by either party."),
            ("Article 2. Non-Disclosure Obligations", "Each receiving party agrees to protect the disclosing party's Confidential Information with the same degree of care it uses for its own confidential data."),
            ("Article 3. Exclusions from Confidentiality", "Obligations do not apply to information that is publicly known through no breach, or independently developed without reference to the disclosure."),
            ("Article 4. Term and Termination", "This Agreement shall remain in effect for a period of two (2) years from the Effective Date, surviving any earlier termination."),
        ],
    },
}


def create_sample_pdfs():
    """Create the 4 realistic test PDFs with PyMuPDF."""
    ground_truth = []

    for filename, doc_spec in DOCUMENTS.items():
        doc_path = FIXTURES_DIR / filename
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)  # Standard Letter size

        # Insert main title (bold, 18pt)
        page.insert_text(
            (72, 72),
            doc_spec["title"],
            fontsize=18,
            fontname="helv",
            color=(0, 0, 0),
        )

        y = 120
        doc_clauses = []
        for idx, (title, content) in enumerate(doc_spec["clauses"]):
            # Insert section title (bold, 12pt)
            page.insert_text(
                (72, y),
                title,
                fontsize=12,
                fontname="helv",
                color=(0, 0, 0),
            )
            y += 20

            # Insert body text
            rect = fitz.Rect(72, y, 540, y + 60)
            page.insert_textbox(rect, content, fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))
            y += 70

            doc_clauses.append({
                "order": idx + 1,
                "title": title,
                "text_snippet": content[:50],
            })

        doc.save(str(doc_path))
        doc.close()

        ground_truth.append({
            "document": filename,
            "title": doc_spec["title"],
            "expected_clauses": len(doc_spec["clauses"]),
            "clauses": doc_clauses,
        })

    (FIXTURES_DIR / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"Generated 4 test PDFs in {FIXTURES_DIR}")


def create_corrupt_test_files():
    """Create empty, corrupt, encrypted, and image-only scanned files."""
    # 1. 0-byte empty file
    (CORRUPT_DIR / "empty_file.pdf").write_bytes(b"")

    # 2. Corrupt garbage PDF
    (CORRUPT_DIR / "corrupt_file.pdf").write_bytes(b"%PDF-1.4\nBROKEN_GARBAGE_BYTES_CORRUPTED_STREAM")

    # 3. Scanned image-only PDF (creates page with a drawn raster rectangle and 0 text)
    doc_scan = fitz.open()
    page_scan = doc_scan.new_page(width=612, height=792)
    # Draw an image/pixmap to simulate scanned raster document
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 300, 300), 0)
    pix.clear_with(200)
    page_scan.insert_image(fitz.Rect(50, 50, 500, 700), pixmap=pix)
    doc_scan.save(str(CORRUPT_DIR / "scanned_image.pdf"))
    doc_scan.close()

    # 4. Encrypted password-protected PDF
    doc_enc = fitz.open()
    p_enc = doc_enc.new_page(width=612, height=792)
    p_enc.insert_text((72, 72), "CONFIDENTIAL PASSWORD PROTECTED", fontsize=14)
    doc_enc.save(
        str(CORRUPT_DIR / "encrypted_file.pdf"),
        encryption=fitz.PDF_ENCRYPT_AES_256,
<<<<<<< HEAD
        user_pw="mock_test_password_123",
        owner_pw="mock_test_owner_123",
=======
        user_pw="secret123",
        owner_pw="owner123",
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
    )
    doc_enc.close()
    print(f"Generated corrupt/scanned test suite in {CORRUPT_DIR}")


if __name__ == "__main__":
    create_sample_pdfs()
    create_corrupt_test_files()
