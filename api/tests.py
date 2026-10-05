from datetime import date
from decimal import Decimal as D

from django.test import TestCase
from rest_framework.test import APIClient

from core.fabrique import MDP, etablissement
from finances.models import FraisScolarite, Paiement
from notes.models import Evaluation, Note


class ApiMobileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = etablissement()
        ev = Evaluation.objects.create(enseignement=cls.d.ens_maths_a, periode=cls.d.t1, titre="DS1", date=date(2026, 10, 1))
        Note.objects.create(evaluation=ev, eleve=cls.d.eleve1, valeur=D("15"))
        cls.frais = FraisScolarite.objects.create(eleve=cls.d.eleve1, annee=cls.d.annee, libelle="1re tranche", montant=150000, echeance=date(2026, 10, 15))

    def client_pour(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_connexion_jwt(self):
        r = APIClient().post("/api/auth/connexion/", {"username": "parent1", "password": MDP}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.json())

    def test_connexion_par_telephone(self):
        u = self.d.parent1
        u.telephone = "+225 07 58 42 18 90"
        u.save()
        r = APIClient().post("/api/auth/connexion/", {"username": "+225 0758421890", "password": MDP}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_sans_jeton_refuse(self):
        self.assertEqual(APIClient().get("/api/moi/").status_code, 401)

    def test_moi_parent_avec_enfants(self):
        r = self.client_pour(self.d.parent1).get("/api/moi/")
        self.assertEqual(len(r.json()["enfants"]), 2)

    def test_parent_ne_voit_pas_un_autre_enfant(self):
        c = self.client_pour(self.d.parent2)
        for url in ("accueil", "notes", "absences", "devoirs", "frais", "emploi-du-temps"):
            with self.subTest(url=url):
                self.assertEqual(c.get(f"/api/eleves/{self.d.eleve1.pk}/{url}/").status_code, 403)

    def test_notes(self):
        r = self.client_pour(self.d.u_eleve1).get(f"/api/eleves/{self.d.eleve1.pk}/notes/?periode={self.d.t1.pk}")
        self.assertEqual(r.status_code, 200)
        maths = next(m for m in r.json()["matieres"] if m["code"] == "MATH")
        self.assertEqual(maths["moyenne"], 15.0)

    def test_paiement_sandbox(self):
        c = self.client_pour(self.d.parent1)
        r = c.post(f"/api/eleves/{self.d.eleve1.pk}/paiements/", {"frais_id": self.frais.pk, "moyen": "OM", "telephone": "0700000000"}, format="json")
        self.assertEqual(r.status_code, 201)
        pid = r.json()["paiement"]["id"]
        r = c.get(f"/api/paiements/{pid}/")
        self.assertEqual(r.json()["statut"], "CONFIRME")
        self.assertEqual(self.frais.reste, 0)
        self.assertTrue(Paiement.objects.get(pk=pid).numero_recu)

    def test_lien_signe_recu(self):
        p = Paiement.objects.create(frais=self.frais, payeur=self.d.parent1, montant=1000, moyen="WAVE")
        from finances.fournisseurs import confirmer

        confirmer(p)
        url = self.client_pour(self.d.parent1).get(f"/api/liens/?type=recu&id={p.pk}").json()["url"]
        r = APIClient().get(url.replace("http://testserver", ""))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        # Un autre parent ne peut pas obtenir de lien
        self.assertEqual(self.client_pour(self.d.parent2).get(f"/api/liens/?type=recu&id={p.pk}").status_code, 404)
