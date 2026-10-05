"""
Construction des réponses JSON de l'API mobile.

Les structures renvoyées ici correspondent exactement aux types TypeScript de
l'application (`mobile/src/lib/types.ts`). Toute modification doit être faite
des deux côtés.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from absences.models import Absence
from absences.services import statistiques
from cahier.models import Devoir, DevoirFait
from edt.services import construire_semaine, creneaux_classe, lundi_de
from messagerie.models import Notification
from notes import calculs
from notes.models import Note
from notes.services import releve_eleve
from scolarite.services import periode_courante, periodes_actives

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def dec(v):
    """Decimal -> float arrondi (JSON), None conservé."""
    return None if v is None else round(float(v), 2)


def initiales(user):
    return ((user.first_name[:1] or "") + (user.last_name[:1] or "")).upper() or user.username[:2].upper()


def eleve_resume(e):
    return {
        "id": e.pk,
        "prenom": e.user.first_name,
        "nom": e.user.last_name,
        "initiales": initiales(e.user),
        "classe": e.classe.nom if e.classe else None,
    }


# ---------------------------------------------------------------------------
# Emploi du temps
# ---------------------------------------------------------------------------
def cours_json(c):
    statut = "annule" if c.annule else "modifie" if c.modifie else "normal"
    info = ""
    if c.modification:
        m = c.modification
        info = m.get_type_display()
        if m.nouvelle_salle:
            info += f" : salle {m.nouvelle_salle}"
        if m.remplacant:
            info += f" : {m.remplacant}"
        if m.motif:
            info += f" — {m.motif}"
    return {
        "id": c.creneau.pk,
        "date": c.date.isoformat(),
        "debut": c.creneau.heure_debut.strftime("%H:%M"),
        "fin": c.creneau.heure_fin.strftime("%H:%M"),
        "matiere": c.matiere.nom,
        "couleur": c.matiere.couleur,
        "enseignant": str(c.enseignant),
        "salle": str(c.salle) if c.salle else "",
        "classe": c.classe.nom,
        "statut": statut,
        "info": info,
    }


def semaine_eleve(eleve, lundi):
    if not eleve.classe:
        return {"lundi": lundi.isoformat(), "jours": []}
    jours = construire_semaine(creneaux_classe(eleve.classe), lundi)
    return {
        "lundi": lundi.isoformat(),
        "jours": [{"date": j["date"].isoformat(), "nom": j["nom"], "cours": [cours_json(c) for c in j["cours"]]} for j in jours],
    }


def cours_du_jour(eleve, jour=None):
    jour = jour or timezone.localdate()
    if jour.weekday() > 5 or not eleve.classe:
        return []
    sem = semaine_eleve(eleve, lundi_de(jour))
    for j in sem["jours"]:
        if j["date"] == jour.isoformat():
            return j["cours"]
    return []


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
def notes_eleve(eleve, periode):
    periodes = list(periodes_actives())
    courante = periode_courante()
    base = {
        "periodes": [{"id": p.pk, "nom": p.nom, "courante": courante is not None and p.pk == courante.pk} for p in periodes],
        "periode_id": periode.pk if periode else None,
    }
    releve = releve_eleve(eleve, periode) if periode else None
    if not releve:
        return {**base, "moyenne_generale": None, "moyenne_classe": None, "rang": None, "effectif": 0, "matieres": [], "evolution": []}

    from bulletins.models import Appreciation

    apps = {a.enseignement_id: a.texte for a in Appreciation.objects.filter(eleve=eleve, periode=periode)}
    matieres = []
    for l in releve["lignes"]:
        ens = l["enseignement"]
        evals = []
        for x in l["evaluations"]:
            ev, n = x["evaluation"], x["note"]
            evals.append({
                "id": ev.pk,
                "titre": ev.titre,
                "date": ev.date.isoformat(),
                "bareme": dec(ev.bareme),
                "coefficient": dec(ev.coefficient),
                "note": dec(n.valeur) if n else None,
                "statut": n.statut if n else None,
                "commentaire": n.commentaire if n else "",
            })
        matieres.append({
            "id": ens.pk,
            "matiere": ens.matiere.nom,
            "code": ens.matiere.code,
            "couleur": ens.matiere.couleur,
            "enseignant": str(ens.enseignant),
            "enseignant_id": ens.enseignant_id,
            "coefficient": dec(ens.coefficient),
            "moyenne": dec(l["moyenne"]),
            "moyenne_classe": dec(l["stats"]["moyenne"]),
            "min": dec(l["stats"]["min"]),
            "max": dec(l["stats"]["max"]),
            "appreciation": apps.get(ens.pk, ""),
            "evaluations": evals,
        })
    # Évolution : moyenne générale de chaque période déjà commencée
    evolution = []
    for p in periodes:
        if p.debut <= timezone.localdate():
            r = releve if p.pk == periode.pk else releve_eleve(eleve, p)
            if r and r["moyenne_generale"] is not None:
                evolution.append({"periode": p.nom, "moyenne": dec(r["moyenne_generale"]), "moyenne_classe": dec(r["stats_generale"]["moyenne"])})
    from bulletins.services import est_publie

    return {
        **base,
        "moyenne_generale": dec(releve["moyenne_generale"]),
        "moyenne_classe": dec(releve["stats_generale"]["moyenne"]),
        "rang": releve["rang"],
        "effectif": releve["effectif"],
        "matieres": matieres,
        "evolution": evolution,
        "bulletin_disponible": bool(eleve.classe and est_publie(eleve.classe, periode)),
    }


def dernieres_notes(eleve, n=5):
    sortie = []
    for note in (
        Note.objects.filter(eleve=eleve, evaluation__publiee=True)
        .select_related("evaluation__enseignement__matiere")
        .order_by("-evaluation__date", "-pk")[:n]
    ):
        ev = note.evaluation
        sortie.append({
            "id": note.pk,
            "matiere": ev.enseignement.matiere.nom,
            "couleur": ev.enseignement.matiere.couleur,
            "titre": ev.titre,
            "date": ev.date.isoformat(),
            "note": dec(note.valeur),
            "bareme": dec(ev.bareme),
            "statut": note.statut,
            "sur20": dec(calculs.sur_20(note.valeur, ev.bareme)) if note.valeur is not None else None,
        })
    return sortie


# ---------------------------------------------------------------------------
# Devoirs
# ---------------------------------------------------------------------------
def devoirs_eleve(eleve, depuis_jours=14):
    if not eleve.classe:
        return []
    aujourd_hui = timezone.localdate()
    qs = (
        Devoir.objects.filter(enseignement__classe=eleve.classe, pour_le__gte=aujourd_hui - timedelta(days=depuis_jours))
        .select_related("enseignement__matiere", "enseignement__enseignant")
        .order_by("pour_le")
    )
    suivis = {d.devoir_id: d.statut for d in DevoirFait.objects.filter(eleve=eleve, devoir__in=qs)}
    sortie = []
    for d in qs:
        suivi = suivis.get(d.pk)
        if suivi == DevoirFait.Statut.TERMINE:
            statut = "termine"
        elif d.pour_le < aujourd_hui:
            statut = "en_retard"
        elif suivi == DevoirFait.Statut.EN_COURS:
            statut = "en_cours"
        else:
            statut = "a_faire"
        sortie.append({
            "id": d.pk,
            "matiere": d.enseignement.matiere.nom,
            "couleur": d.enseignement.matiere.couleur,
            "enseignant": str(d.enseignement.enseignant),
            "enseignant_id": d.enseignement.enseignant_id,
            "titre": d.titre,
            "description": d.description,
            "donne_le": d.donne_le.isoformat(),
            "pour_le": d.pour_le.isoformat(),
            "duree_estimee": d.duree_estimee,
            "piece_jointe": bool(d.piece_jointe),
            "statut": statut,
        })
    return sortie


# ---------------------------------------------------------------------------
# Absences
# ---------------------------------------------------------------------------
def absences_eleve(eleve):
    qs = Absence.objects.filter(eleve=eleve).select_related("creneau__enseignement__matiere")
    annee_debut = periodes_actives().order_by("debut").first()
    items = []
    for a in qs[:100]:
        if a.creneau_id:
            horaire = f"{a.creneau.heure_debut:%H:%M} – {a.creneau.heure_fin:%H:%M}"
            cours = a.creneau.enseignement.matiere.nom
        else:
            horaire, cours = "Journée", "Tous les cours"
        items.append({
            "id": a.pk,
            "date": a.date.isoformat(),
            "horaire": horaire,
            "cours": cours,
            "type": a.type,
            "minutes": a.minutes_retard,
            "statut": a.statut,
            "motif": a.motif or "",
            "justificatif": bool(a.justificatif),
            "commentaire_admin": a.commentaire_admin,
            "justifiable": a.est_justifiable,
        })
    mensuel = []
    if annee_debut:
        d = annee_debut.debut.replace(day=1)
        fin = timezone.localdate()
        while d <= fin:
            mois = qs.filter(date__year=d.year, date__month=d.month)
            mensuel.append({
                "mois": f"{MOIS[d.month - 1]} {d.year}",
                "absences": mois.filter(type=Absence.Type.ABSENCE).count(),
                "retards": mois.filter(type=Absence.Type.RETARD).count(),
            })
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    p = periode_courante()
    stats = statistiques(qs.filter(date__gte=p.debut, date__lte=p.fin) if p else qs)
    return {"stats": stats, "items": items, "mensuel": mensuel}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
TYPE_CATEGORIE = {
    Notification.Type.NOTE: "resultats",
    Notification.Type.BULLETIN: "resultats",
    Notification.Type.ABSENCE: "absences",
    Notification.Type.DEVOIR: "devoirs",
    Notification.Type.EDT: "edt",
    Notification.Type.ANNONCE: "administration",
    Notification.Type.MESSAGE: "messages",
}


def notification_json(n):
    titre = n.titre.lower()
    categorie = TYPE_CATEGORIE.get(n.type, "administration")
    if "paiement" in titre or "tranche" in titre or "frais" in titre:
        categorie = "paiements"
    priorite = 1 if (n.importante and n.type == Notification.Type.ABSENCE) else 2 if n.importante else 3
    return {
        "id": n.pk,
        "type": n.type,
        "categorie": categorie,
        "priorite": priorite,
        "titre": n.titre,
        "lien": n.lien,
        "lue": n.lue,
        "date": n.cree_le.isoformat(),
    }


def notifications_importantes(user, n=3):
    return [notification_json(x) for x in Notification.objects.filter(destinataire=user, lue=False).filter(Q(importante=True) | Q(type=Notification.Type.ABSENCE))[:n]]
