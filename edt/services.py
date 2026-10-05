"""Construction des emplois du temps hebdomadaires (avec modifications appliquées)."""
from dataclasses import dataclass
from datetime import date as Date, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Creneau, ModificationCours

NOMS_JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]


@dataclass
class CoursAffiche:
    creneau: Creneau
    date: Date
    matiere: object
    classe: object
    enseignant: object
    salle: object
    modification: ModificationCours | None = None

    @property
    def annule(self):
        return self.modification is not None and self.modification.type == ModificationCours.Type.ANNULATION

    @property
    def modifie(self):
        return self.modification is not None and not self.annule


def lundi_de(d: Date) -> Date:
    return d - timedelta(days=d.weekday())


def semaine_depuis_requete(request) -> Date:
    """Lundi de la semaine demandée via ?semaine=AAAA-MM-JJ (par défaut : semaine en cours)."""
    valeur = request.GET.get("semaine", "")
    try:
        d = Date.fromisoformat(valeur)
    except ValueError:
        d = timezone.localdate()
    return lundi_de(d)


def creneaux_classe(classe):
    return Creneau.objects.filter(enseignement__classe=classe)


def creneaux_enseignant(user):
    return Creneau.objects.filter(enseignement__enseignant=user)


def construire_semaine(creneaux, lundi: Date, remplacant=None):
    """
    Retourne la liste des jours de la semaine, chacun avec ses cours triés.
    `remplacant` : si fourni (vue enseignant), ajoute les cours où il remplace un collègue.
    """
    fin = lundi + timedelta(days=6)
    if remplacant is not None:
        ids_remplacement = ModificationCours.objects.filter(
            remplacant=remplacant, date__range=(lundi, fin), type=ModificationCours.Type.REMPLACEMENT
        ).values_list("creneau_id", flat=True)
        creneaux = Creneau.objects.filter(Q(pk__in=creneaux.values("pk")) | Q(pk__in=ids_remplacement))

    creneaux = list(
        creneaux.select_related(
            "enseignement__matiere", "enseignement__classe", "enseignement__enseignant", "salle"
        )
    )
    modifs = {
        (m.creneau_id, m.date): m
        for m in ModificationCours.objects.filter(
            creneau__in=[c.pk for c in creneaux], date__range=(lundi, fin)
        ).select_related("nouvelle_salle", "remplacant")
    }

    nb_jours = 6 if any(c.jour == Creneau.Jour.SAMEDI for c in creneaux) else 5
    aujourdhui = timezone.localdate()
    jours = []
    for i in range(nb_jours):
        d = lundi + timedelta(days=i)
        cours = []
        for c in sorted((c for c in creneaux if c.jour == i), key=lambda c: c.heure_debut):
            m = modifs.get((c.pk, d))
            # Vue remplaçant : n'afficher le cours d'un collègue que le jour du remplacement
            if remplacant is not None and c.enseignement.enseignant_id != remplacant.pk:
                if not (m and m.remplacant_id == remplacant.pk):
                    continue
            enseignant = c.enseignement.enseignant
            salle = c.salle
            if m and m.type == ModificationCours.Type.REMPLACEMENT and m.remplacant:
                enseignant = m.remplacant
            if m and m.type == ModificationCours.Type.CHANGEMENT_SALLE and m.nouvelle_salle:
                salle = m.nouvelle_salle
            cours.append(
                CoursAffiche(
                    creneau=c,
                    date=d,
                    matiere=c.enseignement.matiere,
                    classe=c.enseignement.classe,
                    enseignant=enseignant,
                    salle=salle,
                    modification=m,
                )
            )
        jours.append({"date": d, "nom": NOMS_JOURS[i], "cours": cours, "aujourdhui": d == aujourdhui})
    return jours


def cours_du_jour(creneaux, d: Date | None = None, remplacant=None):
    d = d or timezone.localdate()
    if d.weekday() > 5:
        return []
    for jour in construire_semaine(creneaux, lundi_de(d), remplacant=remplacant):
        if jour["date"] == d:
            return jour["cours"]
    return []


def notifier_modification(modif: ModificationCours):
    """Prévient élèves, parents et enseignants concernés d'un changement de cours."""
    from accounts.models import User
    from messagerie.models import Notification
    from messagerie.services import notifier

    classe = modif.creneau.enseignement.classe
    destinataires = set(
        User.objects.filter(
            Q(eleve__classe=classe) | Q(enfants__classe=classe), is_active=True
        ).values_list("pk", flat=True)
    )
    destinataires.add(modif.creneau.enseignement.enseignant_id)
    if modif.remplacant_id:
        destinataires.add(modif.remplacant_id)
    titre = (
        f"{modif.get_type_display()} : {modif.creneau.enseignement.matiere} ({classe}) "
        f"le {modif.date:%d/%m} à {modif.creneau.heure_debut:%H:%M}"
    )
    notifier(
        User.objects.filter(pk__in=destinataires),
        Notification.Type.EDT,
        titre,
        lien=f"/emploi-du-temps/classe/{classe.pk}/?semaine={modif.date.isoformat()}",
    )
