"""Tests du module pur de calcul des moyennes (exécutables sans base de données)."""
import unittest
from decimal import Decimal as D

from notes.calculs import (
    ABSENT, DISPENSE, NON_RENDU, NotePonderee, moyenne_generale, moyenne_matiere, rangs, statistiques,
)


class MoyenneMatiereTests(unittest.TestCase):
    def test_moyenne_simple(self):
        self.assertEqual(moyenne_matiere([NotePonderee(D("12"), D("20"), D("1")), NotePonderee(D("16"), D("20"), D("1"))]), D("14.00"))

    def test_bareme_different_ramene_sur_20(self):
        # 8/10 = 16/20 ; 30/40 = 15/20
        self.assertEqual(moyenne_matiere([NotePonderee(D("8"), D("10"), D("1")), NotePonderee(D("30"), D("40"), D("1"))]), D("15.50"))

    def test_coefficients_evaluations(self):
        # (10×1 + 16×2) / 3 = 14
        self.assertEqual(moyenne_matiere([NotePonderee(D("10"), D("20"), D("1")), NotePonderee(D("16"), D("20"), D("2"))]), D("14.00"))

    def test_absent_et_dispense_exclus(self):
        notes = [NotePonderee(D("14"), D("20"), D("1")), NotePonderee(None, D("20"), D("1"), ABSENT), NotePonderee(None, D("20"), D("3"), DISPENSE)]
        self.assertEqual(moyenne_matiere(notes), D("14.00"))

    def test_non_rendu_compte_zero(self):
        notes = [NotePonderee(D("14"), D("20"), D("1")), NotePonderee(None, D("20"), D("1"), NON_RENDU)]
        self.assertEqual(moyenne_matiere(notes), D("7.00"))

    def test_aucune_note(self):
        self.assertIsNone(moyenne_matiere([]))
        self.assertIsNone(moyenne_matiere([NotePonderee(None, D("20"), D("1"), ABSENT)]))

    def test_coefficient_nul_ignore(self):
        self.assertEqual(moyenne_matiere([NotePonderee(D("5"), D("20"), D("0")), NotePonderee(D("15"), D("20"), D("1"))]), D("15.00"))

    def test_arrondi_au_centieme(self):
        # (10 + 11 + 11) / 3 = 10,666... -> 10,67
        notes = [NotePonderee(D(v), D("20"), D("1")) for v in ("10", "11", "11")]
        self.assertEqual(moyenne_matiere(notes), D("10.67"))

    def test_bareme_invalide(self):
        with self.assertRaises(ValueError):
            moyenne_matiere([NotePonderee(D("5"), D("0"), D("1"))])


class MoyenneGeneraleTests(unittest.TestCase):
    def test_ponderee_par_coefficient_matiere(self):
        # Maths 12 coef 4, Français 15 coef 3, EPS 18 coef 1 -> (48+45+18)/8 = 13,875 -> 13,88
        self.assertEqual(moyenne_generale([(D("12"), D("4")), (D("15"), D("3")), (D("18"), D("1"))]), D("13.88"))

    def test_matiere_sans_note_ignoree(self):
        self.assertEqual(moyenne_generale([(D("12"), D("4")), (None, D("3"))]), D("12.00"))

    def test_rien(self):
        self.assertIsNone(moyenne_generale([(None, D("2"))]))


class StatistiquesEtRangsTests(unittest.TestCase):
    def test_stats(self):
        s = statistiques([D("10"), None, D("14"), D("12")])
        self.assertEqual((s["moyenne"], s["min"], s["max"], s["effectif"]), (D("12.00"), D("10"), D("14"), 3))

    def test_rangs_ex_aequo(self):
        r = rangs({"a": D("15"), "b": D("12"), "c": D("15"), "d": None, "e": D("10")})
        self.assertEqual(r, {"a": 1, "c": 1, "b": 3, "e": 4, "d": None})


if __name__ == "__main__":
    unittest.main()
