"""Bulletins : appréciations par matière, appréciation générale et publication."""
from django.conf import settings
from django.db import models


class Appreciation(models.Model):
    """Appréciation de l'enseignant d'une matière pour un élève sur une période."""

    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE, related_name="appreciations")
    enseignement = models.ForeignKey("scolarite.Enseignement", on_delete=models.CASCADE, related_name="appreciations")
    periode = models.ForeignKey("scolarite.Periode", on_delete=models.CASCADE, related_name="appreciations")
    texte = models.TextField(max_length=600)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    modifiee_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "appréciation"
        constraints = [
            models.UniqueConstraint(fields=["eleve", "enseignement", "periode"], name="appreciation_unique")
        ]

    def __str__(self):
        return f"{self.eleve} — {self.enseignement.matiere} — {self.periode.nom}"


class AppreciationGenerale(models.Model):
    """Appréciation du conseil de classe (professeur principal / direction)."""

    class Mention(models.TextChoices):
        AUCUNE = "", "—"
        FELICITATIONS = "FELICITATIONS", "Félicitations"
        COMPLIMENTS = "COMPLIMENTS", "Compliments"
        ENCOURAGEMENTS = "ENCOURAGEMENTS", "Encouragements"
        AVERT_TRAVAIL = "AVERT_TRAVAIL", "Avertissement travail"
        AVERT_CONDUITE = "AVERT_CONDUITE", "Avertissement conduite"

    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE, related_name="appreciations_generales")
    periode = models.ForeignKey("scolarite.Periode", on_delete=models.CASCADE, related_name="appreciations_generales")
    texte = models.TextField(max_length=1000, blank=True)
    mention = models.CharField(max_length=15, choices=Mention.choices, blank=True, default="")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    modifiee_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "appréciation générale"
        verbose_name_plural = "appréciations générales"
        constraints = [models.UniqueConstraint(fields=["eleve", "periode"], name="appreciation_generale_unique")]


class PublicationBulletin(models.Model):
    """Tant qu'un bulletin n'est pas publié, élèves et parents ne peuvent pas le consulter."""

    classe = models.ForeignKey("scolarite.Classe", on_delete=models.CASCADE, related_name="publications")
    periode = models.ForeignKey("scolarite.Periode", on_delete=models.CASCADE, related_name="publications")
    publie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    publie_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "publication de bulletins"
        verbose_name_plural = "publications de bulletins"
        constraints = [models.UniqueConstraint(fields=["classe", "periode"], name="publication_unique")]

    def __str__(self):
        return f"Bulletins {self.classe} — {self.periode.nom}"
