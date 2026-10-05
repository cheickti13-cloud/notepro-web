import csv
from pathlib import Path
from datetime import date as Date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from core.audit import tracer
from core.models import JournalAcces
from core.permissions import R, eleve_courant, role_requis, verifier_acces_eleve
from edt.models import Creneau, ModificationCours
from messagerie.models import Notification
from messagerie.services import notifier

from .forms import FiltreAdminForm, JustificationForm, SaisieAdminForm, TraitementForm
from .models import Absence, Appel
from .services import PRESENT, cours_a_appeler, enregistrer_appel, notifier_absences, peut_faire_appel, statistiques


def _date_requete(request):
    try:
        return Date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return timezone.localdate()


# ---------------------------------------------------------------------------
# Enseignant : appel
# ---------------------------------------------------------------------------
@role_requis(R.ENSEIGNANT, R.ADMIN)
def mes_appels(request):
    if request.user.est_admin:
        return redirect("absences:vue_admin")
    jour = _date_requete(request)
    return render(request, "absences/mes_appels.html", {"jour": jour, "cours": cours_a_appeler(request.user, jour)})


@role_requis(R.ENSEIGNANT, R.ADMIN)
def appel(request, creneau_id, jour):
    creneau = get_object_or_404(Creneau.objects.select_related("enseignement__classe", "enseignement__matiere"), pk=creneau_id)
    try:
        jour = Date.fromisoformat(jour)
    except ValueError:
        raise Http404
    if jour.weekday() != creneau.jour:
        raise Http404("Ce cours n'a pas lieu ce jour-là.")
    if not peut_faire_appel(request.user, creneau, jour):
        raise PermissionDenied("Vous n'êtes pas l'enseignant de ce cours.")
    if ModificationCours.objects.filter(creneau=creneau, date=jour, type=ModificationCours.Type.ANNULATION).exists():
        messages.warning(request, "Ce cours est annulé : pas d'appel à faire.")
        return redirect("absences:mes_appels")

    eleves = list(creneau.enseignement.classe.eleves.select_related("user"))
    existantes = {a.eleve_id: a for a in Absence.objects.filter(creneau=creneau, date=jour)}

    if request.method == "POST":
        saisies, erreurs = {}, []
        for e in eleves:
            statut = request.POST.get(f"statut_{e.pk}", PRESENT)
            if statut not in {PRESENT, Absence.Type.ABSENCE, Absence.Type.RETARD}:
                statut = PRESENT
            minutes = None
            if statut == Absence.Type.RETARD:
                brut = request.POST.get(f"minutes_{e.pk}", "").strip()
                if not brut.isdigit() or not (1 <= int(brut) <= 240):
                    erreurs.append(f"{e} : durée du retard invalide (1 à 240 minutes).")
                    continue
                minutes = int(brut)
            saisies[e] = (statut, minutes)
        if erreurs:
            for err in erreurs:
                messages.error(request, err)
        else:
            try:
                nouvelles = enregistrer_appel(creneau, jour, request.user, saisies)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(request, f"Appel enregistré ({len(nouvelles)} nouvelle(s) absence(s) ou retard(s)).")
                return redirect(f"{reverse('absences:mes_appels')}?date={jour.isoformat()}")

    lignes = []
    for e in eleves:
        a = existantes.get(e.pk)
        lignes.append({
            "eleve": e,
            "statut": request.POST.get(f"statut_{e.pk}") if request.method == "POST" else (a.type if a else PRESENT),
            "minutes": request.POST.get(f"minutes_{e.pk}", "") if request.method == "POST" else (a.minutes_retard if a and a.minutes_retard else ""),
            "justifiee": a is not None and a.statut == Absence.Statut.JUSTIFIEE,
        })
    contexte = {
        "creneau": creneau,
        "jour": jour,
        "lignes": lignes,
        "deja_fait": Appel.objects.filter(creneau=creneau, date=jour).exists(),
    }
    return render(request, "absences/appel.html", contexte)


# ---------------------------------------------------------------------------
# Élève / parent : consultation et justification
# ---------------------------------------------------------------------------
def mes_absences(request):
    if request.user.est_admin:
        return redirect("absences:vue_admin")
    eleve, choix = eleve_courant(request)
    absences = (
        Absence.objects.filter(eleve=eleve).select_related("creneau__enseignement__matiere") if eleve else Absence.objects.none()
    )
    return render(
        request,
        "absences/mes_absences.html",
        {"eleve": eleve, "choix_eleves": choix, "absences": absences, "stats": statistiques(absences) if eleve else None},
    )


@role_requis(R.PARENT)
def justifier(request, pk):
    absence = get_object_or_404(Absence.objects.select_related("eleve__user"), pk=pk)
    verifier_acces_eleve(request.user, absence.eleve)
    if not absence.est_justifiable:
        messages.info(request, "Cette absence a déjà été justifiée ou est en cours de traitement.")
        return redirect(f"/absences/?eleve={absence.eleve_id}")
    if request.method == "POST":
        form = JustificationForm(request.POST, request.FILES, instance=absence)
        if form.is_valid():
            a = form.save(commit=False)
            a.statut = Absence.Statut.EN_ATTENTE
            a.justifiee_par = request.user
            a.justifiee_le = timezone.now()
            a.save()
            notifier(
                User.objects.filter(role=R.ADMIN, is_active=True),
                Notification.Type.ABSENCE,
                f"Justificatif à valider : {a.eleve} ({a.date:%d/%m})",
                lien="/absences/administration/?statut=EN_ATTENTE",
            )
            messages.success(request, "Justification envoyée à la vie scolaire.")
            return redirect(f"/absences/?eleve={a.eleve_id}")
    else:
        form = JustificationForm(instance=absence)
    return render(request, "absences/justifier.html", {"form": form, "absence": absence})


