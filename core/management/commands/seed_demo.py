"""
Jeu de données de démonstration (DÉVELOPPEMENT UNIQUEMENT).
    python manage.py seed_demo
Crée un établissement fictif complet. Mot de passe de tous les comptes : voir la sortie.
"""
import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Eleve, LienParentEleve, User
from cahier.models import ContenuSeance, Devoir
from edt.models import Creneau
from finances.models import FraisScolarite
from messagerie.models import Annonce
from scolarite.models import Evenement
from notes.models import Evaluation, Note
from scolarite.models import AnneeScolaire, Classe, Enseignement, Matiere, Periode, Salle

MDP = "Demo-NotePro-2026"
PRENOMS = ["Awa", "Moussa", "Fatou", "Ibrahim", "Aminata", "Seydou", "Mariam", "Yao", "Adjoua", "Koffi",
           "Salimata", "Bakary", "Rokia", "Ousmane", "Kadiatou", "Drissa", "Nafissatou", "Lamine", "Assita", "Karim"]
NOMS = ["Traoré", "Koné", "Diallo", "Coulibaly", "Ouattara", "Bamba", "Kouassi", "Yao", "Touré", "Sylla",
        "Cissé", "Diabaté", "Konaté", "Sangaré", "Keïta"]
MATIERES = [("Mathématiques", "MATH", "#2f5bea", 4), ("Français", "FR", "#d9480f", 4), ("Anglais", "ANG", "#2b8a3e", 2),
            ("Histoire-Géographie", "HG", "#9c36b5", 2), ("Physique-Chimie", "PC", "#1098ad", 3), ("SVT", "SVT", "#5c940d", 2),
            ("EPS", "EPS", "#e67700", 1)]
HORAIRES = [(time(8), time(9)), (time(9), time(10)), (time(10, 15), time(11, 15)), (time(11, 15), time(12, 15)),
            (time(14), time(15)), (time(15), time(16))]


