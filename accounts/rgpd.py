"""
Outils RGPD : export des données d'une personne et anonymisation d'un compte.
"""
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string


def _donnees_eleve(eleve):
    from absences.models import Absence
    from notes.models import Note

    return {
        "eleve": str(eleve),
        "classe": str(eleve.classe) if eleve.classe else None,
        "date_naissance": eleve.date_naissance or None,
        "notes": [
            {
                "matiere": str(n.evaluation.enseignement.matiere),
                "evaluation": n.evaluation.titre,
                "date": n.evaluation.date,
                "valeur": n.valeur,
                "bareme": n.evaluation.bareme,
                "statut": n.get_statut_display(),
            }
            for n in Note.objects.filter(eleve=eleve, evaluation__publiee=True).select_related(
                "evaluation__enseignement__matiere"
            )
        ],
        "absences_retards": [
            {
                "date": a.date,
                "type": a.get_type_display(),
                "statut": a.get_statut_display(),
                "motif": a.motif or None,
            }
            for a in Absence.objects.filter(eleve=eleve)
        ],
    }


def exporter_donnees_utilisateur(user):
    from messagerie.models import Message

    donnees = {
        "date_export": timezone.now(),
        "compte": {
            "identifiant": user.username,
            "prenom": user.first_name,
            "nom": user.last_name,
            "email": user.email,
            "role": user.get_role_display(),
            "telephone": user.telephone or None,
            "adresse": user.adresse or None,
            "date_creation": user.date_joined,
            "derniere_connexion": user.last_login,
        },
        "messages_envoyes": [
            {"date": m.envoye_le, "sujet": m.conversation.sujet, "contenu": m.corps}
            for m in Message.objects.filter(auteur=user).select_related("conversation")
        ],
    }
    if user.est_eleve and hasattr(user, "eleve"):
        donnees["scolarite"] = _donnees_eleve(user.eleve)
    if user.est_parent:
        donnees["enfants"] = [_donnees_eleve(e) for e in user.enfants.select_related("user", "classe")]
    return donnees


@transaction.atomic
def anonymiser_utilisateur(user):
    """
    Anonymise un compte (départ de l'établissement, fin de la durée de conservation).
    Les données pédagogiques agrégées restent cohérentes (moyennes de classe),
    mais ne sont plus rattachables à une personne identifiée.
    """
    user.username = f"anonyme-{get_random_string(12).lower()}"
    user.first_name = "Anonyme"
    user.last_name = ""
    user.email = ""
    user.telephone = ""
    user.adresse = ""
    user.is_active = False
    user.set_unusable_password()
    user.anonymise_le = timezone.now()
    user.save()
    if hasattr(user, "eleve"):
        eleve = user.eleve
        eleve.date_naissance = ""
        eleve.save(update_fields=["date_naissance"])
        eleve.liens_parents.all().delete()
        # Suppression des justificatifs (documents potentiellement médicaux)
        for absence in eleve.absences.exclude(justificatif=""):
            absence.justificatif.delete(save=False)
            absence.justificatif = ""
            absence.motif = ""
            absence.save(update_fields=["justificatif", "motif"])
    user.liens_enfants.all().delete()
    return user
