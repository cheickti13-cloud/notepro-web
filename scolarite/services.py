"""Fonctions utilitaires sur l'année et les périodes."""
from django.utils import timezone

from .models import AnneeScolaire, Periode


def annee_active():
    return AnneeScolaire.objects.filter(active=True).first()


def periodes_actives():
    annee = annee_active()
    return Periode.objects.filter(annee=annee) if annee else Periode.objects.none()


def periode_courante(date=None):
    """Période contenant la date (aujourd'hui par défaut), sinon la dernière commencée."""
    date = date or timezone.localdate()
    periodes = periodes_actives()
    p = periodes.filter(debut__lte=date, fin__gte=date).first()
    return p or periodes.filter(debut__lte=date).order_by("-ordre").first() or periodes.first()


def periode_depuis_requete(request):
    """Période choisie via ?periode=<id>, sinon la période courante."""
    pid = request.GET.get("periode")
    if pid and pid.isdigit():
        p = periodes_actives().filter(pk=int(pid)).first()
        if p:
            return p
    return periode_courante()
