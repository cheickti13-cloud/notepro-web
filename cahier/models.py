"""Cahier de texte numérique : contenus des séances et devoirs."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.storage import chemin_aleatoire, stockage_prive


class ContenuSeance(models.Model):
    """Ce qui a été fait en cours."""

    enseignement = models.ForeignKey("scolarite.Enseignement", on_delete=models.CASCADE, related_name="contenus")
    date = models.DateField(db_index=True)
    titre = models.CharField(max_length=150)
    contenu = models.TextField(max_length=10000)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "contenu de séance"
        verbose_name_plural = "contenus de séance"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.enseignement} — {self.date:%d/%m/%Y} — {self.titre}"


class Devoir(models.Model):
    """Travail à faire pour une date donnée."""

    enseignement = models.ForeignKey("scolarite.Enseignement", on_delete=models.CASCADE, related_name="devoirs")
    donne_le = models.DateField("donné le")
    pour_le = models.DateField("à rendre pour le", db_index=True)
    titre = models.CharField(max_length=150)
    description = models.TextField(max_length=5000, blank=True)
    duree_estimee = models.PositiveSmallIntegerField("durée estimée (min)", null=True, blank=True)
    piece_jointe = models.FileField(
        upload_to=chemin_aleatoire("devoirs"), storage=stockage_prive, blank=True,
        help_text="Énoncé ou document (PDF, image).",
    )
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cree_le = models.DateTimeField(auto_now_add=True)
    faits_par = models.ManyToManyField("accounts.Eleve", through="DevoirFait", related_name="devoirs_faits", blank=True)

    class Meta:
        ordering = ["pour_le", "enseignement__matiere__nom"]

    def __str__(self):
        return f"{self.enseignement.matiere} — pour le {self.pour_le:%d/%m/%Y} — {self.titre}"

    def clean(self):
        if self.donne_le and self.pour_le and self.pour_le < self.donne_le:
            raise ValidationError({"pour_le": "L'échéance ne peut pas précéder la date où le devoir est donné."})


class DevoirFait(models.Model):
    """Suivi personnel d'un devoir par l'élève (« en cours » ou « terminé »)."""

    class Statut(models.TextChoices):
        EN_COURS = "EN_COURS", "En cours"
        TERMINE = "TERMINE", "Terminé"

    devoir = models.ForeignKey(Devoir, on_delete=models.CASCADE)
    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.TERMINE)
    fait_le = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["devoir", "eleve"], name="devoir_fait_unique")]
