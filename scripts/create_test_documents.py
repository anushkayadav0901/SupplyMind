"""
Generate sample procurement documents for testing SupplyMind.

Creates realistic invoices and purchase orders as PDFs using PyMuPDF.
These can be uploaded through the frontend to test:
  - OCR / text extraction
  - Entity extraction (vendor, amounts, dates)
  - Risk prediction
  - RAG indexing and Q&A
"""

import fitz  # PyMuPDF
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "test_documents"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_pdf(filename: str, lines: list[str]) -> Path:
    """Create a simple text-based PDF from a list of lines."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    y = 50
    for line in lines:
        # Bold for headers
        if line.startswith("===") or line.startswith("---"):
            continue
        fontsize = 14 if line.isupper() or line.startswith("INVOICE") or line.startswith("PURCHASE") else 10
        fontname = "helv"
        page.insert_text((50, y), line, fontsize=fontsize, fontname=fontname)
        y += fontsize + 6
        if y > 790:
            page = doc.new_page(width=595, height=842)
            y = 50

    path = OUTPUT_DIR / filename
    doc.save(str(path))
    doc.close()
    print(f"  ✅ Created: {path}")
    return path


def invoice_1():
    """Acme Industrial Supplies - Office Equipment Invoice"""
    return create_pdf("invoice_acme_industrial.pdf", [
        "INVOICE",
        "",
        "Invoice No: INV-2026-0042",
        "Date: June 1, 2026",
        "Due Date: July 1, 2026",
        "Payment Terms: Net 30",
        "",
        "FROM:",
        "Acme Industrial Supplies Pvt. Ltd.",
        "GSTIN: 07AABCA1234F1Z5",
        "PAN: AABCA1234F",
        "Address: 45 Nehru Place, New Delhi 110019",
        "Phone: +91 11 2345 6789",
        "Email: accounts@acmeindustrial.in",
        "",
        "BILL TO:",
        "SupplyMind Technologies Pvt. Ltd.",
        "GSTIN: 29AADCS5678G1ZP",
        "12th Floor, Tower B, Cyber Park",
        "Whitefield, Bengaluru 560066",
        "",
        "ITEMS:",
        "-------------------------------------------------------------",
        "Sl.  Description              Qty   Unit Price   Total",
        "-------------------------------------------------------------",
        "1    Ergonomic Office Chair    25    12,500.00    3,12,500.00",
        "2    Standing Desk (L-Shape)   10    28,000.00    2,80,000.00",
        "3    Monitor Arm (Dual)        25     4,200.00    1,05,000.00",
        "4    Cable Management Kit      50       850.00      42,500.00",
        "-------------------------------------------------------------",
        "                              Subtotal:         7,40,000.00",
        "                              CGST (9%):          66,600.00",
        "                              SGST (9%):          66,600.00",
        "                              TOTAL:            8,73,200.00",
        "-------------------------------------------------------------",
        "",
        "Amount in words: Eight Lakh Seventy Three Thousand Two Hundred Only",
        "",
        "Bank Details:",
        "Bank: HDFC Bank, Connaught Place Branch",
        "Account: 50100123456789",
        "IFSC: HDFC0000123",
        "",
        "Terms & Conditions:",
        "1. Payment due within 30 days of invoice date.",
        "2. Late payment attracts 1.5% interest per month.",
        "3. Warranty: 3 years on chairs and desks.",
        "4. Delivery within 7-10 business days.",
    ])


def invoice_2():
    """GlobalTech Solutions - IT Services Invoice"""
    return create_pdf("invoice_globaltech_it.pdf", [
        "INVOICE",
        "",
        "Invoice No: GT-INV-2026-1187",
        "Date: May 15, 2026",
        "Due Date: June 14, 2026",
        "Payment Terms: Net 30",
        "",
        "FROM:",
        "GlobalTech Solutions Ltd.",
        "GSTIN: 27AADCG9876H1ZQ",
        "PAN: AADCG9876H",
        "Address: 302 Tech Hub, BKC, Mumbai 400051",
        "Phone: +91 22 6789 0123",
        "Email: billing@globaltechsolutions.com",
        "Website: www.globaltechsolutions.com",
        "",
        "BILL TO:",
        "SupplyMind Technologies Pvt. Ltd.",
        "12th Floor, Tower B, Cyber Park",
        "Whitefield, Bengaluru 560066",
        "",
        "SERVICE DETAILS:",
        "-------------------------------------------------------------",
        "Sl.  Description                    Qty    Rate       Total",
        "-------------------------------------------------------------",
        "1    Cloud Infrastructure Setup      1    4,50,000   4,50,000",
        "2    Annual AWS Management           12     85,000  10,20,000",
        "3    Security Audit & Pen Testing    1    2,75,000   2,75,000",
        "4    24x7 DevOps Support (Annual)    1    6,00,000   6,00,000",
        "5    SSL Certificate (Wildcard)      5      8,500      42,500",
        "-------------------------------------------------------------",
        "                              Subtotal:        23,87,500.00",
        "                              IGST (18%):       4,29,750.00",
        "                              TOTAL:           28,17,250.00",
        "-------------------------------------------------------------",
        "",
        "Amount: Twenty Eight Lakh Seventeen Thousand Two Hundred Fifty Only",
        "",
        "Bank Details:",
        "Bank: ICICI Bank, BKC Branch",
        "Account: 123456789012",
        "IFSC: ICIC0001234",
        "",
        "Notes:",
        "- SLA: 99.9% uptime guarantee",
        "- Support response time: Critical < 15 mins",
        "- Contract period: April 2026 - March 2027",
    ])


def purchase_order_1():
    """Purchase Order for Raw Materials"""
    return create_pdf("po_rawmaterials_2026.pdf", [
        "PURCHASE ORDER",
        "",
        "PO Number: PO-2026-00389",
        "Date: May 28, 2026",
        "Expected Delivery: June 15, 2026",
        "Shipping Method: Standard Ground (3-5 days)",
        "",
        "VENDOR:",
        "Bharat Raw Materials Corp.",
        "GSTIN: 33AABCB4567J1ZR",
        "PAN: AABCB4567J",
        "Plot 12, SIPCOT Industrial Complex",
        "Hosur, Tamil Nadu 635109",
        "Contact: Rajesh Kumar",
        "Phone: +91 98765 43210",
        "Email: sales@bharatrawmaterials.co.in",
        "",
        "SHIP TO:",
        "SupplyMind Warehouse",
        "Survey No. 45, Peenya Industrial Area",
        "Bengaluru, Karnataka 560058",
        "",
        "ORDER DETAILS:",
        "-------------------------------------------------------------",
        "Sl.  Item                   Qty     Unit    Rate      Total",
        "-------------------------------------------------------------",
        "1    Steel Sheet (2mm)      500     Kg      95.00     47,500",
        "2    Aluminium Rod (10mm)   200     Kg     210.00     42,000",
        "3    Copper Wire (1.5mm)    100     Kg     650.00     65,000",
        "4    Rubber Gasket Set      1000    Pcs      12.50    12,500",
        "5    Industrial Adhesive    50      Ltr     320.00    16,000",
        "-------------------------------------------------------------",
        "                              Subtotal:       1,83,000.00",
        "                              IGST (18%):       32,940.00",
        "                              Freight:           5,500.00",
        "                              TOTAL:          2,21,440.00",
        "-------------------------------------------------------------",
        "",
        "TERMS:",
        "1. 50% advance payment, 50% on delivery.",
        "2. Quality inspection at receiving warehouse.",
        "3. Reject rate must be below 2%.",
        "4. Material test certificates required.",
        "5. Late delivery penalty: 1% per day (max 10%).",
    ])


def vendor_contract():
    """Annual Maintenance Contract"""
    return create_pdf("contract_maintenance_annual.pdf", [
        "ANNUAL MAINTENANCE CONTRACT (AMC)",
        "",
        "Contract No: AMC-2026-0055",
        "Effective Date: April 1, 2026",
        "Expiry Date: March 31, 2027",
        "Auto-Renewal: Yes (with 30-day notice to cancel)",
        "",
        "SERVICE PROVIDER:",
        "QuickFix Facility Services Pvt. Ltd.",
        "GSTIN: 29AADCQ3456K1ZS",
        "PAN: AADCQ3456K",
        "23, 100 Feet Road, Indiranagar",
        "Bengaluru, Karnataka 560038",
        "Contact Person: Priya Sharma",
        "Phone: +91 80 4567 8901",
        "Email: contracts@quickfixfacility.in",
        "",
        "CLIENT:",
        "SupplyMind Technologies Pvt. Ltd.",
        "12th Floor, Tower B, Cyber Park",
        "Whitefield, Bengaluru 560066",
        "",
        "SCOPE OF SERVICES:",
        "1. HVAC System - Quarterly servicing & breakdown support",
        "2. Electrical Systems - Monthly inspection & repair",
        "3. Plumbing - On-call maintenance & annual overhaul",
        "4. Fire Safety - Bi-annual audit & equipment check",
        "5. General Housekeeping Equipment - Monthly maintenance",
        "",
        "CONTRACT VALUE:",
        "-------------------------------------------------------------",
        "Sl.  Service                    Frequency    Annual Cost",
        "-------------------------------------------------------------",
        "1    HVAC Maintenance           Quarterly     1,80,000",
        "2    Electrical Maintenance     Monthly       2,40,000",
        "3    Plumbing Services          On-call       1,20,000",
        "4    Fire Safety Audit          Bi-annual       80,000",
        "5    Housekeeping Equipment     Monthly         60,000",
        "-------------------------------------------------------------",
        "                              Subtotal:       6,80,000.00",
        "                              GST (18%):      1,22,400.00",
        "                              TOTAL:          8,02,400.00",
        "-------------------------------------------------------------",
        "",
        "PAYMENT TERMS:",
        "- Quarterly payments of Rs. 2,00,600.00",
        "- Invoice raised on 1st of each quarter",
        "- Payment due within 15 days",
        "",
        "SLA COMMITMENTS:",
        "- Response time: Critical issues < 2 hours",
        "- Resolution time: Standard issues < 24 hours",
        "- Monthly service report submission",
        "- Penalty for SLA breach: 5% of quarterly value",
    ])


if __name__ == "__main__":
    print("\n📄 Generating test procurement documents...\n")
    files = [
        invoice_1(),
        invoice_2(),
        purchase_order_1(),
        vendor_contract(),
    ]
    print(f"\n✅ Created {len(files)} test documents in: {OUTPUT_DIR}")
    print("\nYou can now upload these through the SupplyMind frontend at:")
    print("  http://127.0.0.1:3000/documents\n")
