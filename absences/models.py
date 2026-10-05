"""
Absences et retards.

- `Appel` : trace qu'un enseignant a fait l'appel pour un cours donné (créneau + date).
- `Absence` : absence ou retard d'un élève, saisi lors de l'appel ou par la vie scolaire.
  Le parent peut le justifier (motif + document) ; l'administration valide ou refuse.

RGPD : le motif (souvent médical ou familial) est chiffré ; le justificatif est
stocké hors de l'espace web public, renommé aléatoirement, et purgé après la
durée de conservation.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.fields import EncryptedTextField
from core.storage import chemin_aleatoire, stockage_prive
from core.validators import valider_justificatif


class Appel(models.Model):
    creneau = models.ForeignKey("edt.Creneau", on_delete=models.CASCADE, related_name="appels")
    date = models.DateField()
    fait_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    fait_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["creneau", "date"], name="un_appel_par_cours")]

    def __str__(self):
        return f"Appel {self.creneau} le {self.date:%d/%m/%Y}"


class Absence(models.Model):
    class Type(models.TextChoices):
        ABSENCE = "ABSENCE", "Absence"
        RETARD = "RETARD", "Retard"

    class Statut(models.TextChoices):
        NON_JUSTIFIEE = "NON_JUSTIFIEE", "Non justifiée"
        EN_ATTENTE = "EN_ATTENTE", "Justificatif en attente de validation"
        JUSTIFIEE = "JUSTIFIEE", "Justifiée"
        REFUSEE = "REFUSEE", "Justification refusée"

    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE, related_name="absences")
    date = models.DateField(db_index=True)
    creneau = models.ForeignKey(
        "edt.Creneau", on_delete=models.SET_NULL, null=True, blank=True, related_name="absences",
        help_text="Laisser vide pour une absence à la journée.",
    )
    type = models.CharField(max_length=8, choices=Type.choices, default=Type.ABSENCE)
    minutes_retard = models.PositiveSmallIntegerField(null=True, blank=True)
    statut = models.CharField(max_length=14, choices=Statut.choices, default=Statut.NON_JUSTIFIEE, db_index=True)

    saisie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    saisie_le = models.DateTimeField(auto_now_add=True)

    # Justification par la famille
    motif = EncryptedTextField(blank=True, help_text="Donnée chiffrée.")
    justificatif = models.FileField(
        upload_to=chemin_aleatoire("justificatifs"),
        storage=stockage_prive,
        blank=True,
        validators=[valider_justificatif],
    )
    justifiee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    justifiee_le = models.DateTimeField(null=True, blank=True)

    # Traitement par l'administration
    traitee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    commentaire_admin = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "creneau__heure_debut"]
        constraints = [
            models.UniqueConstraint(
                fields=["eleve", "date", "creneau"], name="une_absence_par_eleve_et_cours",
                condition=models.Q(creneau__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["eleve", "date"], name="une_absence_journee_par_eleve",
                condition=models.Q(creneau__isnull=True),
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} — {self.eleve} — {self.date:%d/%m/%Y}"

    @property
    def libelle_creneau(self):
        if self.creneau_id:
            c = self.creneau
            return f"{c.heure_debut:%H:%M}-{c.heure_fin:%H:%M} {c.enseignement.matiere}"
        return "Journée"

    @property
    def est_justifiable(self):
        return self.statut in {self.Statut.NON_JUSTIFIEE, self.Statut.REFUSEE}

    def clean(self):
        if self.type == self.Type.RETARD and not self.minutes_retard:
            raise ValidationError({"minutes_retard": "Indiquez la durée du retard."})
        if self.type == self.Type.ABSENCE:
            self.minutes_retard = None
        if self.creneau_id and self.date and self.date.weekday() != self.creneau.jour:
            raise ValidationError("La date ne correspond pas au jour du cours.")
