from datetime import date
from decimal import Decimal as D

from django.test import TestCase
from django.urls import reverse

from core.fabrique import etablissement
from messagerie.models import Notification
from notes.models import Evaluation, Note

from .models import Appreciation, AppreciationGenerale, PublicationBulletin
from .services import donnees_bulletins


class BulletinsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        d = cls.d = etablissement()
        ev = Evaluation.objects.create(enseignement=d.ens_maths_a, periode=d.t1, titre="DS1", date=date(2026, 10, 1))
        Note.objects.create(evaluation=ev, eleve=d.eleve1, valeur=D("15"))
        Note.objects.create(evaluation=ev, eleve=d.eleve2, valeur=D("9"))
        Appreciation.objects.create(eleve=d.eleve1, enseignement=d.ens_maths_a, periode=d.t1, texte="Très bien")
        AppreciationGenerale.objects.create(eleve=d.eleve1, periode=d.t1, texte="Bon trimestre", mention="COMPLIMENTS")

    def test_donnees_bulletin(self):
        b = donnees_bulletins(self.d.classe_a, self.d.t1, eleves=[self.d.eleve1])[0]
        maths = next(m for m in b["matieres"] if m["matiere"] == "Mathématiques")
        self.assertEqual(maths["moyenne"], D("15.00"))
        self.assertEqual(maths["moyenne_classe"], D("12.00"))
        self.assertEqual(maths["appreciation"], "Très bien")
        self.assertEqual(b["rang"], 1)
        self.assertEqual(b["mention"], "Compliments")

    def test_pdf_genere(self):
        self.client.force_login(self.d.admin)
        r = self.client.get(reverse("bulletins:pdf_classe", args=[self.d.classe_a.pk, self.d.t1.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_famille_attend_la_publication(self):
        url = reverse("bulletins:pdf_eleve", args=[self.d.eleve1.pk, self.d.t1.pk])
        self.client.force_login(self.d.parent1)
        self.assertEqual(self.client.get(url).status_code, 403)
        PublicationBulletin.objects.create(classe=self.d.classe_a, periode=self.d.t1)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_parent_ne_telecharge_pas_le_bulletin_d_un_autre(self):
        PublicationBulletin.objects.create(classe=self.d.classe_a, periode=self.d.t1)
        self.client.force_login(self.d.parent2)
        r = self.client.get(reverse("bulletins:pdf_eleve", args=[self.d.eleve1.pk, self.d.t1.pk]))
        self.assertEqual(r.status_code, 403)

    def test_publication_notifie(self):
        self.client.force_login(self.d.admin)
        self.client.post(reverse("bulletins:publier", args=[self.d.classe_a.pk, self.d.t1.pk]))
        self.assertTrue(PublicationBulletin.objects.filter(classe=self.d.classe_a).exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.d.parent1, type="BULLETIN").exists())

    def test_conseil_reserve_au_professeur_principal(self):
        self.client.force_login(self.d.prof_fr)
        self.assertEqual(self.client.get(reverse("bulletins:conseil", args=[self.d.classe_a.pk])).status_code, 403)
        self.client.force_login(self.d.prof_maths)  # professeur principal de 3e A
        self.assertEqual(self.client.get(reverse("bulletins:conseil", args=[self.d.classe_a.pk]) + f"?periode={self.d.t1.pk}").status_code, 200)

    def test_saisie_appreciation_par_enseignant(self):
        self.client.force_login(self.d.prof_fr)
        url = reverse("bulletins:appreciations", args=[self.d.ens_fr_a.pk]) + f"?periode={self.d.t1.pk}"
        self.client.post(url, {f"app_{self.d.eleve2.pk}": "Des progrès"})
        self.assertTrue(Appreciation.objects.filter(eleve=self.d.eleve2, enseignement=self.d.ens_fr_a, texte="Des progrès").exists())
