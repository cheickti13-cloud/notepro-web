"""
Génération PDF des bulletins avec ReportLab.

Module volontairement indépendant de Django : il prend des dictionnaires
simples (voir `services.donnees_bulletin`) et renvoie des octets PDF.
Une classe entière = un seul PDF, une page (ou plus) par élève.
"""
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BLEU = colors.HexColor("#2f5bea")
GRIS = colors.HexColor("#f0f2f7")
BORD = colors.HexColor("#c9cfdc")


def fmt(valeur, decimales=2):
    """Format français : 12,50 ; None -> « — »."""
    if valeur is None or valeur == "":
        return "—"
    if isinstance(valeur, (int, float, Decimal)):
        return f"{Decimal(valeur):.{decimales}f}".replace(".", ",")
    return str(valeur)


def _styles():
    base = getSampleStyleSheet()
    return {
        "titre": ParagraphStyle("titre", parent=base["Title"], fontSize=15, spaceAfter=2, textColor=BLEU),
        "sous": ParagraphStyle("sous", parent=base["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.grey),
        "normal": ParagraphStyle("n", parent=base["Normal"], fontSize=8.5, leading=10.5),
        "petit": ParagraphStyle("p", parent=base["Normal"], fontSize=7.5, leading=9, textColor=colors.HexColor("#555555")),
        "gras": ParagraphStyle("g", parent=base["Normal"], fontSize=8.5, leading=10.5, fontName="Helvetica-Bold"),
        "droite": ParagraphStyle("d", parent=base["Normal"], fontSize=8.5, alignment=TA_RIGHT),
        "section": ParagraphStyle("s", parent=base["Heading3"], fontSize=10, spaceBefore=6, spaceAfter=3, textColor=BLEU),
    }


def _esc(texte):
    """Échappe le texte saisi par les utilisateurs (Paragraph interprète un mini-HTML)."""
    return (str(texte or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def _page_bulletin(d, st):
    elems = []
    elems.append(Paragraph(_esc(d["etablissement"]), st["titre"]))
    elems.append(Paragraph(f"Bulletin scolaire — {_esc(d['periode'])} — Année {_esc(d['annee'])}", st["sous"]))
    elems.append(Spacer(1, 4 * mm))

    entete = Table(
        [[
            Paragraph(f"<b>Élève :</b> {_esc(d['eleve'])}", st["normal"]),
            Paragraph(f"<b>Classe :</b> {_esc(d['classe'])}", st["normal"]),
            Paragraph(f"<b>Effectif :</b> {d['effectif']}", st["normal"]),
        ], [
            Paragraph(f"<b>Professeur principal :</b> {_esc(d.get('professeur_principal') or '—')}", st["normal"]),
            Paragraph(f"<b>Date de naissance :</b> {_esc(d.get('date_naissance') or '—')}", st["normal"]),
            "",
        ]],
        colWidths=[80 * mm, 60 * mm, 40 * mm],
    )
    entete.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GRIS), ("BOX", (0, 0), (-1, -1), 0.5, BORD),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    elems.append(entete)
    elems.append(Spacer(1, 4 * mm))

    lignes = [[Paragraph(f"<b>{t}</b>", st["normal"]) for t in
               ("Matière / Enseignant", "Coef.", "Moy. élève", "Moy. classe", "Min", "Max", "Appréciation")]]
    for m in d["matieres"]:
        lignes.append([
            Paragraph(f"<b>{_esc(m['matiere'])}</b><br/><font size=7 color='#666666'>{_esc(m['enseignant'])}</font>", st["normal"]),
            fmt(m["coefficient"], 0) if m["coefficient"] == int(m["coefficient"]) else fmt(m["coefficient"]),
            Paragraph(f"<b>{fmt(m['moyenne'])}</b>", st["droite"]),
            fmt(m["moyenne_classe"]),
            fmt(m["min"]),
            fmt(m["max"]),
            Paragraph(_esc(m.get("appreciation")), st["petit"]),
        ])
    lignes.append([
        Paragraph("<b>Moyenne générale</b>", st["normal"]), "",
        Paragraph(f"<b>{fmt(d['moyenne_generale'])}</b>", st["droite"]),
        fmt(d["moyenne_generale_classe"]), fmt(d["min_general"]), fmt(d["max_general"]),
        Paragraph(f"<b>Rang : {d['rang'] or '—'} / {d['effectif']}</b>", st["normal"]),
    ])
    tableau = Table(lignes, colWidths=[42 * mm, 12 * mm, 17 * mm, 17 * mm, 12 * mm, 12 * mm, 68 * mm], repeatRows=1)
    tableau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS),
        ("BACKGROUND", (0, -1), (-1, -1), GRIS),
        ("GRID", (0, 0), (-1, -1), 0.4, BORD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (5, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems.append(tableau)

    a = d["absences"]
    elems.append(Paragraph("Vie scolaire", st["section"]))
    elems.append(Paragraph(
        f"Absences : <b>{a['absences']}</b> (dont non justifiées : {a['non_justifiees']}) · "
        f"Retards : <b>{a['retards']}</b> ({a['minutes_retard']} min)", st["normal"]))

    elems.append(Paragraph("Appréciation du conseil de classe", st["section"]))
    bloc = [Paragraph(_esc(d.get("appreciation_generale") or "—"), st["normal"])]
    if d.get("mention"):
        bloc.append(Spacer(1, 2 * mm))
        bloc.append(Paragraph(f"<b>Mention : {_esc(d['mention'])}</b>", st["normal"]))
    cadre = Table([[bloc]], colWidths=[180 * mm])
    cadre.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, BORD), ("TOPPADDING", (0, 0), (-1, -1), 6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
    elems.append(KeepTogether([cadre]))
    elems.append(Spacer(1, 6 * mm))
    elems.append(Paragraph(f"Document généré le {_esc(d['genere_le'])} — à conserver.", st["petit"]))
    return elems


def generer_pdf(bulletins: list[dict]) -> bytes:
    """Génère un PDF contenant un bulletin par élève (dictionnaires de `donnees_bulletin`)."""
    tampon = BytesIO()
    doc = SimpleDocTemplate(
        tampon, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title="Bulletin scolaire", author="NotePro",
    )
    st = _styles()
    elems = []
    for i, d in enumerate(bulletins):
        if i:
            elems.append(PageBreak())
        elems.extend(_page_bulletin(d, st))
    if not elems:
        elems.append(Paragraph("Aucun bulletin.", st["normal"]))
    doc.build(elems)
    return tampon.getvalue()
