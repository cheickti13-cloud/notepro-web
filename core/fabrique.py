"""
Fabrique de données pour les tests automatisés (et la démo).
Crée un petit établissement cohérent : 1 année, 2 périodes, 2 classes,
2 matières, 2 enseignants, élèves, parents, admin.
"""
from datetime import date, time
from decimal import Decimal

from accounts.models import Eleve, LienParentEleve, User
from scolarite.models import AnneeScolaire, Classe, Enseignement, Matiere, Periode, Salle

MDP = "MotDePasse-Test-2026"


def utilisateur(username, role, **kwargs):
    u = User(username=username, role=role, doit_changer_mdp=False, **kwargs)
    u.set_password(MDP)
    u.save()
    return u


def etablissement():
    """Retourne un objet simple dont les attributs sont les données créées."""

    class D:
        pass

    d = D()
    d.annee = AnneeScolaire.objects.create(
        libelle="2026-2027", debut=date(2026, 9, 1), fin=date(2027, 7, 15), active=True
    )
    d.t1 = Periode.objects.create(annee=d.annee, nom="1er trimestre", ordre=1, debut=date(2026, 9, 1), fin=date(2026, 12, 20))
    d.t2 = Periode.objects.create(annee=d.annee, nom="2e trimestre", ordre=2, debut=date(2027, 1, 5), fin=date(2027, 3, 31))

    d.admin = utilisateur("admin", User.Role.ADMIN, first_name="Awa", last_name="Admin")
    d.prof_maths = utilisateur("prof.maths", User.Role.ENSEIGNANT, first_name="Paul", last_name="Maths")
    d.prof_fr = utilisateur("prof.fr", User.Role.ENSEIGNANT, first_name="Fanta", last_name="Francais")

    d.classe_a = Classe.objects.create(annee=d.annee, nom="3e A", niveau="3e", professeur_principal=d.prof_maths)
    d.classe_b = Classe.objects.create(annee=d.annee, nom="3e B", niveau="3e")

    d.maths = Matiere.objects.create(nom="Mathématiques", code="MATH")
    d.francais = Matiere.objects.create(nom="Français", code="FR")
    d.salle1 = Salle.objects.create(nom="A01")
    d.salle2 = Salle.objects.create(nom="A02")

    d.ens_maths_a = Enseignement.objects.create(classe=d.classe_a, matiere=d.maths, enseignant=d.prof_maths, coefficient=Decimal("4"))
    d.ens_fr_a = Enseignement.objects.create(classe=d.classe_a, matiere=d.francais, enseignant=d.prof_fr, coefficient=Decimal("3"))
    # Le prof de français enseigne seul en 3e B : le prof de maths ne doit rien y voir
    d.ens_fr_b = Enseignement.objects.create(classe=d.classe_b, matiere=d.francais, enseignant=d.prof_fr, coefficient=Decimal("3"))

    d.u_eleve1 = utilisateur("eleve1", User.Role.ELEVE, first_name="Ali", last_name="Traore")
    d.u_eleve2 = utilisateur("eleve2", User.Role.ELEVE, first_name="Binta", last_name="Kone")
    d.u_eleve3 = utilisateur("eleve3", User.Role.ELEVE, first_name="Cheick", last_name="Sylla")
    d.eleve1 = Eleve.objects.create(user=d.u_eleve1, classe=d.classe_a)
    d.eleve2 = Eleve.objects.create(user=d.u_eleve2, classe=d.classe_a)
    d.eleve3 = Eleve.objects.create(user=d.u_eleve3, classe=d.classe_b)

    d.parent1 = utilisateur("parent1", User.Role.PARENT, first_name="Mariam", last_name="Traore")
    d.parent2 = utilisateur("parent2", User.Role.PARENT, first_name="Issa", last_name="Kone")
    LienParentEleve.objects.create(parent=d.parent1, eleve=d.eleve1, lien="MERE")
    # parent1 a deux enfants (dans deux classes différentes)
    LienParentEleve.objects.create(parent=d.parent1, eleve=d.eleve3, lien="MERE")
    LienParentEleve.objects.create(parent=d.parent2, eleve=d.eleve2, lien="PERE")
    return d


def creneau(enseignement, jour=0, debut=(8, 0), fin=(9, 0), salle=None):
    from edt.models import Creneau

    return Creneau.objects.create(
        enseignement=enseignement, jour=jour, heure_debut=time(*debut), heure_fin=time(*fin), salle=salle
    )
