"""
Fournisseurs de paiement (Mobile Money, carte).

Architecture : chaque fournisseur implémente `initier`, `verifier` et
`traiter_webhook`. Le choix se fait par `settings.PAIEMENT_FOURNISSEUR`.

- "sandbox" (par défaut) : simulation pour le développement et les démos ;
  le paiement est confirmé à la première vérification. AUCUN argent réel.
- Production : brancher un agrégateur agréé dans votre pays (ex. CinetPay,
  PayDunya, Wave Business, API Orange Money Web Payment...) en créant une
  sous-classe ici. Toujours confirmer via le webhook signé du fournisseur,
  jamais sur la seule parole de l'application mobile.
"""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Paiement


class FournisseurPaiement:
    nom = "abstrait"

    def initier(self, paiement: Paiement) -> dict:
        """Démarre le paiement. Retourne des instructions à afficher à l'utilisateur."""
        raise NotImplementedError

    def verifier(self, paiement: Paiement) -> str:
        """Interroge le fournisseur et retourne le statut à jour."""
        raise NotImplementedError

    def traiter_webhook(self, request):
        """Valide la signature du rappel serveur et met à jour le paiement."""
        raise NotImplementedError


class SandboxFournisseur(FournisseurPaiement):
    nom = "sandbox"

    def initier(self, paiement):
        paiement.reference_operateur = "SBX-" + paiement.reference
        paiement.save(update_fields=["reference_operateur"])
        if paiement.moyen == Paiement.Moyen.CARTE:
            return {"type": "redirection", "message": "Vous allez être redirigé vers la page sécurisée 3-D Secure (simulation)."}
        return {
            "type": "validation_telephone",
            "message": f"Une demande de {paiement.montant} FCFA a été envoyée sur votre compte "
                       f"{paiement.get_moyen_display()}. Validez-la avec votre code secret (simulation).",
        }

    def verifier(self, paiement):
        if paiement.statut == Paiement.Statut.EN_ATTENTE:
            confirmer(paiement)
        return paiement.statut


def confirmer(paiement: Paiement):
    """Marque un paiement confirmé, attribue un n° de reçu et notifie le payeur."""
    with transaction.atomic():
        p = Paiement.objects.select_for_update().get(pk=paiement.pk)
        if p.statut == Paiement.Statut.CONFIRME:
            return p
        p.statut = Paiement.Statut.CONFIRME
        p.confirme_le = timezone.now()
        annee = p.confirme_le.year
        n = Paiement.objects.filter(statut=Paiement.Statut.CONFIRME, confirme_le__year=annee).count() + 1
        p.numero_recu = f"{annee}-{n:04d}"
        p.save(update_fields=["statut", "confirme_le", "numero_recu"])
    paiement.refresh_from_db()
    if p.payeur_id:
        from messagerie.models import Notification
        from messagerie.services import notifier

        notifier([p.payeur], Notification.Type.ANNONCE, f"Paiement de {p.montant} FCFA confirmé (reçu n°{p.numero_recu})", lien="/frais")
    return p


FOURNISSEURS = {"sandbox": SandboxFournisseur}


def fournisseur():
    nom = getattr(settings, "PAIEMENT_FOURNISSEUR", "sandbox")
    return FOURNISSEURS[nom]()
