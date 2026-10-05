"""Règles métier de la messagerie et des notifications."""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mass_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import User

from .models import Annonce, Conversation, Message, Notification, Participation

log = logging.getLogger(__name__)
R = User.Role


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def notifier(destinataires, type_, titre, lien="", importante=False):
    """Crée une notification pour chaque destinataire (+ e-mail si l'utilisateur l'a demandé)."""
    destinataires = list(destinataires)
    Notification.objects.bulk_create(
        [
            Notification(destinataire=u, type=type_, titre=titre[:200], lien=lien, importante=importante)
            for u in destinataires
        ]
    )
    try:
        from .push import envoyer_push

        envoyer_push(destinataires, type_, titre, lien)
    except Exception:
        log.exception("Notifications push indisponibles")
    courriels = [
        # Volontairement minimal : aucune donnée scolaire dans l'e-mail, juste une invitation à se connecter
        (f"[NotePro] {titre[:150]}", "Une nouvelle information vous attend sur NotePro.", settings.DEFAULT_FROM_EMAIL, [u.email])
        for u in destinataires
        if u.notifications_email and u.email
    ]
    if courriels:
        try:
            send_mass_mail(courriels, fail_silently=False)
        except Exception:
            log.exception("Envoi des e-mails de notification impossible")


# ---------------------------------------------------------------------------
# Qui peut écrire à qui
# ---------------------------------------------------------------------------
def destinataires_autorises(user):
    """
    Admin      -> tout le monde
    Enseignant -> administration, enseignants, élèves de ses classes et leurs parents
    Élève      -> enseignants de sa classe, administration (pas les autres élèves : protection des mineurs)
    Parent     -> enseignants des classes de ses enfants, administration
    """
    actifs = User.objects.filter(is_active=True).exclude(pk=user.pk)
    if user.est_admin:
        return actifs
    admins = Q(role=R.ADMIN)
    if user.est_enseignant:
        classes = user.enseignements.values("classe")
        classes_pp = user.classes_principales.values("pk")
        return actifs.filter(
            admins
            | Q(role=R.ENSEIGNANT)
            | Q(eleve__classe__in=classes)
            | Q(eleve__classe__in=classes_pp)
            | Q(enfants__classe__in=classes)
            | Q(enfants__classe__in=classes_pp)
        ).distinct()
    if user.est_eleve:
        classe_id = getattr(getattr(user, "eleve", None), "classe_id", None)
        return actifs.filter(admins | Q(role=R.ENSEIGNANT, enseignements__classe_id=classe_id)).distinct()
    if user.est_parent:
        classes = user.enfants.values("classe")
        return actifs.filter(admins | Q(role=R.ENSEIGNANT, enseignements__classe__in=classes)).distinct()
    return actifs.none()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
def conversations_de(user):
    return (
        Conversation.objects.filter(participations__utilisateur=user, participations__archivee=False)
        .prefetch_related("participants")
        .distinct()
    )


def nb_messages_non_lus(user):
    """Nombre de conversations contenant des messages non lus par `user`."""
    return (
        Participation.objects.filter(utilisateur=user, archivee=False)
        .filter(
            Q(derniere_lecture__isnull=True)
            | Q(conversation__dernier_message_le__gt=F("derniere_lecture"))
        )
        .count()
    )


def verifier_participant(user, conversation):
    p = Participation.objects.filter(conversation=conversation, utilisateur=user).first()
    if p is None:
        raise PermissionDenied("Vous ne participez pas à cette conversation.")
    return p


@transaction.atomic
def creer_conversation(auteur, destinataires, sujet, corps):
    autorises = set(destinataires_autorises(auteur).values_list("pk", flat=True))
    destinataires = [u for u in destinataires if u.pk != auteur.pk]
    if not destinataires:
        raise PermissionDenied("Aucun destinataire valide.")
    if any(u.pk not in autorises for u in destinataires):
        raise PermissionDenied("Vous n'êtes pas autorisé à écrire à l'un de ces destinataires.")
    conv = Conversation.objects.create(sujet=sujet, cree_par=auteur)
    maintenant = timezone.now()
    Participation.objects.bulk_create(
        [Participation(conversation=conv, utilisateur=auteur, derniere_lecture=maintenant)]
        + [Participation(conversation=conv, utilisateur=u) for u in destinataires]
    )
    _ajouter_message(conv, auteur, corps)
    return conv


@transaction.atomic
def repondre(conversation, auteur, corps):
    verifier_participant(auteur, conversation)
    return _ajouter_message(conversation, auteur, corps)


def _ajouter_message(conversation, auteur, corps):
    msg = Message.objects.create(conversation=conversation, auteur=auteur, corps=corps)
    conversation.dernier_message_le = msg.envoye_le
    conversation.save(update_fields=["dernier_message_le"])
    Participation.objects.filter(conversation=conversation, utilisateur=auteur).update(
        derniere_lecture=msg.envoye_le
    )
    # Une conversation archivée réapparaît quand un nouveau message arrive
    Participation.objects.filter(conversation=conversation).exclude(utilisateur=auteur).update(archivee=False)
    autres = conversation.participants.exclude(pk=auteur.pk).filter(is_active=True)
    notifier(
        autres,
        Notification.Type.MESSAGE,
        f"Message de {auteur} : {conversation.sujet}",
        lien=f"/messagerie/{conversation.pk}/",
    )
    return msg


def marquer_lue(conversation, user):
    Participation.objects.filter(conversation=conversation, utilisateur=user).update(
        derniere_lecture=timezone.now()
    )


# ---------------------------------------------------------------------------
# Annonces
# ---------------------------------------------------------------------------
def public_annonce(annonce):
    roles = []
    if annonce.pour_eleves:
        roles.append(R.ELEVE)
    if annonce.pour_parents:
        roles.append(R.PARENT)
    if annonce.pour_enseignants:
        roles.append(R.ENSEIGNANT)
    qs = User.objects.filter(is_active=True, role__in=roles)
    if annonce.classe_id:
        qs = qs.filter(
            Q(eleve__classe=annonce.classe)
            | Q(enfants__classe=annonce.classe)
            | Q(enseignements__classe=annonce.classe)
        )
    return qs.distinct()


def publier_annonce(annonce):
    notifier(
        public_annonce(annonce),
        Notification.Type.ANNONCE,
        annonce.titre,
        lien="/messagerie/annonces/",
        importante=annonce.importante,
    )


def annonces_visibles(user):
    if user.est_admin:
        return Annonce.objects.all()
    filtre_role = {
        R.ELEVE: Q(pour_eleves=True),
        R.PARENT: Q(pour_parents=True),
        R.ENSEIGNANT: Q(pour_enseignants=True),
    }.get(user.role, Q(pk__in=[]))
    if user.est_eleve:
        classes = Q(classe__isnull=True) | Q(classe__eleves__user=user)
    elif user.est_parent:
        classes = Q(classe__isnull=True) | Q(classe__in=user.enfants.values("classe"))
    else:
        classes = Q(classe__isnull=True) | Q(classe__in=user.enseignements.values("classe"))
    return Annonce.objects.filter(filtre_role & classes).distinct()

