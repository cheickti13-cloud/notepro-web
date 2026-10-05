from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from core.permissions import R, eleve_courant, role_requis, verifier_gestion_enseignement
from messagerie.models import Notification
from messagerie.services import notifier
from scolarite.models import Enseignement
from scolarite.services import annee_active, periode_depuis_requete, periodes_actives

from .forms import EvaluationForm
from .models import Evaluation, Note
from .services import releve_eleve, tableau_classe


@role_requis(R.ENSEIGNANT, R.ADMIN)
def mes_enseignements(request):
    qs = Enseignement.objects.filter(classe__annee=annee_active()).select_related("classe", "matiere", "enseignant")
    if request.user.est_enseignant:
        qs = qs.filter(enseignant=request.user)
    qs = qs.annotate(nb_evaluations=Count("evaluations"))
    return render(request, "notes/mes_enseignements.html", {"enseignements": qs})


@role_requis(R.ENSEIGNANT, R.ADMIN)
def evaluations(request, enseignement_id):
    ens = get_object_or_404(Enseignement.objects.select_related("classe", "matiere"), pk=enseignement_id)
    verifier_gestion_enseignement(request.user, ens)
    periode = periode_depuis_requete(request)
    eleves = list(ens.classe.eleves.select_related("user"))
    t = tableau_classe(ens.classe, periode, eleves, publiees_seulement=False) if periode else None
    lignes = []
    if t:
        for e in eleves:
            lignes.append(
                {
                    "eleve": e,
                    "notes": [t.notes.get((ev.pk, e.pk)) for ev in t.evaluations.get(ens.pk, [])],
                    "moyenne": t.moyennes[e.pk][ens.pk],
                }
            )
    contexte = {
        "ens": ens,
        "periode": periode,
        "periodes": periodes_actives(),
        "evals": t.evaluations.get(ens.pk, []) if t else [],
        "lignes": lignes,
        "stats": t.stats_matieres.get(ens.pk) if t else None,
    }
    return render(request, "notes/evaluations.html", contexte)


@role_requis(R.ENSEIGNANT, R.ADMIN)
def evaluation_form(request, enseignement_id, pk=None):
    ens = get_object_or_404(Enseignement, pk=enseignement_id)
    verifier_gestion_enseignement(request.user, ens)
    instance = get_object_or_404(Evaluation, pk=pk, enseignement=ens) if pk else Evaluation(enseignement=ens)
    if request.method == "POST":
        form = EvaluationForm(request.POST, instance=instance)
        if form.is_valid():
            ev = form.save(commit=False)
            if not pk:
                ev.creee_par = request.user
            ev.save()
            messages.success(request, "Évaluation enregistrée. Saisissez maintenant les notes.")
            return redirect("notes:saisie", pk=ev.pk)
    else:
        form = EvaluationForm(instance=instance)
    return render(request, "notes/evaluation_form.html", {"form": form, "ens": ens, "evaluation": instance if pk else None})


@require_POST
@role_requis(R.ENSEIGNANT, R.ADMIN)
def evaluation_supprimer(request, pk):
    ev = get_object_or_404(Evaluation.objects.select_related("enseignement"), pk=pk)
    verifier_gestion_enseignement(request.user, ev.enseignement)
    ens_id = ev.enseignement_id
    ev.delete()
    messages.success(request, "Évaluation et notes associées supprimées.")
    return redirect("notes:evaluations", enseignement_id=ens_id)


def _parse_note(texte):
    """Accepte « 12,5 » comme « 12.5 ». Retourne (Decimal|None, erreur|None)."""
    texte = (texte or "").strip().replace(",", ".")
    if not texte:
        return None, None
    try:
        return Decimal(texte), None
    except InvalidOperation:
        return None, "note invalide"


