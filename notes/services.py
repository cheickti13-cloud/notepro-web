"""
Agrégation des notes d'une classe sur une période.

Toutes les moyennes d'une classe sont calculées en 3 requêtes (enseignements,
évaluations, notes) puis en mémoire avec `calculs` — pas de requête par élève.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from scolarite.models import Enseignement

from . import calculs
from .models import Evaluation, Note


@dataclass
class TableauClasse:
    enseignements: list
    evaluations: dict  # enseignement_id -> [Evaluation]
    notes: dict  # (evaluation_id, eleve_id) -> Note
    moyennes: dict  # eleve_id -> {enseignement_id: Decimal|None}
    generales: dict  # eleve_id -> Decimal|None
    rangs: dict  # eleve_id -> int|None
    stats_matieres: dict  # enseignement_id -> {moyenne, min, max}
    stats_generale: dict = field(default_factory=dict)


def tableau_classe(classe, periode, eleves, publiees_seulement=True) -> TableauClasse:
    enseignements = list(
        Enseignement.objects.filter(classe=classe).select_related("matiere", "enseignant").order_by("matiere__nom")
    )
    evals_qs = Evaluation.objects.filter(enseignement__classe=classe, periode=periode)
    if publiees_seulement:
        evals_qs = evals_qs.filter(publiee=True)
    evaluations = defaultdict(list)
    for ev in evals_qs.order_by("date", "pk"):
        evaluations[ev.enseignement_id].append(ev)
    ids_eleves = [e.pk for e in eleves]
    notes = {
        (n.evaluation_id, n.eleve_id): n
        for n in Note.objects.filter(evaluation__in=evals_qs, eleve_id__in=ids_eleves)
    }

    moyennes, generales = {}, {}
    for eid in ids_eleves:
        moyennes[eid] = {}
        for ens in enseignements:
            ponderees = [
                calculs.NotePonderee(n.valeur, ev.bareme, ev.coefficient, n.statut)
                for ev in evaluations.get(ens.pk, [])
                if (n := notes.get((ev.pk, eid))) is not None
            ]
            moyennes[eid][ens.pk] = calculs.moyenne_matiere(ponderees)
        generales[eid] = calculs.moyenne_generale(
            (moyennes[eid][ens.pk], ens.coefficient) for ens in enseignements
        )

    stats_matieres = {
        ens.pk: calculs.statistiques(moyennes[eid][ens.pk] for eid in ids_eleves) for ens in enseignements
    }
    return TableauClasse(
        enseignements=enseignements,
        evaluations=dict(evaluations),
        notes=notes,
        moyennes=moyennes,
        generales=generales,
        rangs=calculs.rangs(generales),
        stats_matieres=stats_matieres,
        stats_generale=calculs.statistiques(generales.values()),
    )


def releve_eleve(eleve, periode, publiees_seulement=True):
    """Relevé de notes d'un élève : lignes par matière + moyennes et position dans la classe."""
    if eleve.classe is None or periode is None:
        return None
    eleves_classe = list(eleve.classe.eleves.all())
    t = tableau_classe(eleve.classe, periode, eleves_classe, publiees_seulement)
    lignes = []
    for ens in t.enseignements:
        evals = [
            {"evaluation": ev, "note": t.notes.get((ev.pk, eleve.pk))}
            for ev in t.evaluations.get(ens.pk, [])
        ]
        lignes.append(
            {
                "enseignement": ens,
                "evaluations": evals,
                "moyenne": t.moyennes[eleve.pk][ens.pk],
                "stats": t.stats_matieres[ens.pk],
            }
        )
    return {
        "lignes": lignes,
        "moyenne_generale": t.generales[eleve.pk],
        "rang": t.rangs[eleve.pk],
        "effectif": len(eleves_classe),
        "stats_generale": t.stats_generale,
    }


def dernieres_notes(eleve, limite=5):
    return (
        Note.objects.filter(eleve=eleve, evaluation__publiee=True)
        .select_related("evaluation__enseignement__matiere")
        .order_by("-evaluation__date", "-pk")[:limite]
    )


def moyenne_evaluation(evaluation) -> Decimal | None:
    return calculs.statistiques(n.sur_20 for n in evaluation.notes.all())["moyenne"]
