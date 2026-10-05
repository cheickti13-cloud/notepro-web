import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.fabrique import creneau, etablissement
from core.fields import PREFIXE
from core.models import JournalAcces
from edt.models import ModificationCours
from messagerie.models import Notification

from .models import Absence, Appel

LUNDI = date(2026, 10, 5)
DOSSIER_TMP = tempfile.mkdtemp()


@override_settings(PRIVATE_MEDIA_ROOT=DOSSIER_TMP)
class AbsencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        cls.c_maths = creneau(cls.d.ens_maths_a, jour=0)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_TMP, ignore_errors=True)

    def url_appel(self):
        return reverse("absences:appel", args=[self.c_maths.pk, LUNDI.isoformat()])

    def test_appel_par_enseignant(self):
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(self.url_appel(), {
            f"statut_{self.d.eleve1.pk}": "ABSENCE",
            f"statut_{self.d.eleve2.pk}": "RETARD", f"minutes_{self.d.eleve2.pk}": "10",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Absence.objects.get(eleve=self.d.eleve1).type, "ABSENCE")
        self.assertEqual(Absence.objects.get(eleve=self.d.eleve2).minutes_retard, 10)
        self.assertTrue(Appel.objects.filter(creneau=self.c_maths, date=LUNDI).exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.d.parent1, type="ABSENCE").exists())

    def test_correction_appel_supprime_absence_non_justifiee(self):
        self.client.force_login(self.d.prof_maths)
        self.client.post(self.url_appel(), {f"statut_{self.d.eleve1.pk}": "ABSENCE"})
        self.client.post(self.url_appel(), {f"statut_{self.d.eleve1.pk}": "PRESENT"})
        self.assertFalse(Absence.objects.filter(eleve=self.d.eleve1).exists())

    def test_retard_sans_duree_refuse(self):
        self.client.force_login(self.d.prof_maths)
        r = self.client.post(self.url_appel(), {f"statut_{self.d.eleve1.pk}": "RETARD", f"minutes_{self.d.eleve1.pk}": ""})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Absence.objects.exists())

    def test_autre_enseignant_ne_peut_pas_faire_l_appel(self):
        self.client.force_login(self.d.prof_fr)
        self.assertEqual(self.client.get(self.url_appel()).status_code, 403)

    def test_remplacant_fait_l_appel(self):
        ModificationCours.objects.create(creneau=self.c_maths, date=LUNDI, type="REMPLACEMENT", remplacant=self.d.prof_fr)
        self.client.force_login(self.d.prof_fr)
        self.assertEqual(self.client.get(self.url_appel()).status_code, 200)
        self.client.force_login(self.d.prof_maths)
        self.assertEqual(self.client.get(self.url_appel()).status_code, 403)

    def test_justification_parent_avec_document(self):
        a = Absence.objects.create(eleve=self.d.eleve1, date=LUNDI, creneau=self.c_maths)
        self.client.force_login(self.d.parent1)
        pdf = SimpleUploadedFile("certificat.pdf", b"%PDF-1.4 contenu", content_type="application/pdf")
        r = self.client.post(reverse("absences:justifier", args=[a.pk]), {"motif": "Rendez-vous médical", "justificatif": pdf})
        self.assertEqual(r.status_code, 302)
        a.refresh_from_db()
        self.assertEqual(a.statut, "EN_ATTENTE")
        self.assertNotIn("certificat", a.justificatif.name)  # nom d'origine non conservé
        # Motif chiffré en base
        from django.db import connection

        with connection.cursor() as c:
            c.execute("SELECT motif FROM absences_absence WHERE id = %s", [a.pk])
            self.assertTrue(c.fetchone()[0].startswith(PREFIXE))
        self.assertTrue(Notification.objects.filter(destinataire=self.d.admin, type="ABSENCE").exists())

    def test_faux_pdf_refuse(self):
        a = Absence.objects.create(eleve=self.d.eleve1, date=LUNDI, creneau=self.c_maths)
        self.client.force_login(self.d.parent1)
        faux = SimpleUploadedFile("virus.pdf", b"MZ\x90\x00 executable", content_type="application/pdf")
        r = self.client.post(reverse("absences:justifier", args=[a.pk]), {"motif": "Malade", "justificatif": faux})
        self.assertEqual(r.status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.statut, "NON_JUSTIFIEE")

    def test_parent_ne_peut_pas_justifier_pour_un_autre_enfant(self):
        a = Absence.objects.create(eleve=self.d.eleve2, date=LUNDI, creneau=self.c_maths)
        self.client.force_login(self.d.parent1)
        self.assertEqual(self.client.get(reverse("absences:justifier", args=[a.pk])).status_code, 403)

    def test_enseignant_ne_voit_pas_le_justificatif(self):
        a = Absence.objects.create(eleve=self.d.eleve1, date=LUNDI, creneau=self.c_maths)
        a.justificatif = SimpleUploadedFile("x.pdf", b"%PDF-1.4")
        a.save()
        self.client.force_login(self.d.prof_maths)
        self.assertEqual(self.client.get(reverse("absences:justificatif", args=[a.pk])).status_code, 403)
        self.client.force_login(self.d.admin)
        self.assertEqual(self.client.get(reverse("absences:justificatif", args=[a.pk])).status_code, 200)
        self.assertTrue(JournalAcces.objects.filter(action="TELECHARGEMENT").exists())

    def test_validation_admin(self):
        a = Absence.objects.create(eleve=self.d.eleve1, date=LUNDI, creneau=self.c_maths, statut="EN_ATTENTE", justifiee_par=self.d.parent1)
        self.client.force_login(self.d.admin)
        self.client.post(reverse("absences:traiter", args=[a.pk]), {"decision": "JUSTIFIEE"})
        a.refresh_from_db()
        self.assertEqual(a.statut, "JUSTIFIEE")

    def test_vue_admin_reservee(self):
        self.client.force_login(self.d.prof_maths)
        self.assertEqual(self.client.get(reverse("absences:vue_admin")).status_code, 403)
        self.client.force_login(self.d.admin)
        self.assertEqual(self.client.get(reverse("absences:vue_admin") + "?statut=EN_ATTENTE").status_code, 200)
        self.assertEqual(self.client.get(reverse("absences:export_csv")).status_code, 200)
