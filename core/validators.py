"""Validation des fichiers déposés (justificatifs)."""
from django.conf import settings
from django.core.exceptions import ValidationError

# Signature binaire (« magic bytes ») des formats autorisés : on ne se fie pas
# à l'extension seule, qui peut être falsifiée.
SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}


def valider_justificatif(fichier):
    nom = (fichier.name or "").lower()
    ext = "." + nom.rsplit(".", 1)[-1] if "." in nom else ""
    if ext not in SIGNATURES:
        raise ValidationError("Format non autorisé. Formats acceptés : PDF, PNG, JPG.")
    if fichier.size > settings.JUSTIFICATIF_MAX_OCTETS:
        raise ValidationError("Fichier trop volumineux (5 Mo maximum).")
    debut = fichier.read(8)
    fichier.seek(0)
    if not any(debut.startswith(sig) for sig in SIGNATURES[ext]):
        raise ValidationError("Le contenu du fichier ne correspond pas à son extension.")
