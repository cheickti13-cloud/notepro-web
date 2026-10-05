"""
Messagerie interne, notifications et annonces.

- Conversation : fil de discussion entre plusieurs participants.
- Participation : appartenance d'un utilisateur à une conversation (+ date de dernière lecture).
- Message : un message dans une conversation.
- Notification : alerte individuelle (nouveau message, absence, note, changement de cours...).
- Annonce : information de l'administration diffusée à un public ciblé.
"""
from django.conf import settings
from django.db import models

from core.storage import chemin_aleatoire, stockage_prive
from core.validators import valider_justificatif


class Conversation(models.Model):
    sujet = models.CharField(max_length=150)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    dernier_message_le = models.DateTimeField(auto_now_add=True, db_index=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Participation", related_name="conversations"
    )

    class Meta:
        ordering = ["-dernier_message_le"]

    def __str__(self):
        return self.sujet


class Participation(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participations")
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations"
    )
    derniere_lecture = models.DateTimeField(null=True, blank=True)
    archivee = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "utilisateur"], name="participation_unique")
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="messages_envoyes"
    )
    corps = models.TextField(max_length=5000)
    piece_jointe = models.FileField(
        upload_to=chemin_aleatoire("messages"), storage=stockage_prive, blank=True,
        validators=[valider_justificatif],
    )
    envoye_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["envoye_le"]

    def __str__(self):
        return f"{self.auteur} — {self.envoye_le:%d/%m/%Y %H:%M}"


class Notification(models.Model):
    class Type(models.TextChoices):
        MESSAGE = "MESSAGE", "Nouveau message"
        ANNONCE = "ANNONCE", "Information"
        ABSENCE = "ABSENCE", "Absence / retard"
        NOTE = "NOTE", "Nouvelle note"
        EDT = "EDT", "Emploi du temps"
        DEVOIR = "DEVOIR", "Devoir"
        BULLETIN = "BULLETIN", "Bulletin"

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=10, choices=Type.choices)
    titre = models.CharField(max_length=200)
    lien = models.CharField(max_length=300, blank=True)
    importante = models.BooleanField(default=False)
    lue = models.BooleanField(default=False, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-cree_le"]
        indexes = [models.Index(fields=["destinataire", "lue"])]

    def __str__(self):
        return self.titre


class Annonce(models.Model):
    titre = models.CharField(max_length=150)
    contenu = models.TextField(max_length=5000)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    pour_eleves = models.BooleanField("élèves", default=True)
    pour_parents = models.BooleanField("parents", default=True)
    pour_enseignants = models.BooleanField("enseignants", default=True)
    classe = models.ForeignKey(
        "scolarite.Classe",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Laisser vide pour tout l'établissement.",
    )
    importante = models.BooleanField(default=False, help_text="Mise en avant sur le tableau de bord.")
    publiee_le = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-publiee_le"]

    def __str__(self):
        return self.titre
