from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from accounts.models import Eleve, User
from core.audit import tracer
from core.models import JournalAcces
from core.permissions import R, eleve_courant, role_requis, verifier_acces_eleve, verifier_gestion_enseignement
from messagerie.models import Notification
from messagerie.services import notifier
from notes.services import tableau_classe
from scolarite.models import Classe, Enseignement, Periode
from scolarite.services import annee_active, periode_depuis_requete, periodes_actives

from .models import Appreciation, AppreciationGenerale, PublicationBulletin
from .pdf import generer_pdf
from .services import donnees_bulletins, est_publie


def _peut_gerer_classe(user, classe):
    """Conseil de classe : administration ou professeur principal."""
    return user.est_admin or (user.est_enseignant and classe.professeur_principal_id == user.pk)


def index(request):
    u = request.user
    periodes = periodes_actives()
    if u.est_eleve or u.est_parent:
        eleve, choix = eleve_courant(request)
        publies = set()
        if eleve and eleve.classe_id:
            publies = set(PublicationBulletin.objects.filter(classe_id=eleve.classe_id).values_list("periode_id", flat=True))
        return render(request, "bulletins/index_famille.html", {
            "eleve": eleve, "choix_eleves": choix,
            "periodes": [(p, p.pk in publies) for p in periodes],
        })
    classes = Classe.objects.filter(annee=annee_active())
    contexte = {"periodes": periodes}
    if u.est_enseignant:
        contexte["enseignements"] = Enseignement.objects.filter(enseignant=u, classe__annee=annee_active()).select_related("classe", "matiere")
        contexte["classes_pp"] = classes.filter(professeur_principal=u)
    else:
        publications = {(p.classe_id, p.periode_id) for p in PublicationBulletin.objects.filter(classe__in=classes)}
        contexte["tableau"] = [(c, [(p, (c.pk, p.pk) in publications) for p in periodes]) for c in classes]
    return render(request, "bulletins/index_personnel.html", contexte)


@role_requis(R.ENSEIGNANT, R.ADMIN)
def appreciations(request, enseignement_id):
    """Saisie des appréciations d'une matière pour toute la classe."""
    ens = get_object_or_404(Enseignement.objects.select_related("classe", "matiere"), pk=enseignement_id)
    verifier_gestion_enseignement(request.user, ens)
    periode = periode_depuis_requete(request)
    if periode is None:
        messages.error(request, "Aucune période définie pour l'année active.")
        return redirect("bulletins:index")
    eleves = list(ens.classe.eleves.select_related("user"))
    existantes = {a.eleve_id: a for a in Appreciation.objects.filter(enseignement=ens, periode=periode)}

    if request.method == "POST":
        with transaction.atomic():
            for e in eleves:
                texte = request.POST.get(f"app_{e.pk}", "").strip()[:600]
                a = existantes.get(e.pk)
                if texte:
                    if a:
                        a.texte, a.auteur = texte, request.user
                        a.save(update_fields=["texte", "auteur", "modifiee_le"])
                    else:
                        Appreciation.objects.create(eleve=e, enseignement=ens, periode=periode, texte=texte, auteur=request.user)
                elif a:
                    a.delete()
        messages.success(request, "Appréciations enregistrées.")
        return redirect(f"{request.path}?periode={periode.pk}")

    t = tableau_classe(ens.classe, periode, eleves, publiees_seulement=False)
    lignes = [{"eleve": e, "moyenne": t.moyennes[e.pk][ens.pk], "texte": existantes[e.pk].texte if e.pk in existantes else ""} for e in eleves]
    return render(request, "bulletins/appreciations.html", {"ens": ens, "periode": periode, "periodes": periodes_actives(), "lignes": lignes})


