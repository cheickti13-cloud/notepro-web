"""Carnet de notes : évaluations et notes des élèves."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from . import calculs


class Evaluation(models.Model):
    enseignement = models.ForeignKey(
        "scolarite.Enseignement", on_delete=models.CASCADE, related_name="evaluations"
    )
    periode = models.ForeignKey("scolarite.Periode", on_delete=models.PROTECT, related_name="evaluations")
    titre = models.CharField(max_length=120)
    date = models.DateField()
    bareme = models.DecimalField(
        "barème", max_digits=5, decimal_places=2, default=Decimal("20"),
        validators=[MinValueValidator(Decimal("1"))], help_text="Note maximale (ex. 20, 10, 40).",
    )
    coefficient = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("1"), validators=[MinValueValidator(Decimal("0"))]
    )
    publiee = models.BooleanField(
        "visible par les élèves et parents", default=True,
        help_text="Décochez pour saisir les notes sans les rendre visibles tout de suite.",
    )
    creee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    creee_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "évaluation"
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.titre} ({self.enseignement}, {self.date:%d/%m/%Y})"

    def clean(self):
        if self.periode_id and self.date and not (self.periode.debut <= self.date <= self.periode.fin):
            raise ValidationError({"date": "La date doit être comprise dans la période choisie."})
        if self.periode_id and self.enseignement_id and self.periode.annee_id != self.enseignement.classe.annee_id:
            raise ValidationError({"periode": "La période n'appartient pas à l'année de la classe."})


class Note(models.Model):
    class Statut(models.TextChoices):
        NOTEE = calculs.NOTEE, "Notée"
        ABSENT = calculs.ABSENT, "Absent (non comptée)"
        DISPENSE = calculs.DISPENSE, "Dispensé (non comptée)"
        NON_RENDU = calculs.NON_RENDU, "Non rendu (compte 0)"

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="notes")
    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE, related_name="notes")
    valeur = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))]
    )
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.NOTEE)
    commentaire = models.CharField(max_length=200, blank=True)
    modifiee_le = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "eleve"], name="une_note_par_eleve_et_evaluation")
        ]

    def __str__(self):
        return f"{self.eleve} : {self.affichage}"

    @property
    def affichage(self):
        if self.statut != self.Statut.NOTEE:
            return {"ABSENT": "Abs", "DISPENSE": "Disp", "NON_RENDU": "N.R."}[self.statut]
        return "—" if self.valeur is None else f"{self.valeur.normalize():f}".replace(".", ",")

    @property
    def sur_20(self):
        if self.statut == self.Statut.NOTEE and self.valeur is not None:
            return calculs.arrondir(calculs.sur_20(self.valeur, self.evaluation.bareme))
        return None

    def clean(self):
        if self.valeur is not None and self.evaluation_id and self.valeur > self.evaluation.bareme:
            raise ValidationError({"valeur": f"La note ne peut pas dépasser le barème ({self.evaluation.bareme})."})
        if self.statut == self.Statut.NOTEE and self.valeur is None:
            raise ValidationError({"valeur": "Saisissez une note ou choisissez un statut."})
        if self.eleve_id and self.evaluation_id and self.eleve.classe_id != self.evaluation.enseignement.classe_id:
            raise ValidationError("Cet élève n'appartient pas à la classe de l'évaluation.")
