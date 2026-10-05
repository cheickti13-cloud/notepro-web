from django.test import TestCase
from django.urls import reverse

from core.fabrique import MDP, etablissement, utilisateur
from core.fields import PREFIXE
from core.permissions import eleves_visibles, peut_voir_eleve

from .models import User


class AuthentificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()

    def test_mot_de_passe_hache_argon2(self):
        self.assertTrue(self.d.u_eleve1.password.startswith("argon2"))

    def test_connexion_reussie_redirige_vers_accueil(self):
        r = self.client.post(reverse("accounts:login"), {"username": "eleve1", "password": MDP})
        self.assertRedirects(r, reverse("dashboard:index"), fetch_redirect_response=False)

    def test_connexion_echouee_message_generique(self):
        r = self.client.post(reverse("accounts:login"), {"username": "eleve1", "password": "faux"})
        self.assertContains(r, "Identifiant ou mot de passe incorrect")

    def test_page_protegee_sans_connexion(self):
        r = self.client.get(reverse("dashboard:index"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])

    def test_blocage_apres_5_echecs(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "eleve2", "password": "faux"})
        r = self.client.post(reverse("accounts:login"), {"username": "eleve2", "password": MDP})
        self.assertEqual(r.status_code, 429)  # django-axes : verrouillé

    def test_changement_mdp_force(self):
        u = utilisateur("nouveau", User.Role.ELEVE)
        u.doit_changer_mdp = True
        u.save()
        self.client.force_login(u)
        r = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(r, reverse("accounts:changer_mdp"), fetch_redirect_response=False)

    def test_seul_admin_est_staff(self):
        self.assertTrue(self.d.admin.is_staff)
        self.assertFalse(self.d.prof_maths.is_staff)
        self.client.force_login(self.d.prof_maths)
        r = self.client.get("/admin/")
        self.assertNotEqual(r.status_code, 200)

    def test_telephone_chiffre_en_base(self):
        u = self.d.parent1
        u.telephone = "+225 07 00 00 00"
        u.save()
        from django.db import connection

        with connection.cursor() as c:
            c.execute("SELECT telephone FROM accounts_user WHERE id = %s", [u.pk])
            brut = c.fetchone()[0]
        self.assertTrue(brut.startswith(PREFIXE))
        self.assertNotIn("07 00", brut)
        u.refresh_from_db()
        self.assertEqual(u.telephone, "+225 07 00 00 00")

    def test_export_rgpd(self):
        self.client.force_login(self.d.parent1)
        r = self.client.post(reverse("accounts:export"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("enfants", r.json())


class PerimetreAccesTests(TestCase):
    """Le cœur du contrôle d'accès : qui voit quel élève."""

    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()

    def test_parent_voit_ses_enfants_uniquement(self):
        d = self.d
        self.assertEqual(set(eleves_visibles(d.parent1)), {d.eleve1, d.eleve3})
        self.assertFalse(peut_voir_eleve(d.parent1, d.eleve2))

    def test_eleve_se_voit_lui_meme(self):
        self.assertEqual(list(eleves_visibles(self.d.u_eleve1)), [self.d.eleve1])

    def test_enseignant_voit_ses_classes(self):
        d = self.d
        self.assertEqual(set(eleves_visibles(d.prof_maths)), {d.eleve1, d.eleve2})
        self.assertFalse(peut_voir_eleve(d.prof_maths, d.eleve3))
        self.assertEqual(set(eleves_visibles(d.prof_fr)), {d.eleve1, d.eleve2, d.eleve3})

    def test_admin_voit_tout(self):
        self.assertEqual(eleves_visibles(self.d.admin).count(), 3)
