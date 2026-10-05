from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.fabrique import etablissement
from messagerie.models import Notification

from .models import Devoir, DevoirFait


class CahierDeTexteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        cls.today = timezone.localdate()

    def test_enseignant_cree_devoir_et_notifie(self):
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(reverse("cahier:devoir_creer", args=[self.d.ens_maths_a.pk]), {
            "donne_le": self.today, "pour_le": self.today + timedelta(days=2), "titre": "Exercices 1 à 5",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Devoir.objects.filter(titre="Exercices 1 à 5").exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.d.u_eleve1, type="DEVOIR").exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.d.parent2, type="DEVOIR").exists())
        self.assertFalse(Notification.objects.filter(destinataire=self.d.u_eleve3, type="DEVOIR").exists())

    def test_echeance_avant_date_donnee_refusee(self):
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(reverse("cahier:devoir_creer", args=[self.d.ens_maths_a.pk]), {
            "donne_le": self.today, "pour_le": self.today - timedelta(days=1), "titre": "X",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Devoir.objects.exists())

    def test_autre_enseignant_refuse(self):
        self.client.force_login(self.d.prof_fr)
        self.assertEqual(self.client.get(reverse("cahier:devoir_creer", args=[self.d.ens_maths_a.pk])).status_code, 403)

    def test_eleve_voit_devoirs_de_sa_classe_et_coche_fait(self):
        dv = Devoir.objects.create(enseignement=self.d.ens_maths_a, donne_le=self.today, pour_le=self.today + timedelta(days=1), titre="Lire chapitre 3")
        autre = Devoir.objects.create(enseignement=self.d.ens_fr_b, donne_le=self.today, pour_le=self.today + timedelta(days=1), titre="Devoir 3e B")
        self.client.force_login(self.d.u_eleve1)
        r = self.client.get(reverse("cahier:index"))
        self.assertContains(r, "Lire chapitre 3")
        self.assertNotContains(r, "Devoir 3e B")
        self.client.post(reverse("cahier:basculer_fait", args=[dv.pk]))
        self.assertTrue(DevoirFait.objects.filter(devoir=dv, eleve=self.d.eleve1).exists())
        # Impossible de cocher un devoir d'une autre classe
        self.assertEqual(self.client.post(reverse("cahier:basculer_fait", args=[autre.pk])).status_code, 403)

    def test_parent_voit_devoirs_de_l_enfant_choisi(self):
        Devoir.objects.create(enseignement=self.d.ens_fr_b, donne_le=self.today, pour_le=self.today + timedelta(days=1), titre="Devoir 3e B")
        self.client.force_login(self.d.parent1)
        r = self.client.get(reverse("cahier:index") + f"?eleve={self.d.eleve3.pk}")
        self.assertContains(r, "Devoir 3e B")
