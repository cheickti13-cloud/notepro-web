from datetime import timedelta
from itertools import groupby

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from core.permissions import R, eleve_courant, role_requis, verifier_gestion_enseignement
from messagerie.models import Notification
from messagerie.services import notifier
from scolarite.models import Classe, Enseignement
from scolarite.services import annee_active

from .forms import ContenuSeanceForm, DevoirForm
from .models import ContenuSeance, Devoir, DevoirFait


def devoirs_a_venir(classe, depuis=None, jours=None):
    depuis = depuis or timezone.localdate()
    qs = Devoir.objects.filter(enseignement__classe=classe, pour_le__gte=depuis).select_related(
        "enseignement__matiere", "enseignement__enseignant"
    )
    if jours:
        qs = qs.filter(pour_le__lte=depuis + timedelta(days=jours))
    return qs.order_by("pour_le", "enseignement__matiere__nom")


def index(request):
    u = request.user
    if u.est_enseignant:
        enseignements = Enseignement.objects.filter(enseignant=u, classe__annee=annee_active()).select_related("classe", "matiere")
        return render(request, "cahier/index_enseignant.html", {"enseignements": enseignements})
    if u.est_admin:
        return render(request, "cahier/index_admin.html", {"classes": Classe.objects.filter(annee=annee_active())})
    return vue_eleve(request)


def vue_eleve(request):
    """Élève / parent : devoirs à venir groupés par échéance + contenus récents."""
    eleve, choix = eleve_courant(request)
    if eleve is None or eleve.classe is None:
        return render(request, "cahier/eleve.html", {"eleve": eleve, "choix_eleves": choix})
    devoirs = list(devoirs_a_venir(eleve.classe))
    faits = set(DevoirFait.objects.filter(eleve=eleve, devoir__in=devoirs).values_list("devoir_id", flat=True))
    for d in devoirs:
        d.fait = d.pk in faits
    par_jour = [(jour, list(items)) for jour, items in groupby(devoirs, key=lambda d: d.pour_le)]

    matiere = request.GET.get("matiere")
    contenus = ContenuSeance.objects.filter(enseignement__classe=eleve.classe).select_related("enseignement__matiere")
    if matiere and matiere.isdigit():
        contenus = contenus.filter(enseignement__matiere_id=int(matiere))
    contexte = {
        "eleve": eleve,
        "choix_eleves": choix,
        "par_jour": par_jour,
        "contenus": contenus[:30],
        "matieres": [e.matiere for e in eleve.classe.enseignements.select_related("matiere")],
        "matiere_choisie": int(matiere) if matiere and matiere.isdigit() else None,
    }
    return render(request, "cahier/eleve.html", contexte)


@role_requis(R.ENSEIGNANT, R.ADMIN)
def classe(request, classe_id):
    """Cahier de texte complet d'une classe (consultation enseignants / administration)."""
    cl = get_object_or_404(Classe, pk=classe_id)
    contexte = {
        "classe": cl,
        "devoirs": devoirs_a_venir(cl),
        "contenus": ContenuSeance.objects.filter(enseignement__classe=cl).select_related("enseignement__matiere")[:50],
    }
    return render(request, "cahier/classe.html", contexte)


@role_requis(R.ENSEIGNANT, R.ADMIN)
def enseignement(request, enseignement_id):
    ens = get_object_or_404(Enseignement.objects.select_related("classe", "matiere"), pk=enseignement_id)
    verifier_gestion_enseignement(request.user, ens)
    contexte = {
        "ens": ens,
        "contenus": ens.contenus.all()[:50],
        "devoirs": ens.devoirs.order_by("-pour_le")[:50],
        "effectif": ens.classe.eleves.count(),
    }
    return render(request, "cahier/enseignement.html", contexte)


def _formulaire(request, enseignement_id, pk, modele, classe_form, titre):
    ens = get_object_or_404(Enseignement, pk=enseignement_id)
    verifier_gestion_enseignement(request.user, ens)
    instance = get_object_or_404(modele, pk=pk, enseignement=ens) if pk else modele(enseignement=ens)
    if request.method == "POST":
        form = classe_form(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            nouveau = obj.pk is None
            if nouveau:
                obj.auteur = request.user
            obj.save()
            if nouveau and isinstance(obj, Devoir):
                eleves = ens.classe.eleves.all()
                notifier(
                    User.objects.filter(Q(eleve__in=eleves) | Q(enfants__in=eleves), is_active=True).distinct(),
                    Notification.Type.DEVOIR,
                    f"Nouveau devoir en {ens.matiere} pour le {obj.pour_le:%d/%m} : {obj.titre}",
                    lien="/cahier-de-texte/",
                )
            messages.success(request, "Enregistré.")
            return redirect("cahier:enseignement", enseignement_id=ens.pk)
    else:
        initial = {"date": timezone.localdate(), "donne_le": timezone.localdate()} if not pk else None
        form = classe_form(instance=instance, initial=initial)
    return render(request, "cahier/form.html", {"form": form, "ens": ens, "titre": titre})


@role_requis(R.ENSEIGNANT, R.ADMIN)
def contenu_form(request, enseignement_id, pk=None):
    return _formulaire(request, enseignement_id, pk, ContenuSeance, ContenuSeanceForm, "Contenu de séance")


@role_requis(R.ENSEIGNANT, R.ADMIN)
def devoir_form(request, enseignement_id, pk=None):
    return _formulaire(request, enseignement_id, pk, Devoir, DevoirForm, "Devoir")


@require_POST
@role_requis(R.ENSEIGNANT, R.ADMIN)
def supprimer(request, type_, pk):
    modele = {"contenu": ContenuSeance, "devoir": Devoir}.get(type_)
    if modele is None:
        raise Http404
    obj = get_object_or_404(modele.objects.select_related("enseignement"), pk=pk)
    verifier_gestion_enseignement(request.user, obj.enseignement)
    ens_id = obj.enseignement_id
    obj.delete()
    messages.success(request, "Supprimé.")
    return redirect("cahier:enseignement", enseignement_id=ens_id)


@require_POST
@role_requis(R.ELEVE)
def basculer_fait(request, pk):
    """L'élève coche / décoche « fait » (seulement pour un devoir de sa classe)."""
    eleve = request.user.eleve
    devoir = get_object_or_404(Devoir, pk=pk)
    if devoir.enseignement.classe_id != eleve.classe_id:
        raise PermissionDenied
    lien, cree = DevoirFait.objects.get_or_create(devoir=devoir, eleve=eleve)
    if not cree:
        lien.delete()
    return redirect("cahier:index")
