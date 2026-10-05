from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.fabrique import creneau, etablissement
from messagerie.models import Notification

from .models import ModificationCours
from .services import construire_semaine, creneaux_classe, creneaux_enseignant

LUNDI = date(2026, 10, 5)  # un lundi


class EmploiDuTempsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        cls.c_maths = creneau(cls.d.ens_maths_a, jour=0, debut=(8, 0), fin=(9, 0), salle=cls.d.salle1)
        cls.c_fr = creneau(cls.d.ens_fr_a, jour=0, debut=(9, 0), fin=(10, 0), salle=cls.d.salle1)

    def test_conflit_classe_detecte(self):
        from edt.models import Creneau

        doublon = Creneau(enseignement=self.d.ens_fr_a, jour=0, heure_debut="08:30", heure_fin="09:30")
        with self.assertRaises(ValidationError):
            doublon.full_clean()

    def test_conflit_salle_detecte(self):
        from edt.models import Creneau

        autre = Creneau(enseignement=self.d.ens_fr_b, jour=0, heure_debut="08:00", heure_fin="09:00", salle=self.d.salle1)
        with self.assertRaises(ValidationError):
            autre.full_clean()

    def test_semaine_classe(self):
        jours = construire_semaine(creneaux_classe(self.d.classe_a), LUNDI)
        self.assertEqual(len(jours), 5)
        self.assertEqual([c.matiere for c in jours[0]["cours"]], [self.d.maths, self.d.francais])

    def test_annulation_et_changement_de_salle(self):
        ModificationCours.objects.create(creneau=self.c_maths, date=LUNDI, type="ANNULATION")
        ModificationCours.objects.create(creneau=self.c_fr, date=LUNDI, type="SALLE", nouvelle_salle=self.d.salle2)
        cours = construire_semaine(creneaux_classe(self.d.classe_a), LUNDI)[0]["cours"]
        self.assertTrue(cours[0].annule)
        self.assertEqual(cours[1].salle, self.d.salle2)
        # La semaine suivante n'est pas affectée
        cours_suiv = construire_semaine(creneaux_classe(self.d.classe_a), date(2026, 10, 12))[0]["cours"]
        self.assertFalse(cours_suiv[0].annule)

    def test_remplacant_voit_le_cours(self):
        ModificationCours.objects.create(creneau=self.c_maths, date=LUNDI, type="REMPLACEMENT", remplacant=self.d.prof_fr)
        jours = construire_semaine(creneaux_enseignant(self.d.prof_fr), LUNDI, remplacant=self.d.prof_fr)
        self.assertIn(self.d.maths, [c.matiere for c in jours[0]["cours"]])

    def test_date_incoherente_avec_le_jour(self):
        m = ModificationCours(creneau=self.c_maths, date=date(2026, 10, 6), type="ANNULATION")  # mardi
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_modification_notifie_eleves_et_parents(self):
        self.client.force_login(self.d.admin)
        r = self.client.post(reverse("edt:modifications"), {"creneau": self.c_maths.pk, "date": LUNDI, "type": "ANNULATION"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Notification.objects.filter(destinataire=self.d.u_eleve1).exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.d.parent1).exists())
        self.assertFalse(Notification.objects.filter(destinataire=self.d.u_eleve3).exists())

    def test_acces_classe_refuse_a_un_autre_eleve(self):
        self.client.force_login(self.d.u_eleve3)  # élève de 3e B
        r = self.client.get(reverse("edt:classe", args=[self.d.classe_a.pk]))
        self.assertEqual(r.status_code, 403)

    def test_parent_ne_voit_pas_edt_d_un_autre_enfant(self):
        self.client.force_login(self.d.parent2)
        r = self.client.get(reverse("edt:eleve", args=[self.d.eleve1.pk]))
        self.assertEqual(r.status_code, 403)

    def test_eleve_ne_peut_pas_modifier(self):
        self.client.force_login(self.d.u_eleve1)
        r = self.client.get(reverse("edt:modifications"))
        self.assertEqual(r.status_code, 403)
