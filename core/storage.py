"""Stockage privé : les fichiers ne sont jamais exposés via une URL publique."""
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class StockagePrive(FileSystemStorage):
    """
    Dossier lu dynamiquement depuis settings.PRIVATE_MEDIA_ROOT (ce qui permet
    aussi de le surcharger dans les tests). Aucune URL publique : les fichiers
    sont servis uniquement par des vues qui contrôlent les droits.
    En production cloud, remplacer par un bucket S3 privé (django-storages).
    """

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Fichier privé : utilisez la vue de téléchargement protégée.")


stockage_prive = StockagePrive()


@deconstructible
class CheminAleatoire:
    """Renomme le fichier avec un UUID : le nom d'origine (souvent nominatif) n'est pas conservé."""

    def __init__(self, dossier):
        self.dossier = dossier

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()[:10]
        return f"{self.dossier}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, CheminAleatoire) and other.dossier == self.dossier


def chemin_aleatoire(sous_dossier):
    return CheminAleatoire(sous_dossier)