def justificatif(request, pk):
    """Téléchargement d'un justificatif : parent de l'élève ou administration uniquement."""
    absence = get_object_or_404(Absence.objects.select_related("eleve"), pk=pk)
    u = request.user
    autorise = u.est_admin or (u.est_parent and u.enfants.filter(pk=absence.eleve_id).exists())
    if not autorise:
        raise PermissionDenied
    if not absence.justificatif:
        raise Http404
    tracer(request, JournalAcces.Action.TELECHARGEMENT, f"justificatif absence #{absence.pk} ({absence.eleve})")
    try:
        fichier = absence.justificatif.open("rb")
    except FileNotFoundError:
        raise Http404("Fichier introuvable.")
    return FileResponse(fichier, as_attachment=True, filename=f"justificatif-{absence.pk}{Path(absence.justificatif.name).suffix}")


# ---------------------------------------------------------------------------
# Administration : vue consolidée
# ---------------------------------------------------------------------------
def _absences_filtrees(form):
    qs = Absence.objects.select_related("eleve__user", "eleve__classe", "creneau__enseignement__matiere")
    if form.is_valid():
        f = form.cleaned_data
        if f["debut"]:
            qs = qs.filter(date__gte=f["debut"])
        if f["fin"]:
            qs = qs.filter(date__lte=f["fin"])
        if f["classe"]:
            qs = qs.filter(eleve__classe=f["classe"])
        if f["type"]:
            qs = qs.filter(type=f["type"])
        if f["statut"]:
            qs = qs.filter(statut=f["statut"])
        if f["eleve"]:
            qs = qs.filter(Q(eleve__user__last_name__icontains=f["eleve"]) | Q(eleve__user__first_name__icontains=f["eleve"]))
    return qs


@role_requis(R.ADMIN)
def vue_admin(request):
    form = FiltreAdminForm(request.GET or None)
    qs = _absences_filtrees(form)
    aujourd_hui = timezone.localdate()
    # Élèves les plus absents sur la sélection
    top = (
        qs.values("eleve__pk", "eleve__user__first_name", "eleve__user__last_name", "eleve__classe__nom")
        .annotate(n=Count("pk"), nj=Count("pk", filter=Q(statut__in=["NON_JUSTIFIEE", "REFUSEE"])))
        .order_by("-n")[:10]
    )
    contexte = {
        "form": form,
        "absences": qs[:300],
        "total": qs.count(),
        "stats": statistiques(qs),
        "stats_jour": statistiques(Absence.objects.filter(date=aujourd_hui)),
        "top": top,
        "traitement": TraitementForm(),
        "query": request.GET.urlencode(),
    }
    return render(request, "absences/vue_admin.html", contexte)


@role_requis(R.ADMIN)
def export_csv(request):
    qs = _absences_filtrees(FiltreAdminForm(request.GET or None))
    tracer(request, JournalAcces.Action.EXPORT, f"export CSV absences ({qs.count()} lignes)")
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = 'attachment; filename="absences.csv"'
    reponse.write("﻿")  # BOM pour Excel
    w = csv.writer(reponse, delimiter=";")
    w.writerow(["Date", "Élève", "Classe", "Cours", "Type", "Retard (min)", "Statut"])
    for a in qs:
        w.writerow([a.date.strftime("%d/%m/%Y"), str(a.eleve), str(a.eleve.classe or ""), a.libelle_creneau,
                    a.get_type_display(), a.minutes_retard or "", a.get_statut_display()])
    return reponse


@require_POST
@role_requis(R.ADMIN)
def traiter(request, pk):
    absence = get_object_or_404(Absence, pk=pk)
    form = TraitementForm(request.POST)
    if form.is_valid():
        absence.statut = form.cleaned_data["decision"]
        absence.commentaire_admin = form.cleaned_data["commentaire"]
        absence.traitee_par = request.user
        absence.save(update_fields=["statut", "commentaire_admin", "traitee_par"])
        if absence.justifiee_par_id:
            notifier(
                User.objects.filter(pk=absence.justifiee_par_id),
                Notification.Type.ABSENCE,
                f"Justification {'acceptée' if absence.statut == 'JUSTIFIEE' else 'refusée'} : {absence.eleve} ({absence.date:%d/%m})",
                lien=f"/absences/?eleve={absence.eleve_id}",
            )
        messages.success(request, "Décision enregistrée.")
    retour = request.POST.get("retour", "")
    return redirect(f"/absences/administration/?{retour}" if retour else "absences:vue_admin")


@role_requis(R.ADMIN)
def saisie_admin(request):
    if request.method == "POST":
        form = SaisieAdminForm(request.POST)
        if form.is_valid():
            a = form.save(commit=False)
            a.saisie_par = request.user
            if a.statut == Absence.Statut.JUSTIFIEE:
                a.traitee_par = request.user
            a.save()
            notifier_absences([a])
            messages.success(request, "Absence enregistrée et famille notifiée.")
            return redirect("absences:vue_admin")
    else:
        form = SaisieAdminForm(initial={"date": timezone.localdate()})
    return render(request, "absences/saisie_admin.html", {"form": form})
