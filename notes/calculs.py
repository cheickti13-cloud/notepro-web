"""
Calcul des moyennes — module PUR (aucune dépendance à Django ni à la base),
pour pouvoir être testé isolément et réutilisé partout (relevé, bulletin...).

Règles :
- Chaque note est ramenée sur 20 : valeur / barème × 20.
- Moyenne d'une matière = Σ(note/20 × coef évaluation) / Σ(coef évaluation).
- Moyenne générale = Σ(moyenne matière × coef matière) / Σ(coef matière),
  en ignorant les matières sans note (et les coefficients nuls).
- Statuts : ABSENT et DISPENSE sont exclus du calcul ; NON_RENDU compte 0.
- Arrondi au centième, arrondi commercial (0,005 → 0,01).
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional

VINGT = Decimal("20")
CENTIEME = Decimal("0.01")

NOTEE = "NOTEE"
ABSENT = "ABSENT"
DISPENSE = "DISPENSE"
NON_RENDU = "NON_RENDU"
STATUTS_EXCLUS = {ABSENT, DISPENSE}


@dataclass(frozen=True)
class NotePonderee:
    valeur: Optional[Decimal]
    bareme: Decimal
    coefficient: Decimal
    statut: str = NOTEE


def arrondir(x: Decimal) -> Decimal:
    return x.quantize(CENTIEME, rounding=ROUND_HALF_UP)


def sur_20(valeur: Decimal, bareme: Decimal) -> Decimal:
    if bareme <= 0:
        raise ValueError("Le barème doit être strictement positif.")
    return Decimal(valeur) / Decimal(bareme) * VINGT


def moyenne_matiere(notes: Iterable[NotePonderee]) -> Optional[Decimal]:
    """Moyenne /20 d'une matière, ou None s'il n'y a aucune note comptabilisée."""
    total = Decimal("0")
    poids = Decimal("0")
    for n in notes:
        if n.statut in STATUTS_EXCLUS or n.coefficient <= 0:
            continue
        if n.statut == NON_RENDU:
            valeur = Decimal("0")
        elif n.valeur is None:
            continue  # pas encore saisie
        else:
            valeur = Decimal(n.valeur)
        total += sur_20(valeur, n.bareme) * Decimal(n.coefficient)
        poids += Decimal(n.coefficient)
    if poids == 0:
        return None
    return arrondir(total / poids)


def moyenne_generale(moyennes: Iterable[tuple[Optional[Decimal], Decimal]]) -> Optional[Decimal]:
    """`moyennes` : couples (moyenne de la matière ou None, coefficient de la matière)."""
    total = Decimal("0")
    poids = Decimal("0")
    for moy, coef in moyennes:
        if moy is None or coef is None or Decimal(coef) <= 0:
            continue
        total += Decimal(moy) * Decimal(coef)
        poids += Decimal(coef)
    if poids == 0:
        return None
    return arrondir(total / poids)


def statistiques(valeurs: Iterable[Optional[Decimal]]) -> dict:
    """Moyenne, minimum et maximum d'une série (valeurs None ignorées)."""
    v = [Decimal(x) for x in valeurs if x is not None]
    if not v:
        return {"moyenne": None, "min": None, "max": None, "effectif": 0}
    return {
        "moyenne": arrondir(sum(v) / len(v)),
        "min": min(v),
        "max": max(v),
        "effectif": len(v),
    }


def rangs(moyennes: dict) -> dict:
    """Rang de chaque clé selon sa moyenne décroissante (ex aequo = même rang). None = non classé."""
    classees = sorted(((k, m) for k, m in moyennes.items() if m is not None), key=lambda x: -x[1])
    resultat = {k: None for k in moyennes}
    rang_precedent, moyenne_precedente = 0, None
    for i, (k, m) in enumerate(classees, start=1):
        if m != moyenne_precedente:
            rang_precedent, moyenne_precedente = i, m
        resultat[k] = rang_precedent
    return resultat
