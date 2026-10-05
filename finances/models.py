"""
Frais de scolarité et paiements.

Les montants sont en francs CFA (entiers, pas de centimes).
Un paiement en ligne passe par un « fournisseur » (Mobile Money, carte) :
voir `fournisseurs.py`. Seuls les paiements CONFIRMÉS comptent dans le solde.
"""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.fields import EncryptedTextField


class FraisScolarite(models.Model):
    class Categorie(models.TextChoices):
        SCOLARITE = "SCOLARITE", "Scolarité"
        CANTINE = "CANTINE", "Cantine"
        TRANSPORT = "TRANSPORT", "Transport"
        AUTRE = "AUTRE", "Autre"

    eleve = models.ForeignKey("accounts.Eleve", on_delete=models.CASCADE, related_name="frais")
    annee = models.ForeignKey("scolarite.AnneeScolaire", on_delete=models.PROTECT, related_name="frais")
    libelle = models.CharField("libellé", max_length=120, help_text="Ex. 3e tranche de scolarité")
    categorie = models.CharField(max_length=10, choices=Categorie.choices, default=Categorie.SCOLARITE)
    montant = models.PositiveIntegerField(help_text="En FCFA")
    echeance = models.DateField("échéance")

    class Meta:
        verbose_name = "frais de scolarité"
        verbose_name_plural = "frais de scolarité"
        ordering = ["echeance"]

    def __str__(self):
        return f"{self.eleve} — {self.libelle} ({self.montant} FCFA)"

    @property
    def paye(self) -> int:
        return self.paiements.filter(statut=Paiement.Statut.CONFIRME).aggregate(t=Sum("montant"))["t"] or 0

    @property
    def reste(self) -> int:
        return max(self.montant - self.paye, 0)


def _reference():
    return "NP-" + uuid.uuid4().hex[:12].upper()


class Paiement(models.Model):
    class Moyen(models.TextChoices):
        ORANGE_MONEY = "OM", "Orange Money"
        WAVE = "WAVE", "Wave"
        MTN = "MTN", "MTN MoMo"
        MOOV = "MOOV", "Moov Money"
        CARTE = "CB", "Carte bancaire"
        ESPECES = "ESPECES", "Espèces (au guichet)"

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente de validation"
        CONFIRME = "CONFIRME", "Confirmé"
        ECHOUE = "ECHOUE", "Échoué"
        ANNULE = "ANNULE", "Annulé"

    frais = models.ForeignKey(FraisScolarite, on_delete=models.PROTECT, related_name="paiements")
    payeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="paiements")
    montant = models.PositiveIntegerField()
    moyen = models.CharField(max_length=8, choices=Moyen.choices)
    telephone = EncryptedTextField(blank=True, help_text="Numéro Mobile Money (chiffré)")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True)
    reference = models.CharField(max_length=20, unique=True, default=_reference, editable=False)
    reference_operateur = models.CharField(max_length=100, blank=True)
    numero_recu = models.CharField("n° de reçu", max_length=20, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    confirme_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return f"{self.reference} — {self.montant} FCFA — {self.get_statut_display()}"