def compte(username, role, prenom, nom):
    u, _ = User.objects.get_or_create(username=username, defaults={"role": role, "first_name": prenom, "last_name": nom})
    u.role, u.first_name, u.last_name, u.doit_changer_mdp = role, prenom, nom, False
    u.set_password(MDP)
    u.save()
    return u


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (DEBUG uniquement)."

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("Commande réservée au développement (DEBUG=True).")
        if AnneeScolaire.objects.exists():
            raise CommandError("La base contient déjà des données : utilisez une base vide.")
        random.seed(42)
        aujourd_hui = timezone.localdate()
        debut = date(aujourd_hui.year if aujourd_hui.month >= 9 else aujourd_hui.year - 1, 9, 1)
        annee = AnneeScolaire.objects.create(libelle=f"{debut.year}-{debut.year + 1}", debut=debut, fin=date(debut.year + 1, 7, 15), active=True)
        periodes = [
            Periode.objects.create(annee=annee, nom="1er trimestre", ordre=1, debut=debut, fin=date(debut.year, 12, 20)),
            Periode.objects.create(annee=annee, nom="2e trimestre", ordre=2, debut=date(debut.year + 1, 1, 5), fin=date(debut.year + 1, 3, 31)),
            Periode.objects.create(annee=annee, nom="3e trimestre", ordre=3, debut=date(debut.year + 1, 4, 1), fin=date(debut.year + 1, 7, 15)),
        ]
        compte("admin", User.Role.ADMIN, "Awa", "Direction")
        matieres = [Matiere.objects.create(nom=n, code=c, couleur=col) for n, c, col, _ in MATIERES]
        coefs = {c: Decimal(k) for _, c, _, k in MATIERES}
        salles = [Salle.objects.create(nom=f"Salle {i}", capacite=40) for i in range(101, 109)]
        profs = {m.code: compte(f"prof.{m.code.lower()}", User.Role.ENSEIGNANT, random.choice(PRENOMS), random.choice(NOMS)) for m in matieres}

        n_eleve = 0
        for i, nom_classe in enumerate(["6e A", "3e A", "Tle D"]):
            classe = Classe.objects.create(annee=annee, nom=nom_classe, niveau=nom_classe.split()[0], professeur_principal=profs[matieres[i].code])
            enss = [Enseignement.objects.create(classe=classe, matiere=m, enseignant=profs[m.code], coefficient=coefs[m.code]) for m in matieres]
            # Emploi du temps : chaque matière placée sans conflit (classe/prof/salle)
            for _j, ens in enumerate(enss * 2):
                for _essai in range(60):
                    jour, (h1, h2) = random.randint(0, 4), random.choice(HORAIRES)
                    c = Creneau(enseignement=ens, jour=jour, heure_debut=h1, heure_fin=h2, salle=random.choice(salles))
                    try:
                        c.full_clean()
                    except Exception:
                        continue
                    c.save()
                    break
            eleves = []
            for _k in range(12):
                n_eleve += 1
                prenom, nom = random.choice(PRENOMS), random.choice(NOMS)
                u = compte(f"eleve{n_eleve}", User.Role.ELEVE, prenom, nom)
                e = Eleve.objects.create(user=u, classe=classe, date_naissance=f"{2014 - i * 3}-0{random.randint(1, 9)}-1{random.randint(0, 9)}")
                p = compte(f"parent{n_eleve}", User.Role.PARENT, random.choice(PRENOMS), nom)
                LienParentEleve.objects.create(parent=p, eleve=e, lien=random.choice(["MERE", "PERE"]))
                eleves.append(e)
                for t, (mois, jour) in enumerate([(9, 15), (1, 15), (4, 15)], start=1):
                    FraisScolarite.objects.create(
                        eleve=e, annee=annee, libelle=f"{t}e tranche de scolarité" if t > 1 else "1re tranche de scolarité",
                        montant=150000, echeance=date(debut.year + (0 if mois >= 9 else 1), mois, jour),
                    )
            # Notes du 1er trimestre
            p1 = periodes[0]
            for ens in enss:
                for t, titre in enumerate(["Devoir 1", "Interrogation", "Devoir 2"]):
                    d = min(p1.debut + timedelta(days=15 + 25 * t), p1.fin)
                    ev = Evaluation.objects.create(enseignement=ens, periode=p1, titre=titre, date=d,
                                                   bareme=Decimal("10") if titre == "Interrogation" else Decimal("20"),
                                                   coefficient=Decimal("1") if titre == "Interrogation" else Decimal("2"))
                    for e in eleves:
                        maxi = int(ev.bareme)
                        Note.objects.create(evaluation=ev, eleve=e, valeur=Decimal(random.randint(maxi // 4, maxi * 4) ) / 4 if random.random() > .05 else None,
                                            statut="NOTEE" if random.random() > .05 else "ABSENT")
                Devoir.objects.create(enseignement=ens, donne_le=aujourd_hui, pour_le=aujourd_hui + timedelta(days=random.randint(1, 6)),
                                      titre=f"Exercices — {ens.matiere}", description="Voir le manuel, pages indiquées en classe.")
                ContenuSeance.objects.create(enseignement=ens, date=aujourd_hui - timedelta(days=1), titre="Séance du jour",
                                             contenu="Correction des exercices et nouvelle notion.")
        Note.objects.filter(statut="ABSENT").update(valeur=None)
        Note.objects.filter(statut="NOTEE", valeur__isnull=True).update(statut="ABSENT")
        maintenant = timezone.now()
        for jours, titre, type_, lieu in [
            (4, "Réunion parents-professeurs", "REUNION", "Salle polyvalente"),
            (10, "Journée culturelle", "CULTURE", "Cour principale"),
            (13, "Compositions du trimestre", "EXAMEN", "Salles de classe"),
            (18, "Vacances scolaires", "VACANCES", ""),
        ]:
            Evenement.objects.create(titre=titre, type=type_, lieu=lieu, debut=maintenant + timedelta(days=jours))
        Annonce.objects.create(titre="Bienvenue sur NotePro", contenu="Votre nouvel espace numérique de vie scolaire.", importante=True)
        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))
        self.stdout.write(f"Mot de passe de tous les comptes : {MDP}")
        self.stdout.write("Comptes : admin · prof.math, prof.fr, ... · eleve1 à eleve36 · parent1 à parent36")
