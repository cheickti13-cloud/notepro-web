"""Règles métier des absences : appel, statistiques, notifications."""
from django.db import transaction
from django.db.models import Count, Q, Sum

from accounts.models import User
from edt.models import ModificationCours
from edt.services import cours_du_jour, creneaux_enseignant
from messagerie.models import Notification
from messagerie.services import notifier

from .models import Absence, Appel

PRESENT = "PRESENT"


def peut_faire_appel(user, creneau, date):
    """L'enseignant du cours, son remplaçant ce jour-là, ou l'administration."""
    if user.est_admin:
        return True
    if not user.est_enseignant:
        return False
    modif = ModificationCours.objects.filter(creneau=creneau, date=date).first()
    if modif and modif.type == ModificationCours.Type.REMPLACEMENT:
        return modif.remplacant_id == user.pk
    return creneau.enseignement.enseignant_id == user.pk


def cours_a_appeler(enseignant, date):
    """Cours du jour de l'enseignant (hors cours annulés) avec l'état de l'appel."""
    cours = [c for c in cours_du_jour(creneaux_enseignant(enseignant), date, remplacant=enseignant) if not c.annule]
    # Cours remplacés par un collègue : c'est le remplaçant qui fait l'appel
    cours = [c for c in cours if c.enseignant.pk == enseignant.pk]
    faits = set(Appel.objects.filter(date=date, creneau__in=[c.creneau for c in cours]).values_list("creneau_id", flat=True))
    return [{"cours": c, "fait": c.creneau.pk in faits} for c in cours]


@transaction.atomic
def enregistrer_appel(creneau, date, auteur, saisies):
    """
    `saisies` : {eleve: (statut, minutes)} avec statut PRESENT / ABSENCE / RETARD.
    Crée, modifie ou supprime les absences de ce cours. Une absence déjà
    justifiée par la famille conserve sa justification.
    Retourne la liste des absences nouvellement créées.
    """
    existantes = {a.eleve_id: a for a in Absence.objects.filter(creneau=creneau, date=date)}
    nouvelles = []
    for eleve, (statut, minutes) in saisies.items():
        a = existantes.get(eleve.pk)
        if statut == PRESENT:
            # On ne supprime que les absences non encore justifiées (sinon : correction par la vie scolaire)
            if a and a.statut == Absence.Statut.NON_JUSTIFIEE:
                a.delete()
            continue
        if a is None:
            a = Absence(eleve=eleve, date=date, creneau=creneau, saisie_par=auteur)
            nouvelles.append(a)
        a.type = statut
        a.minutes_retard = minutes if statut == Absence.Type.RETARD else None
        a.full_clean()
        a.save()
    Appel.objects.update_or_create(creneau=creneau, date=date, defaults={"fait_par": auteur})
    if nouvelles:
        notifier_absences(nouvelles)
    return nouvelles


def notifier_absences(absences):
    """Prévient les parents (et l'élève) de chaque nouvelle absence ou retard."""
    for a in absences:
        destinataires = User.objects.filter(Q(pk=a.eleve.user_id) | Q(enfants=a.eleve), is_active=True).distinct()
        notifier(
            destinataires,
            Notification.Type.ABSENCE,
            f"{a.get_type_display()} de {a.eleve.user.first_name} le {a.date:%d/%m} ({a.libelle_creneau})",
            lien=f"/absences/?eleve={a.eleve_id}",
            importante=a.type == Absence.Type.ABSENCE,
        )


def statistiques(absences_qs):
    """Totaux sur un ensemble d'absences."""
    s = absences_qs.aggregate(
        absences=Count("pk", filter=Q(type=Absence.Type.ABSENCE)),
        retards=Count("pk", filter=Q(type=Absence.Type.RETARD)),
        non_justifiees=Count("pk", filter=Q(statut__in=[Absence.Statut.NON_JUSTIFIEE, Absence.Statut.REFUSEE])),
        en_attente=Count("pk", filter=Q(statut=Absence.Statut.EN_ATTENTE)),
        minutes_retard=Sum("minutes_retard"),
    )
    s["minutes_retard"] = s["minutes_retard"] or 0
    return s


def stats_eleve(eleve, debut=None, fin=None):
    qs = Absence.objects.filter(eleve=eleve)
    if debut:
        qs = qs.filter(date__gte=debut)
    if fin:
        qs = qs.filter(date__lte=fin)
    return statistiques(qs)
