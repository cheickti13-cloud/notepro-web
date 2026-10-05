from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm


class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion avec messages d'erreur volontairement génériques
    (on ne révèle pas si l'identifiant existe)."""

    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Identifiant ou mot de passe incorrect.",
    }


class ChangementMdpForm(PasswordChangeForm):
    pass


class PreferencesForm(forms.Form):
    notifications_email = forms.BooleanField(
        required=False, label="Recevoir aussi les notifications par e-mail"
    )
