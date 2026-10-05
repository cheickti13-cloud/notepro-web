"""Reçu de paiement au format PDF (ReportLab)."""
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def fcfa(n):
    return f"{n:,}".replace(",", " ") + " FCFA"


def recu_pdf(paiement) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    w, h = A5
    c.setFillColorRGB(0.043, 0.122, 0.227)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(14 * mm, h - 15 * mm, settings.ETABLISSEMENT_NOM)
    c.setFont("Helvetica", 10)
    c.drawString(14 * mm, h - 22 * mm, f"Reçu de paiement n° {paiement.numero_recu}")
    c.setFillColorRGB(0, 0, 0)
    y = h - 42 * mm
    lignes = [
        ("Élève", str(paiement.frais.eleve)),
        ("Objet", paiement.frais.libelle),
        ("Montant", fcfa(paiement.montant)),
        ("Moyen", paiement.get_moyen_display()),
        ("Date", paiement.confirme_le.strftime("%d/%m/%Y %H:%M") if paiement.confirme_le else "—"),
        ("Référence", paiement.reference),
        ("Payé par", str(paiement.payeur or "—")),
    ]
    for lib, val in lignes:
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.32, 0.38, 0.49)
        c.drawString(14 * mm, y, lib)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50 * mm, y, val[:60])
        y -= 9 * mm
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.32, 0.38, 0.49)
    c.drawString(14 * mm, 14 * mm, "Document généré par NotePro — à conserver.")
    c.showPage()
    c.save()
    return buf.getvalue()
