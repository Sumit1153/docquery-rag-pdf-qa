"""Rebuild sample PDF (synthetic data only). Requires reportlab."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter

DEST = Path(__file__).resolve().parent / "team_handbook.pdf"
PAGES = [
    ("01 / Working arrangements", [
        ("Remote work policy", "Employees may work remotely three days per week. On the remaining two days, employees work onsite with their team."),
        ("Core collaboration hours", "All team members should be available for collaboration from 10:00 to 15:00 IST on working days."),
        ("New employee onboarding", "New hires complete their onboarding checklist within 14 calendar days after their starting date."),
    ]),
    ("02 / Expenses and equipment", [
        ("Travel reimbursement", "Travel reimbursement claims must be submitted within 30 days of the date of travel. Receipts are required for every claim."),
        ("Computer equipment", "Company laptops are eligible for normal replacement every four years, subject to manager approval."),
        ("Lost equipment", "If a device is lost, the employee must notify the IT support team immediately and follow the security incident checklist."),
    ]),
]

c = canvas.Canvas(str(DEST), pagesize=letter)
for page_number, (subtitle, sections) in enumerate(PAGES, start=1):
    width, height = letter
    c.setFillColor(HexColor("#f6f7f4")); c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(HexColor("#112f37")); c.rect(0, height - 132, width, 132, fill=1, stroke=0)
    c.setFillColor(HexColor("#d5efb2")); c.setFont("Helvetica-Bold", 13); c.drawString(50, height - 49, "DOCQUERY  /  SAMPLE HANDBOOK")
    c.setFillColor(HexColor("#ffffff")); c.setFont("Helvetica-Bold", 25); c.drawString(50, height - 92, subtitle)
    y = height - 185
    for label, body in sections:
        c.setFillColor(HexColor("#23483d")); c.setFont("Helvetica-Bold", 14); c.drawString(50, y, label)
        c.setFillColor(HexColor("#293b42")); c.setFont("Helvetica", 11)
        from reportlab.lib.utils import simpleSplit
        for line in simpleSplit(body, "Helvetica", 11, width - 100):
            y -= 19; c.drawString(50, y, line)
        y -= 58
    c.setStrokeColor(HexColor("#cbd8d3")); c.line(50, 80, width - 50, 80)
    c.setFont("Helvetica", 9); c.setFillColor(HexColor("#6d807e"));
    c.drawString(50, 62, "Synthetic demo only · Not an actual company policy")
    c.drawRightString(width - 50, 62, f"PAGE {page_number} / 2")
    c.showPage()
c.save()
print(DEST)
