"""
Champ de modèle chiffré au repos.

Les données sensibles (téléphone, adresse, motif d'absence, etc.) sont stockées
chiffrées en base avec Fernet (AES-128-CBC + HMAC-SHA256). Même en cas de fuite
de la base de données, elles restent illisibles sans la clé.

Limite volontaire : un champ chiffré n'est ni filtrable ni triable en SQL.
On ne l'utilise donc que pour des données qu'on n'a pas besoin de rechercher.
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

PREFIXE = "enc::"  # permet de distinguer une valeur chiffrée d'une valeur en clair


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    cles = getattr(settings, "FIELD_ENCRYPTION_KEYS", None)
    if not cles:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS n'est pas défini.")
    try:
        return MultiFernet([Fernet(c.encode() if isinstance(c, str) else c) for c in cles])
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(f"Clé FIELD_ENCRYPTION_KEYS invalide : {exc}") from exc


def chiffrer(valeur: str) -> str:
    return PREFIXE + _fernet().encrypt(valeur.encode("utf-8")).decode("ascii")


def dechiffrer(valeur: str) -> str:
    if not valeur.startswith(PREFIXE):
        # Valeur historique non chiffrée : on la renvoie telle quelle
        return valeur
    try:
        return _fernet().decrypt(valeur[len(PREFIXE):].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Impossible de déchiffrer la donnée (mauvaise clé ?).") from exc


class EncryptedTextField(models.TextField):
    """TextField dont le contenu est chiffré en base et déchiffré à la lecture."""

    description = "Texte chiffré (Fernet)"

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return dechiffrer(value)

    def to_python(self, value):
        if value is None or not isinstance(value, str):
            return value
        if value.startswith(PREFIXE):
            return dechiffrer(value)
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return chiffrer(str(value))
