"""Connexion par numéro de téléphone (en plus de l'identifiant)."""
import re

from django.contrib.auth.backends import ModelBackend

from .models import User


class TelephoneBackend(ModelBackend):
    """Si l'identifiant saisi ressemble à un numéro, on cherche le compte par empreinte du téléphone."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        if not re.fullmatch(r"[\d\s+().-]{8,20}", username) or len(re.sub(r"\D", "", username)) < 8:
            return None
        empreinte = User.empreinte_telephone(username)
        comptes = list(User.objects.filter(telephone_empreinte=empreinte, is_active=True)[:2])
        if len(comptes) != 1:  # inconnu ou numéro partagé par plusieurs comptes : on refuse
            User().set_password(password)  # temps constant (évite de deviner l'existence du compte)
            return None
        user = comptes[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