@role_requis(R.ENSEIGNANT, R.ADMIN)
def saisie(request, pk):
    """Grille de saisie des notes d'une évaluation pour toute la classe."""
    ev = get_object_or_404(Evaluation.objects.select_related("enseignement__classe", "enseignement__matiere", "periode"), pk=pk)
    verifier_gestion_enseignement(request.user, ev.enseignement)
    eleves = list(ev.enseignement.classe.eleves.select_related("user"))
    existantes = {n.eleve_id: n for n in ev.notes.all()}
    erreurs = {}

    if request.method == "POST":
        a_enregistrer, a_supprimer = [], []
        for e in eleves:
            statut = request.POST.get(f"statut_{e.pk}", Note.Statut.NOTEE)
            if statut not in Note.Statut.values:
                statut = Note.Statut.NOTEE
            valeur, err = _parse_note(request.POST.get(f"note_{e.pk}"))
            commentaire = request.POST.get(f"commentaire_{e.pk}", "").strip()[:200]
            if err:
                erreurs[e.pk] = err
                continue
            if statut == Note.Statut.NOTEE and valeur is None:
                if e.pk in existantes:
                    a_supprimer.append(existantes[e.pk])  # champ vidé = note retirée
                continue
            if statut != Note.Statut.NOTEE:
                valeur = None
            note = existantes.get(e.pk) or Note(evaluation=ev, eleve=e)
            note.valeur, note.statut, note.commentaire = valeur, statut, commentaire
            try:
                # full_clean() appelle aussi Note.clean() (barème, classe de l'élève)
                note.full_clean(exclude=["evaluation", "eleve"])
            except ValidationError as exc:
                erreurs[e.pk] = "; ".join(exc.messages)
                continue
            a_enregistrer.append(note)

        if erreurs:
            messages.error(request, "Certaines notes sont invalides : rien n'a été enregistré. Corrigez les lignes signalées.")
        else:
            nouveaux = [n.eleve for n in a_enregistrer if n.pk is None]
            with transaction.atomic():
                for n in a_enregistrer:
                    n.save()
                for n in a_supprimer:
                    n.delete()
            if ev.publiee and nouveaux:
                _notifier_nouvelles_notes(ev, nouveaux)
            messages.success(request, f"{len(a_enregistrer)} note(s) enregistrée(s).")
            return redirect("notes:evaluations", enseignement_id=ev.enseignement_id)

    lignes = []
    for e in eleves:
        n = existantes.get(e.pk)
        lignes.append(
            {
                "eleve": e,
                "valeur": request.POST.get(f"note_{e.pk}") if request.method == "POST" else (str(n.valeur).replace(".", ",") if n and n.valeur is not None else ""),
                "statut": request.POST.get(f"statut_{e.pk}") if request.method == "POST" else (n.statut if n else Note.Statut.NOTEE),
                "commentaire": request.POST.get(f"commentaire_{e.pk}", "") if request.method == "POST" else (n.commentaire if n else ""),
                "erreur": erreurs.get(e.pk),
            }
        )
    return render(request, "notes/saisie.html", {"ev": ev, "lignes": lignes, "statuts": Note.Statut.choices})


def _notifier_nouvelles_notes(ev, eleves):
    """Notifie les élèves concernés et leurs parents (sans divulguer la note dans le titre)."""
    users = User.objects.filter(is_active=True).filter(
        pk__in=[e.user_id for e in eleves]
    ) | User.objects.filter(is_active=True, enfants__in=eleves)
    notifier(
        users.distinct(),
        Notification.Type.NOTE,
        f"Nouvelle note en {ev.enseignement.matiere} : {ev.titre}",
        lien="/notes/releve/",
    )


def releve(request):
    """Relevé de notes : élève (lui-même), parent (ses enfants), enseignant/admin (?eleve=)."""
    eleve, choix = eleve_courant(request)
    periode = periode_depuis_requete(request)
    donnees = releve_eleve(eleve, periode) if eleve else None
    return render(
        request,
        "notes/releve.html",
        {
            "eleve": eleve,
            "choix_eleves": choix,
            "periode": periode,
            "periodes": periodes_actives(),
            "releve": donnees,
        },
    )
