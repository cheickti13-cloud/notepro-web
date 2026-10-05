"""
Emploi du temps.

- `Creneau` : cours hebdomadaire récurrent (ex. Maths 3e A, lundi 8h-9h, salle B12).
- `ModificationCours` : exception ponctuelle à une date donnée (annulation,
  changement de salle, remplacement d'enseignant).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Creneau(models.Model):
    class Jour(models.IntegerChoices):
        LUNDI = 0, "Lundi"
        MARDI = 1, "Mardi"
        MERCREDI = 2, "Mercredi"
        JEUDI = 3, "Jeudi"
        VENDREDI = 4, "Vendredi"
        SAMEDI = 5, "Samedi"

    enseignement = models.ForeignKey(
        "scolarite.Enseignement", on_delete=models.CASCADE, related_name="creneaux"
    )
    jour = models.PositiveSmallIntegerField(choices=Jour.choices)
    heure_debut = models.TimeField("début")
    heure_fin = models.TimeField("fin")
    salle = models.ForeignKey(
        "scolarite.Salle", on_delete=models.SET_NULL, null=True, blank=True, related_name="creneaux"
    )

    class Meta:
        verbose_name = "créneau"
        ordering = ["jour", "heure_debut"]
        indexes = [models.Index(fields=["jour", "heure_debut"])]

    def __str__(self):
        return f"{self.enseignement} — {self.get_jour_display()} {self.heure_debut:%H:%M}-{self.heure_fin:%H:%M}"

    def clean(self):
        if self.heure_debut and self.heure_fin and self.heure_fin <= self.heure_debut:
            raise ValidationError("L'heure de fin doit être après l'heure de début.")
        if not (self.enseignement_id and self.heure_debut and self.heure_fin and self.jour is not None):
            return
        # Détection des conflits : même jour, horaires qui se chevauchent
        ens = self.enseignement
        chevauchement = Creneau.objects.filter(
            enseignement__classe__annee=ens.classe.annee,  # seulement l'année concernée
            jour=self.jour,
            heure_debut__lt=self.heure_fin,
            heure_fin__gt=self.heure_debut,
        ).exclude(pk=self.pk)
        conflits = []
        if chevauchement.filter(enseignement__classe=ens.classe).exists():
            conflits.append(f"la classe {ens.classe} a déjà cours")
        if chevauchement.filter(enseignement__enseignant=ens.enseignant).exists():
            conflits.append(f"{ens.enseignant} enseigne déjà")
        if self.salle_id and chevauchement.filter(salle=self.salle).exists():
            conflits.append(f"la salle {self.salle} est déjà occupée")
        if conflits:
            raise ValidationError("Conflit d'emploi du temps : " + " ; ".join(conflits) + ".")


class ModificationCours(models.Model):
    class Type(models.TextChoices):
        ANNULATION = "ANNULATION", "Cours annulé"
        CHANGEMENT_SALLE = "SALLE", "Changement de salle"
        REMPLACEMENT = "REMPLACEMENT", "Remplacement d'enseignant"

    creneau = models.ForeignKey(Creneau, on_delete=models.CASCADE, related_name="modifications")
    date = models.DateField()
    type = models.CharField(max_length=12, choices=Type.choices)
    nouvelle_salle = models.ForeignKey(
        "scolarite.Salle", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    remplacant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remplacements",
        limit_choices_to={"role": "ENSEIGNANT"},
    )
    motif = models.CharField(max_length=200, blank=True, help_text="Visible par les élèves et parents.")
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "modification de cours"
        verbose_name_plural = "modifications de cours"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["creneau", "date"], name="une_modif_par_cours_et_date")
        ]

    def __str__(self):
        return f"{self.get_type_display()} — {self.creneau} le {self.date:%d/%m/%Y}"

    def clean(self):
        if self.creneau_id and self.date and self.date.weekday() != self.creneau.jour:
            raise ValidationError("La date ne correspond pas au jour du créneau.")
        if self.type == self.Type.CHANGEMENT_SALLE and not self.nouvelle_salle_id:
            raise ValidationError("Indiquez la nouvelle salle.")
        if self.type == self.Type.REMPLACEMENT and not self.remplacant_id:
            raise ValidationError("Indiquez l'enseignant remplaçant.")
        if self.type == self.Type.CHANGEMENT_SALLE and self.nouvelle_salle_id and self.creneau_id:
            occupants = Creneau.objects.filter(
                jour=self.creneau.jour,
                salle=self.nouvelle_salle,
                heure_debut__lt=self.creneau.heure_fin,
                heure_fin__gt=self.creneau.heure_debut,
            ).exclude(pk=self.creneau_id)
            # Un cours annulé ou déplacé ailleurs ce jour-là libère la salle
            liberes = ModificationCours.objects.filter(
                creneau__in=occupants,
                date=self.date,
                type__in=[self.Type.ANNULATION, self.Type.CHANGEMENT_SALLE],
            ).values_list("creneau_id", flat=True)
            # Un autre cours déplacé dans cette salle ce jour-là l'occupe aussi
            deplaces_ici = (
                ModificationCours.objects.filter(
                    date=self.date,
                    type=self.Type.CHANGEMENT_SALLE,
                    nouvelle_salle=self.nouvelle_salle,
                    creneau__heure_debut__lt=self.creneau.heure_fin,
                    creneau__heure_fin__gt=self.creneau.heure_debut,
                )
                .exclude(pk=self.pk)
                .exclude(creneau_id=self.creneau_id)
            )
            if occupants.exclude(pk__in=liberes).exists() or deplaces_ici.exists():
                raise ValidationError("La nouvelle salle est déjà occupée sur ce créneau.")
