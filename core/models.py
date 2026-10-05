"""Journal d'accès aux données sensibles (traçabilité RGPD)."""
from django.conf import settings
from django.db import models


class JournalAcces(models.Model):
    class Action(models.TextChoices):
        CONSULTATION = "CONSULTATION", "Consultation"
        TELECHARGEMENT = "TELECHARGEMENT", "Téléchargement"
        EXPORT = "EXPORT", "Export de données"
        MODIFICATION = "MODIFICATION", "Modification"
        SUPPRESSION = "SUPPRESSION", "Suppression / anonymisation"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    action = models.CharField(max_length=15, choices=Action.choices)
    objet = models.CharField(max_length=200, help_text="Ressource concernée")
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "entrée du journal d'accès"
        verbose_name_plural = "journal d'accès"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} {self.utilisateur} {self.action} {self.objet}"
