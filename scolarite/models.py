"""
Structure pédagogique de l'établissement : année, périodes, classes,
matières, salles et enseignements (qui enseigne quelle matière à quelle classe).
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.storage import chemin_aleatoire, stockage_prive


class AnneeScolaire(models.Model):
    libelle = models.CharField("libellé", max_length=20, unique=True, help_text="Ex. 2026-2027")
    debut = models.DateField("début")
    fin = models.DateField()
    active = models.BooleanField(default=False, help_text="Une seule année active à la fois.")

    class Meta:
        verbose_name = "année scolaire"
        verbose_name_plural = "années scolaires"
        ordering = ["-debut"]
        constraints = [
            models.UniqueConstraint(
                fields=["active"], condition=models.Q(active=True), name="une_seule_annee_active"
            )
        ]

    def __str__(self):
        return self.libelle

    def clean(self):
        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError("La fin doit être postérieure au début.")


class Periode(models.Model):
    """Trimestre ou semestre."""

    annee = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, related_name="periodes")
    nom = models.CharField(max_length=30, help_text="Ex. 1er trimestre")
    ordre = models.PositiveSmallIntegerField(default=1)
    debut = models.DateField("début")
    fin = models.DateField()

    class Meta:
        verbose_name = "période"
        ordering = ["annee", "ordre"]
        constraints = [
            models.UniqueConstraint(fields=["annee", "ordre"], name="periode_ordre_unique")
        ]

    def __str__(self):
        return f"{self.nom} ({self.annee})"

    def clean(self):
        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError("La fin doit être postérieure au début.")
        if self.annee_id and self.debut and self.fin:
            if self.debut < self.annee.debut or self.fin > self.annee.fin:
                raise ValidationError("La période doit être comprise dans l'année scolaire.")


class Matiere(models.Model):
    nom = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=10, unique=True)
    couleur = models.CharField(
        max_length=7, default="#4f6bed", help_text="Couleur d'affichage dans l'emploi du temps (#RRGGBB)."
    )

    class Meta:
        verbose_name = "matière"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Salle(models.Model):
    nom = models.CharField(max_length=30, unique=True)
    capacite = models.PositiveSmallIntegerField("capacité", null=True, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Classe(models.Model):
    annee = models.ForeignKey(AnneeScolaire, on_delete=models.PROTECT, related_name="classes")
    nom = models.CharField(max_length=20, help_text="Ex. 3e A, Tle D")
    niveau = models.CharField(max_length=20, blank=True, help_text="Ex. 3e, Terminale")
    professeur_principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes_principales",
        limit_choices_to={"role": "ENSEIGNANT"},
    )

    class Meta:
        ordering = ["niveau", "nom"]
        constraints = [models.UniqueConstraint(fields=["annee", "nom"], name="classe_nom_unique")]

    def __str__(self):
        return self.nom


class Enseignement(models.Model):
    """Une matière enseignée dans une classe par un enseignant, avec son coefficient."""

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="enseignements")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT, related_name="enseignements")
    enseignant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="enseignements",
        limit_choices_to={"role": "ENSEIGNANT"},
    )
    coefficient = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Coefficient de la matière pour la moyenne générale.",
    )

    class Meta:
        ordering = ["classe", "matiere"]
        constraints = [
            models.UniqueConstraint(fields=["classe", "matiere"], name="enseignement_unique")
        ]

    def __str__(self):
        return f"{self.matiere} — {self.classe}"

    def clean(self):
        if self.enseignant_id and self.enseignant.role != "ENSEIGNANT":
            raise ValidationError("L'enseignant doit avoir le rôle Enseignant.")


class Evenement(models.Model):
    """Événement du calendrier de l'établissement (réunion, examen, vacances...)."""

    class Type(models.TextChoices):
        REUNION = "REUNION", "Réunion"
        EXAMEN = "EXAMEN", "Examen"
        VACANCES = "VACANCES", "Vacances"
        SORTIE = "SORTIE", "Sortie"
        CULTURE = "CULTURE", "Culture et sport"
        AUTRE = "AUTRE", "Autre"

    titre = models.CharField(max_length=150)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.AUTRE)
    debut = models.DateTimeField("début")
    fin = models.DateTimeField(null=True, blank=True)
    lieu = models.CharField(max_length=150, blank=True)
    description = models.TextField(max_length=2000, blank=True)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, null=True, blank=True, help_text="Vide = tout l'établissement.")

    class Meta:
        verbose_name = "événement"
        ordering = ["debut"]

    def __str__(self):
        return self.titre


class DocumentEtablissement(models.Model):
    """Document téléchargeable (règlement, calendrier, fournitures...)."""

    titre = models.CharField(max_length=150)
    fichier = models.FileField(upload_to=chemin_aleatoire("documents"), storage=stockage_prive)
    publie_le = models.DateTimeField(auto_now_add=True)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "document de l'établissement"
        verbose_name_plural = "documents de l'établissement"
        ordering = ["-publie_le"]

    def __str__(self):
        return self.titre
