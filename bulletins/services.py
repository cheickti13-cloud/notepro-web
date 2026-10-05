"""Assemblage des données d'un bulletin à partir des notes, absences et appréciations."""
from django.conf import settings
from django.utils import timezone

from absences.services import stats_eleve
from notes.services import tableau_classe

from .models import Appreciation, AppreciationGenerale, PublicationBulletin


def est_publie(classe, periode):
    return PublicationBulletin.objects.filter(classe=classe, periode=periode).exists()


def _date_naissance_fr(iso):
    try:
        a, m, j = iso.split("-")
        return f"{j}/{m}/{a}"
    except (ValueError, AttributeError):
        return ""


def donnees_bulletins(classe, periode, eleves=None):
    """
    Retourne la liste des bulletins (dictionnaires prêts pour le PDF ou l'écran)
    des élèves demandés (par défaut toute la classe). Les moyennes de classe et
    les rangs sont toujours calculés sur la classe entière.
    """
    tous = list(classe.eleves.select_related("user").order_by("user__last_name", "user__first_name"))
    cibles = tous if eleves is None else [e for e in tous if e.pk in {x.pk for x in eleves}]
    t = tableau_classe(classe, periode, tous, publiees_seulement=True)

    appreciations = {
        (a.eleve_id, a.enseignement_id): a.texte
        for a in Appreciation.objects.filter(periode=periode, enseignement__classe=classe)
    }
    generales = {a.eleve_id: a for a in AppreciationGenerale.objects.filter(periode=periode, eleve__classe=classe)}
    genere_le = timezone.localdate().strftime("%d/%m/%Y")

    resultat = []
    for e in cibles:
        g = generales.get(e.pk)
        resultat.append({
            "eleve_id": e.pk,
            "etablissement": settings.ETABLISSEMENT_NOM,
            "periode": periode.nom,
            "annee": periode.annee.libelle,
            "eleve": f"{e.user.first_name} {e.user.last_name.upper()}",
            "classe": classe.nom,
            "effectif": len(tous),
            "professeur_principal": str(classe.professeur_principal) if classe.professeur_principal else "",
            "date_naissance": _date_naissance_fr(e.date_naissance),
            "matieres": [
                {
                    "matiere": ens.matiere.nom,
                    "enseignant": str(ens.enseignant),
                    "coefficient": ens.coefficient,
                    "moyenne": t.moyennes[e.pk][ens.pk],
                    "moyenne_classe": t.stats_matieres[ens.pk]["moyenne"],
                    "min": t.stats_matieres[ens.pk]["min"],
                    "max": t.stats_matieres[ens.pk]["max"],
                    "appreciation": appreciations.get((e.pk, ens.pk), ""),
                }
                for ens in t.enseignements
            ],
            "moyenne_generale": t.generales[e.pk],
            "moyenne_generale_classe": t.stats_generale["moyenne"],
            "min_general": t.stats_generale["min"],
            "max_general": t.stats_generale["max"],
            "rang": t.rangs[e.pk],
            "absences": stats_eleve(e, periode.debut, periode.fin),
            "appreciation_generale": g.texte if g else "",
            "mention": g.get_mention_display() if g and g.mention else "",
            "genere_le": genere_le,
        })
    return resultat
