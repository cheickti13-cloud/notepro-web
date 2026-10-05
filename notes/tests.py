from datetime import date
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.fabrique import etablissement
from messagerie.models import Notification

from .models import Evaluation, Note
from .services import releve_eleve


class CarnetDeNotesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        d = cls.d = etablissement()
        cls.ev_maths = Evaluation.objects.create(enseignement=d.ens_maths_a, periode=d.t1, titre="DS1", date=date(2026, 10, 1), bareme=D("20"), coefficient=D("1"))
        cls.ev_maths2 = Evaluation.objects.create(enseignement=d.ens_maths_a, periode=d.t1, titre="Interro", date=date(2026, 10, 8), bareme=D("10"), coefficient=D("2"))
        cls.ev_fr = Evaluation.objects.create(enseignement=d.ens_fr_a, periode=d.t1, titre="Dictée", date=date(2026, 10, 2))
        Note.objects.create(evaluation=cls.ev_maths, eleve=d.eleve1, valeur=D("12"))
        Note.objects.create(evaluation=cls.ev_maths2, eleve=d.eleve1, valeur=D("8"))  # 16/20 coef 2
        Note.objects.create(evaluation=cls.ev_fr, eleve=d.eleve1, valeur=D("10"))
        Note.objects.create(evaluation=cls.ev_maths, eleve=d.eleve2, valeur=D("18"))
        Note.objects.create(evaluation=cls.ev_fr, eleve=d.eleve2, valeur=D("14"))

    def test_moyennes_releve(self):
        r = releve_eleve(self.d.eleve1, self.d.t1)
        par_matiere = {l["enseignement"].matiere.code: l["moyenne"] for l in r["lignes"]}
        # Maths : (12×1 + 16×2)/3 = 14,67 ; Français : 10
        self.assertEqual(par_matiere["MATH"], D("14.67"))
        self.assertEqual(par_matiere["FR"], D("10.00"))
        # Générale : (14,67×4 + 10×3)/7 = 12,67
        self.assertEqual(r["moyenne_generale"], D("12.67"))
        self.assertEqual(r["rang"], 2)  # eleve2 : (18×4 + 14×3)/7 = 16,29

    def test_evaluation_non_publiee_invisible(self):
        self.ev_fr.publiee = False
        self.ev_fr.save()
        r = releve_eleve(self.d.eleve1, self.d.t1)
        fr = next(l for l in r["lignes"] if l["enseignement"].matiere.code == "FR")
        self.assertIsNone(fr["moyenne"])

    def test_note_superieure_au_bareme_refusee(self):
        n = Note(evaluation=self.ev_maths2, eleve=self.d.eleve2, valeur=D("12"))
        with self.assertRaises(ValidationError):
            n.full_clean()

    def test_eleve_hors_classe_refuse(self):
        n = Note(evaluation=self.ev_maths, eleve=self.d.eleve3, valeur=D("12"))
        with self.assertRaises(ValidationError):
            n.full_clean()

    def test_saisie_grille_par_enseignant(self):
        ev = Evaluation.objects.create(enseignement=self.d.ens_maths_a, periode=self.d.t1, titre="DS2", date=date(2026, 11, 5))
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(reverse("notes:saisie", args=[ev.pk]), {
            f"note_{self.d.eleve1.pk}": "13,5", f"statut_{self.d.eleve1.pk}": "NOTEE",
            f"note_{self.d.eleve2.pk}": "", f"statut_{self.d.eleve2.pk}": "ABSENT",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Note.objects.get(evaluation=ev, eleve=self.d.eleve1).valeur, D("13.5"))
        self.assertEqual(Note.objects.get(evaluation=ev, eleve=self.d.eleve2).statut, "ABSENT")
        # Élève et parent notifiés, sans la note dans le titre
        notif = Notification.objects.get(destinataire=self.d.parent1, type="NOTE")
        self.assertNotIn("13", notif.titre)

    def test_saisie_invalide_n_enregistre_rien(self):
        ev = Evaluation.objects.create(enseignement=self.d.ens_maths_a, periode=self.d.t1, titre="DS3", date=date(2026, 11, 6))
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(reverse("notes:saisie", args=[ev.pk]), {
            f"note_{self.d.eleve1.pk}": "15", f"note_{self.d.eleve2.pk}": "25",  # 25 > 20
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Note.objects.filter(evaluation=ev).exists())

    def test_autre_enseignant_ne_peut_pas_saisir(self):
        self.client.force_login(self.d.prof_fr)
        r = self.client.get(reverse("notes:saisie", args=[self.ev_maths.pk]))
        self.assertEqual(r.status_code, 403)

    def test_eleve_ne_peut_pas_saisir(self):
        self.client.force_login(self.d.u_eleve1)
        self.assertEqual(self.client.get(reverse("notes:saisie", args=[self.ev_maths.pk])).status_code, 403)

    def test_parent_voit_releve_de_son_enfant_seulement(self):
        self.client.force_login(self.d.parent2)
        self.assertEqual(self.client.get(reverse("notes:releve")).status_code, 200)
        r = self.client.get(reverse("notes:releve") + f"?eleve={self.d.eleve1.pk}")
        self.assertEqual(r.status_code, 403)

    def test_eleve_ne_peut_pas_voir_un_autre_eleve(self):
        self.client.force_login(self.d.u_eleve1)
        r = self.client.get(reverse("notes:releve") + f"?eleve={self.d.eleve2.pk}")
        self.assertEqual(r.status_code, 403)
