from django.test import TestCase
from django.urls import reverse

from core.fabrique import creneau, etablissement


class TableauDeBordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        creneau(cls.d.ens_maths_a, jour=0)

    def test_chaque_role_a_son_tableau_de_bord(self):
        attendus = {
            self.d.u_eleve1: "dashboard/famille.html",
            self.d.parent1: "dashboard/famille.html",
            self.d.prof_maths: "dashboard/enseignant.html",
            self.d.admin: "dashboard/admin.html",
        }
        for user, gabarit in attendus.items():
            with self.subTest(user=user.username):
                self.client.force_login(user)
                r = self.client.get(reverse("dashboard:index"))
                self.assertEqual(r.status_code, 200)
                self.assertTemplateUsed(r, gabarit)

    def test_parent_voit_tous_ses_enfants(self):
        self.client.force_login(self.d.parent1)
        r = self.client.get(reverse("dashboard:index"))
        self.assertEqual(len(r.context["resumes"]), 2)
        self.assertContains(r, "Ali")
        self.assertContains(r, "Cheick")
        self.assertNotContains(r, "Binta")


class FumeeTests(TestCase):
    """Test de fumée : toutes les pages principales répondent pour chaque rôle (pas d'erreur 500)."""

    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        creneau(cls.d.ens_maths_a, jour=0)

    def test_pages(self):
        urls = [
            reverse("dashboard:index"), reverse("edt:mon_edt"), reverse("notes:releve"), reverse("absences:mes_absences"),
            reverse("cahier:index"), reverse("bulletins:index"), reverse("messagerie:boite"), reverse("messagerie:nouveau"),
            reverse("messagerie:notifications"), reverse("messagerie:annonces"), reverse("accounts:mon_compte"),
        ]
        for user in [self.d.u_eleve1, self.d.parent1, self.d.prof_maths, self.d.admin]:
            self.client.force_login(user)
            for url in urls:
                with self.subTest(user=user.username, url=url):
                    r = self.client.get(url, follow=True)
                    self.assertIn(r.status_code, (200, 403))
