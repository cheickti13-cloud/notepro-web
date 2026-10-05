"""Tableau de bord personnalisé selon le rôle connecté."""
from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from absences.models import Absence
from absences.services import cours_a_appeler, statistiques, stats_eleve
from accounts.models import Eleve, User
from cahier.views import devoirs_a_venir
from core.permissions import eleves_visibles
from edt.models import ModificationCours
from edt.services import cours_du_jour, creneaux_classe
from messagerie.models import Notification
from messagerie.services import annonces_visibles
from notes.services import dernieres_notes
from scolarite.models import Classe
from scolarite.services import annee_active, periode_courante


def _resume_eleve(eleve, aujourd_hui):
    """Bloc de synthèse d'un élève (utilisé par l'élève et par ses parents)."""
    periode = periode_courante(aujourd_hui)
    return {
        "eleve": eleve,
        "cours": cours_du_jour(creneaux_classe(eleve.classe), aujourd_hui) if eleve.classe else [],
        "devoirs": list(devoirs_a_venir(eleve.classe, aujourd_hui, jours=7)) if eleve.classe else [],
        "notes": dernieres_notes(eleve, 5),
        "absences": stats_eleve(eleve, periode.debut if periode else None, periode.fin if periode else None),
    }


def index(request):
    u = request.user
    aujourd_hui = timezone.localdate()
    contexte = {
        "aujourd_hui": aujourd_hui,
        "notifications": Notification.objects.filter(destinataire=u, lue=False)[:6],
        "annonces": annonces_visibles(u).filter(publiee_le__gte=timezone.now() - timedelta(days=30))[:4],
    }

    if u.est_eleve:
        eleve = eleves_visibles(u).first()
        contexte["resumes"] = [_resume_eleve(eleve, aujourd_hui)] if eleve else []
        return render(request, "dashboard/famille.html", contexte)

    if u.est_parent:
        contexte["resumes"] = [_resume_eleve(e, aujourd_hui) for e in eleves_visibles(u)]
        return render(request, "dashboard/famille.html", contexte)

    if u.est_enseignant:
        contexte["cours"] = cours_a_appeler(u, aujourd_hui)
        contexte["appels_manquants"] = sum(1 for c in contexte["cours"] if not c["fait"])
        contexte["classes_pp"] = Classe.objects.filter(annee=annee_active(), professeur_principal=u)
        return render(request, "dashboard/enseignant.html", contexte)

    # Administration
    annee = annee_active()
    contexte.update({
        "annee": annee,
        "nb_eleves": Eleve.objects.filter(classe__annee=annee).count(),
        "nb_classes": Classe.objects.filter(annee=annee).count(),
        "nb_enseignants": User.objects.filter(role=User.Role.ENSEIGNANT, is_active=True).count(),
        "stats_jour": statistiques(Absence.objects.filter(date=aujourd_hui)),
        "en_attente": Absence.objects.filter(statut=Absence.Statut.EN_ATTENTE).count(),
        "modifs_jour": ModificationCours.objects.filter(date=aujourd_hui).select_related(
            "creneau__enseignement__matiere", "creneau__enseignement__classe", "remplacant", "nouvelle_salle"
        ),
        "sans_classe": Eleve.objects.filter(classe__isnull=True).count(),
    })
    return render(request, "dashboard/admin.html", contexte)
