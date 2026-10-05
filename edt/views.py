from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from core.permissions import R, eleve_courant, role_requis, verifier_acces_eleve
from scolarite.models import Classe
from scolarite.services import annee_active

from .forms import ModificationCoursForm
from .models import ModificationCours
from .services import (
    construire_semaine,
    creneaux_classe,
    creneaux_enseignant,
    notifier_modification,
    semaine_depuis_requete,
)


def _rendu(request, titre, jours, lundi, **extra):
    contexte = {
        "titre": titre,
        "jours": jours,
        "lundi": lundi,
        "semaine_prec": lundi - timedelta(days=7),
        "semaine_suiv": lundi + timedelta(days=7),
        "nb_jours": len(jours),
        "classes": Classe.objects.filter(annee=annee_active()) if request.user.est_admin or request.user.est_enseignant else None,
        "enseignants": User.objects.filter(role=R.ENSEIGNANT, is_active=True) if request.user.est_admin or request.user.est_enseignant else None,
        **extra,
    }
    return render(request, "edt/semaine.html", contexte)


def mon_edt(request):
    """Redirige chaque rôle vers l'emploi du temps qui le concerne."""
    u = request.user
    if u.est_enseignant:
        return redirect("edt:enseignant", user_id=u.pk)
    if u.est_eleve or u.est_parent:
        eleve, _ = eleve_courant(request)
        if eleve is None:
            return render(request, "edt/vide.html")
        return redirect("edt:eleve", eleve_id=eleve.pk)
    # Admin : première classe de l'année active
    classe = Classe.objects.filter(annee=annee_active()).first()
    if classe is None:
        return render(request, "edt/vide.html")
    return redirect("edt:classe", classe_id=classe.pk)


def edt_classe(request, classe_id):
    classe = get_object_or_404(Classe, pk=classe_id)
    u = request.user
    # Élèves et parents : uniquement la classe de l'élève concerné
    if u.est_eleve and getattr(u, "eleve", None) and u.eleve.classe_id != classe.pk:
        raise PermissionDenied
    if u.est_parent and not u.enfants.filter(classe=classe).exists():
        raise PermissionDenied
    lundi = semaine_depuis_requete(request)
    jours = construire_semaine(creneaux_classe(classe), lundi)
    return _rendu(request, f"Classe {classe}", jours, lundi, vue="classe", cible=classe)


@role_requis(R.ENSEIGNANT, R.ADMIN)
def edt_enseignant(request, user_id):
    enseignant = get_object_or_404(User, pk=user_id, role=R.ENSEIGNANT)
    lundi = semaine_depuis_requete(request)
    jours = construire_semaine(creneaux_enseignant(enseignant), lundi, remplacant=enseignant)
    return _rendu(request, f"{enseignant}", jours, lundi, vue="enseignant", cible=enseignant)


def edt_eleve(request, eleve_id):
    from accounts.models import Eleve

    eleve = get_object_or_404(Eleve.objects.select_related("classe", "user"), pk=eleve_id)
    verifier_acces_eleve(request.user, eleve)
    lundi = semaine_depuis_requete(request)
    jours = construire_semaine(creneaux_classe(eleve.classe), lundi) if eleve.classe else []
    _, choix = eleve_courant(request) if request.user.est_parent else (None, [])
    return _rendu(
        request, f"{eleve} ({eleve.classe or 'sans classe'})", jours, lundi,
        vue="eleve", cible=eleve, eleve=eleve, choix_eleves=choix,
    )


@role_requis(R.ADMIN)
def modifications(request):
    """Gestion des changements de salle, remplacements et annulations."""
    if request.method == "POST":
        form = ModificationCoursForm(request.POST)
        if form.is_valid():
            # La validation métier (ModificationCours.clean) a déjà été faite par is_valid()
            modif = form.save(commit=False)
            modif.cree_par = request.user
            modif.save()
            notifier_modification(modif)
            messages.success(request, "Modification enregistrée, les personnes concernées sont notifiées.")
            return redirect("edt:modifications")
    else:
        form = ModificationCoursForm()
    a_venir = ModificationCours.objects.filter(date__gte=timezone.localdate()).select_related(
        "creneau__enseignement__matiere", "creneau__enseignement__classe", "nouvelle_salle", "remplacant"
    ).order_by("date", "creneau__heure_debut")
    return render(request, "edt/modifications.html", {"form": form, "a_venir": a_venir})


@require_POST
@role_requis(R.ADMIN)
def supprimer_modification(request, pk):
    modif = get_object_or_404(ModificationCours, pk=pk)
    modif.delete()
    messages.success(request, "Modification supprimée : le cours reprend son déroulement normal.")
    return redirect("edt:modifications")
