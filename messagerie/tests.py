from django.test import TestCase
from django.urls import reverse

from core.fabrique import etablissement

from .models import Annonce, Conversation, Notification
from .services import destinataires_autorises, nb_messages_non_lus, publier_annonce


class MessagerieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()

    def test_perimetre_destinataires(self):
        d = self.d
        eleve = set(destinataires_autorises(d.u_eleve1))
        self.assertIn(d.prof_maths, eleve)
        self.assertIn(d.admin, eleve)
        self.assertNotIn(d.u_eleve2, eleve)  # pas de messagerie entre élèves
        parent = set(destinataires_autorises(d.parent2))
        self.assertIn(d.prof_maths, parent)
        self.assertNotIn(d.parent1, parent)
        prof = set(destinataires_autorises(d.prof_maths))
        self.assertIn(d.parent1, prof)
        self.assertNotIn(d.u_eleve3, prof)  # pas d'élève hors de ses classes

    def test_envoi_lecture_et_notification(self):
        d = self.d
        self.client.force_login(d.parent2)
        r = self.client.post(reverse("messagerie:nouveau"), {"destinataires": [d.prof_maths.pk], "sujet": "RDV", "corps": "Bonjour"})
        conv = Conversation.objects.get(sujet="RDV")
        self.assertRedirects(r, reverse("messagerie:conversation", args=[conv.pk]), fetch_redirect_response=False)
        self.assertEqual(nb_messages_non_lus(d.prof_maths), 1)
        self.assertEqual(nb_messages_non_lus(d.parent2), 0)
        self.assertTrue(Notification.objects.filter(destinataire=d.prof_maths, type="MESSAGE").exists())
        self.client.force_login(d.prof_maths)
        self.client.get(reverse("messagerie:conversation", args=[conv.pk]))
        self.assertEqual(nb_messages_non_lus(d.prof_maths), 0)

    def test_destinataire_non_autorise_refuse(self):
        self.client.force_login(self.d.u_eleve1)
        self.client.post(reverse("messagerie:nouveau"), {"destinataires": [self.d.u_eleve2.pk], "sujet": "X", "corps": "Y"})
        self.assertFalse(Conversation.objects.exists())

    def test_conversation_privee(self):
        d = self.d
        self.client.force_login(d.parent2)
        self.client.post(reverse("messagerie:nouveau"), {"destinataires": [d.prof_maths.pk], "sujet": "Privé", "corps": "..."})
        conv = Conversation.objects.get(sujet="Privé")
        self.client.force_login(d.parent1)
        self.assertEqual(self.client.get(reverse("messagerie:conversation", args=[conv.pk])).status_code, 403)

    def test_annonce_ciblee(self):
        a = Annonce.objects.create(titre="Réunion parents 3e A", contenu="...", pour_eleves=False, pour_enseignants=False, classe=self.d.classe_a)
        publier_annonce(a)
        self.assertTrue(Notification.objects.filter(destinataire=self.d.parent2, type="ANNONCE").exists())
        self.assertFalse(Notification.objects.filter(destinataire=self.d.u_eleve1, type="ANNONCE").exists())

    def test_notification_lien_externe_ignore(self):
        n = Notification.objects.create(destinataire=self.d.u_eleve1, type="ANNONCE", titre="x", lien="https://pirate.example/")
        self.client.force_login(self.d.u_eleve1)
        r = self.client.post(reverse("messagerie:ouvrir_notification", args=[n.pk]))
        self.assertEqual(r["Location"], reverse("messagerie:notifications"))