@role_requis(R.ENSEIGNANT, R.ADMIN)
def conseil(request, classe_id):
    """Appréciations générales et mentions (conseil de classe)."""
    classe = get_object_or_404(Classe, pk=classe_id)
    if not _peut_gerer_classe(request.user, classe):
        raise PermissionDenied("Réservé au professeur principal et à l'administration.")
    periode = periode_depuis_requete(request)
    if periode is None:
        messages.error(request, "Aucune période définie pour l'année active.")
        return redirect("bulletins:index")
    eleves = list(classe.eleves.select_related("user"))
    existantes = {a.eleve_id: a for a in AppreciationGenerale.objects.filter(periode=periode, eleve__classe=classe)}
    mentions_valides = set(AppreciationGenerale.Mention.values)

    if request.method == "POST":
        with transaction.atomic():
            for e in eleves:
                texte = request.POST.get(f"app_{e.pk}", "").strip()[:1000]
                mention = request.POST.get(f"mention_{e.pk}", "")
                mention = mention if mention in mentions_valides else ""
                AppreciationGenerale.objects.update_or_create(
                    eleve=e, periode=periode, defaults={"texte": texte, "mention": mention, "auteur": request.user}
                )
        messages.success(request, "Conseil de classe enregistré.")
        return redirect(f"{request.path}?periode={periode.pk}")

    t = tableau_classe(classe, periode, eleves, publiees_seulement=True)
    lignes = [
        {
            "eleve": e,
            "moyenne": t.generales[e.pk],
            "rang": t.rangs[e.pk],
            "texte": existantes[e.pk].texte if e.pk in existantes else "",
            "mention": existantes[e.pk].mention if e.pk in existantes else "",
        }
        for e in sorted(eleves, key=lambda x: (t.rangs[x.pk] is None, t.rangs[x.pk] or 0))
    ]
    return render(request, "bulletins/conseil.html", {
        "classe": classe, "periode": periode, "periodes": periodes_actives(), "lignes": lignes,
        "mentions": AppreciationGenerale.Mention.choices, "publie": est_publie(classe, periode),
    })


@require_POST
@role_requis(R.ADMIN)
def publier(request, classe_id, periode_id):
    classe = get_object_or_404(Classe, pk=classe_id)
    periode = get_object_or_404(Periode, pk=periode_id)
    pub = PublicationBulletin.objects.filter(classe=classe, periode=periode).first()
    if pub:
        pub.delete()
        messages.info(request, f"Bulletins de {classe} ({periode.nom}) dépubliés.")
    else:
        PublicationBulletin.objects.create(classe=classe, periode=periode, publie_par=request.user)
        eleves = classe.eleves.all()
        notifier(
            User.objects.filter(Q(eleve__in=eleves) | Q(enfants__in=eleves), is_active=True).distinct(),
            Notification.Type.BULLETIN,
            f"Le bulletin du {periode.nom} est disponible",
            lien="/bulletins/",
            importante=True,
        )
        messages.success(request, f"Bulletins de {classe} ({periode.nom}) publiés, familles notifiées.")
    return redirect("bulletins:index")


def _reponse_pdf(contenu, nom):
    r = HttpResponse(contenu, content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="{nom}.pdf"'
    return r


def pdf_eleve(request, eleve_id, periode_id):
    eleve = get_object_or_404(Eleve.objects.select_related("classe", "user"), pk=eleve_id)
    periode = get_object_or_404(Periode, pk=periode_id)
    verifier_acces_eleve(request.user, eleve)
    if eleve.classe is None:
        raise PermissionDenied
    u = request.user
    # Familles : uniquement les bulletins publiés
    if (u.est_eleve or u.est_parent) and not est_publie(eleve.classe, periode):
        raise PermissionDenied("Ce bulletin n'est pas encore publié.")
    donnees = donnees_bulletins(eleve.classe, periode, eleves=[eleve])
    tracer(request, JournalAcces.Action.TELECHARGEMENT, f"bulletin {eleve} {periode}")
    return _reponse_pdf(generer_pdf(donnees), f"bulletin-{slugify(str(eleve))}-{slugify(periode.nom)}")


def pdf_classe(request, classe_id, periode_id):
    classe = get_object_or_404(Classe, pk=classe_id)
    periode = get_object_or_404(Periode, pk=periode_id)
    if not _peut_gerer_classe(request.user, classe):
        raise PermissionDenied
    tracer(request, JournalAcces.Action.TELECHARGEMENT, f"bulletins classe {classe} {periode}")
    return _reponse_pdf(generer_pdf(donnees_bulletins(classe, periode)), f"bulletins-{slugify(classe.nom)}-{slugify(periode.nom)}")
