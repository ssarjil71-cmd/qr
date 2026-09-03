# QR-NexID Student Brochure

This folder contains the editable QR-NexID Student one-page flyer generator and the generated print-ready PDF.

## Generate

From the project root:

```powershell
python brochure\generate_brochure.py
```

The generator reads the existing logo and hero artwork from `static/img/` without modifying them. It creates safe demo visuals and does not load application data or screenshots.

## Output

- `QR-NexID_Student_Flyer.pdf` - single-page A4 promotional flyer for digital sharing and print/PDF export.
- `generate_brochure.py` - editable source for the flyer copy, layout, colors, and design.

The contact details on the final page are intentional placeholders for the organization's approved website, phone, email, and address.
