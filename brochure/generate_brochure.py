from pathlib import Path

import qrcode
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
PDF_PATH = OUT_DIR / "QR-NexID_Student_Flyer.pdf"
LOGO_PATH = ROOT / "static" / "img" / "qr-nexid-logo.png"
HERO_PATH = ROOT / "static" / "img" / "qr-nexid-hero-art.png"
PAGE_W, PAGE_H = A4
MARGIN = 16 * mm

NAVY = HexColor("#080D2F")
INK = HexColor("#0F172A")
BLUE = HexColor("#2563EB")
INDIGO = HexColor("#4F46E5")
VIOLET = HexColor("#7C3AED")
SLATE = HexColor("#475569")
MUTED = HexColor("#64748B")
LINE = HexColor("#DCE8FA")
PALE = HexColor("#F7FAFF")
PALE_BLUE = HexColor("#EEF4FF")
PALE_VIOLET = HexColor("#F4F1FF")
TEAL = HexColor("#0891B2")
GREEN = HexColor("#059669")

FONT_DIR = Path("C:/Windows/Fonts")
if (FONT_DIR / "segoeui.ttf").exists():
    pdfmetrics.registerFont(TTFont("BrandSans", str(FONT_DIR / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("BrandSans-Bold", str(FONT_DIR / "segoeuib.ttf")))
    REG, BOLD = "BrandSans", "BrandSans-Bold"
else:
    REG, BOLD = "Helvetica", "Helvetica-Bold"


def text(c, x, y, value, size=10, color=INK, font=REG):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, value)


def centered(c, x, y, value, size=10, color=INK, font=REG):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawCentredString(x, y, value)


def wrap(value, width):
    words = value.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def paragraph(c, x, y, value, width, size=9, leading=12, color=SLATE):
    for row in wrap(value, width):
        text(c, x, y, row, size, color)
        y -= leading
    return y


def box(c, x, y, w, h, fill=white, stroke=LINE, radius=9, width=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(width)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def draw_logo(c, x, y, width):
    img = ImageReader(str(LOGO_PATH))
    iw, ih = img.getSize()
    c.drawImage(img, x, y, width=width, height=width * ih / iw, preserveAspectRatio=True, mask="auto")


def draw_hero_art(c, x, y, w, h):
    img = ImageReader(str(HERO_PATH))
    iw, ih = img.getSize()
    scale = max(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(x, y, w, h, fill=1, stroke=0)
    clip = c.beginPath()
    clip.rect(x, y, w, h)
    c.clipPath(clip, stroke=0, fill=0)
    c.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, width=dw, height=dh, mask="auto")
    c.setFillColor(Color(0.03, 0.05, 0.18, alpha=0.3))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.restoreState()


def draw_qr(c, x, y, size):
    qr = qrcode.QRCode(version=3, box_size=5, border=1)
    qr.add_data("QR-NexID student demo profile")
    qr.make(fit=True)
    path = OUT_DIR / "_demo_qr.png"
    qr.make_image(fill_color="#0F172A", back_color="white").save(path)
    box(c, x - 6, y - 6, size + 12, size + 24, white, LINE, 8)
    c.drawImage(str(path), x, y + 12, width=size, height=size, preserveAspectRatio=True, mask="auto")
    centered(c, x + size / 2, y + 1, "DEMO QR", 7.5, MUTED, BOLD)


def feature_card(c, x, y, w, h, label, title, color, detail):
    box(c, x, y, w, h, white, LINE, 9)
    c.setFillColor(color)
    c.circle(x + 13 * mm, y + h - 13 * mm, 7 * mm, fill=1, stroke=0)
    centered(c, x + 13 * mm, y + h - 15.5 * mm, label, 7.5, white, BOLD)
    text(c, x + 25 * mm, y + h - 11 * mm, title, 9.3, INK, BOLD)
    paragraph(c, x + 25 * mm, y + h - 19 * mm, detail, 24, 7.1, 8, MUTED)


def step(c, x, y, number, title):
    c.setFillColor(BLUE if number != "02" else INDIGO)
    c.circle(x, y, 7 * mm, fill=1, stroke=0)
    centered(c, x, y - 2.5 * mm, number, 8.5, white, BOLD)
    centered(c, x, y - 14 * mm, title, 8.4, INK, BOLD)


def build():
    OUT_DIR.mkdir(exist_ok=True)
    c = canvas.Canvas(str(PDF_PATH), pagesize=A4)
    c.setTitle("QR-NexID Student Flyer")
    c.setAuthor("QR-NexID")

    # Light page with a compact dark hero band.
    c.setFillColor(PALE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    hero_h = 77 * mm
    draw_hero_art(c, 0, PAGE_H - hero_h, PAGE_W, hero_h)
    draw_logo(c, MARGIN, PAGE_H - 29 * mm, 54 * mm)
    text(c, MARGIN, PAGE_H - 49 * mm, "YOUR DIGITAL IDENTITY.", 20, white, BOLD)
    text(c, MARGIN, PAGE_H - 61 * mm, "ONE QR.", 28, white, BOLD)
    text(c, PAGE_W - MARGIN - 34 * mm, PAGE_H - 20 * mm, "STUDENT", 8, HexColor("#BFDBFE"), BOLD)
    text(c, PAGE_W - MARGIN - 45 * mm, PAGE_H - 29 * mm, "SCAN ME, KNOW ME", 8, white, BOLD)

    # Intro and primary QR visual.
    intro_y = PAGE_H - hero_h - 13 * mm
    text(c, MARGIN, intro_y, "A student profile that keeps up with you.", 13.5, BLUE, BOLD)
    paragraph(c, MARGIN, intro_y - 9 * mm, "QR-NexID brings your personal, academic, project, certificate, resume, and emergency information together in one profile you can access through a QR identity.", 57, 9.2, 12, SLATE)
    draw_qr(c, PAGE_W - MARGIN - 35 * mm, intro_y - 25 * mm, 27 * mm)

    # Feature grid: only features confirmed in the student UI/model.
    section_y = 163 * mm
    text(c, MARGIN, section_y + 3 * mm, "WHAT YOU CAN CARRY", 8, INDIGO, BOLD)
    text(c, MARGIN, section_y - 7 * mm, "Your essentials, connected.", 16, INK, BOLD)
    card_w, card_h = 84 * mm, 19 * mm
    cards = [
        ("ID", "Digital student profile", BLUE, "Personal details, photo, and address."),
        ("AC", "Academic information", INDIGO, "College, branch, year, roll number, and bio."),
        ("SK", "Skills & projects", VIOLET, "Show your skills, work, technologies, and links."),
        ("CE", "Certificates & documents", TEAL, "Keep credentials and supporting documents together."),
        ("CV", "Resume & social links", GREEN, "Headline, preferred role, summary, and profile links."),
        ("QR", "Profile QR + Emergency QR", BLUE, "Two scan experiences for identity and emergency contact information."),
    ]
    for index, item in enumerate(cards):
        x = MARGIN if index % 2 == 0 else 105 * mm
        y = section_y - 30 * mm - (index // 2) * 22 * mm
        feature_card(c, x, y, card_w, card_h, *item)

    # Three-step strip.
    strip_y = 55 * mm
    box(c, MARGIN, strip_y, PAGE_W - 2 * MARGIN, 31 * mm, PALE_BLUE, PALE_BLUE, 11)
    text(c, MARGIN + 8 * mm, strip_y + 22 * mm, "HOW IT WORKS", 8, BLUE_DARK if False else BLUE, BOLD)
    step(c, MARGIN + 31 * mm, strip_y + 12 * mm, "01", "Create profile")
    step(c, PAGE_W / 2, strip_y + 12 * mm, "02", "Get your QR")
    step(c, PAGE_W - MARGIN - 31 * mm, strip_y + 12 * mm, "03", "Share / scan")
    line_x = [MARGIN + 40 * mm, PAGE_W / 2 - 10 * mm, PAGE_W / 2 + 10 * mm]
    for x1, x2 in zip(line_x[::2], line_x[1::2]):
        c.setStrokeColor(HexColor("#A9C7F7"))
        c.setLineWidth(1.2)
        c.line(x1, strip_y + 12 * mm, x2, strip_y + 12 * mm)

    # Bottom benefits and CTA.
    bottom_y = 20 * mm
    text(c, MARGIN, bottom_y + 26 * mm, "WHY QR-NEXID", 8, INDIGO, BOLD)
    benefits = ["One digital identity", "Easy information sharing", "Professional student presence", "Quick QR-based access"]
    for index, benefit in enumerate(benefits):
        x = MARGIN + (index % 2) * 51 * mm
        y = bottom_y + 16 * mm - (index // 2) * 8 * mm
        c.setFillColor(BLUE)
        c.circle(x + 2, y + 2, 2, fill=1, stroke=0)
        text(c, x + 7, y, benefit, 8, SLATE, BOLD)
    c.setFillColor(NAVY)
    c.roundRect(112 * mm, bottom_y - 1 * mm, 74 * mm, 31 * mm, 10, fill=1, stroke=0)
    text(c, 119 * mm, bottom_y + 20 * mm, "QR-NexID", 13, white, BOLD)
    text(c, 119 * mm, bottom_y + 11 * mm, "Scan Me, Know Me", 9, HexColor("#BFDBFE"), BOLD)
    text(c, 119 * mm, bottom_y + 3 * mm, "Website  |  Email  |  Contact", 7.2, HexColor("#CBD5E1"), REG)
    c.setStrokeColor(HexColor("#334155"))
    c.setLineWidth(0.7)
    c.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
    text(c, MARGIN, 7 * mm, "[your website]   [your email]   [your contact]", 7, MUTED, REG)
    text(c, PAGE_W - MARGIN - 33 * mm, 7 * mm, "STUDENT EDITION", 7, MUTED, BOLD)
    c.showPage()
    c.save()
    demo = OUT_DIR / "_demo_qr.png"
    if demo.exists():
        demo.unlink()
    print(PDF_PATH)


if __name__ == "__main__":
    build()
