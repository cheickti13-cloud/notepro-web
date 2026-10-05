"""
Comptes utilisateurs et rôles.

- Un seul modèle User avec un champ `role` (élève, parent, enseignant, admin).
- Le profil `Eleve` porte les informations scolaires de l'élève (classe...).
- `LienParentEleve` relie un compte parent à un ou plusieurs élèves.

RGPD : on ne stocke que le strict nécessaire. Les coordonnées (téléphone,
adresse) et la date de naissance sont chiffrées au repos.
"""
import hashlib
import hmac
import re

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from core.fields import EncryptedTextField


class User(AbstractUser):
    class Role(models.TextChoices):
        ELEVE = "ELEVE", "Élève"
        PARENT = "PARENT", "Parent"
        ENSEIGNANT = "ENSEIGNANT", "Enseignant"
        ADMIN = "ADMIN", "Administration"

    role = models.CharField(max_length=12, choices=Role.choices, db_index=True)
    telephone = EncryptedTextField("téléphone", blank=True)
    adresse = EncryptedTextField(blank=True)
    doit_changer_mdp = models.BooleanField(
        "doit changer son mot de passe",
        default=True,
        help_text="Force le changement du mot de passe initial à la première connexion.",
    )
    notifications_email = models.BooleanField("recevoir les notifications par e-mail", default=False)
    anonymise_le = models.DateTimeField(null=True, blank=True, editable=False)
    # Empreinte HMAC du téléphone : permet la connexion par numéro sans stocker
    # le numéro en clair (le champ `telephone` reste chiffré).
    telephone_empreinte = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    # Préférences de notifications push par catégorie : {"NOTE": false, ...} (absent = activé)
    preferences_push = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "utilisateur"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        nom = self.get_full_name()
        return nom or self.username

    # Raccourcis de lecture dans le code et les gabarits
    @property
    def est_eleve(self):
        return self.role == self.Role.ELEVE

    @property
    def est_parent(self):
        return self.role == self.Role.PARENT

    @property
    def est_enseignant(self):
        return self.role == self.Role.ENSEIGNANT

    @property
    def est_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    # Le rôle Administration donne tous les droits dans /admin (pas besoin de gérer
    # les permissions fines de Django pour un établissement unique).
    def has_perm(self, perm, obj=None):
        if self.is_active and self.role == self.Role.ADMIN:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.role == self.Role.ADMIN:
            return True
        return super().has_module_perms(app_label)

    @staticmethod
    def empreinte_telephone(numero: str) -> str:
        """Normalise le numéro (chiffres uniquement, sans préfixe 00) puis le hache avec SECRET_KEY."""
        chiffres = re.sub(r"\D", "", numero or "")
        if chiffres.startswith("00"):
            chiffres = chiffres[2:]
        if not chiffres:
            return ""
        return hmac.new(settings.SECRET_KEY.encode(), chiffres.encode(), hashlib.sha256).hexdigest()

    def save(self, *args, **kwargs):
        self.telephone_empreinte = self.empreinte_telephone(self.telephone)
        # Seule l'administration accède à l'interface /admin de Django
        if self.is_superuser:
            self.role = self.Role.ADMIN
        self.is_staff = self.role == self.Role.ADMIN
        super().save(*args, **kwargs)


class Eleve(models.Model):
    """Profil scolaire d'un élève (lié 1-1 à son compte)."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="eleve",
        limit_choices_to={"role": User.Role.ELEVE},
    )
    classe = models.ForeignKey(
        "scolarite.Classe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eleves",
    )
    date_naissance = EncryptedTextField(
        "date de naissance (AAAA-MM-JJ)", blank=True, help_text="Donnée chiffrée."
    )
    parents = models.ManyToManyField(
        User,
        through="LienParentEleve",
        related_name="enfants",
        blank=True,
    )

    class Meta:
        verbose_name = "élève"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return str(self.user)

    def clean(self):
        if self.user_id and self.user.role != User.Role.ELEVE:
            raise ValidationError("Le compte associé doit avoir le rôle Élève.")


class LienParentEleve(models.Model):
    class Lien(models.TextChoices):
        MERE = "MERE", "Mère"
        PERE = "PERE", "Père"
        TUTEUR = "TUTEUR", "Tuteur légal"
        AUTRE = "AUTRE", "Autre responsable"

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="liens_enfants",
        limit_choices_to={"role": User.Role.PARENT},
    )
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="liens_parents")
    lien = models.CharField(max_length=10, choices=Lien.choices, default=Lien.AUTRE)

    class Meta:
        verbose_name = "lien parent / élève"
        verbose_name_plural = "liens parent / élève"
        constraints = [
            models.UniqueConstraint(fields=["parent", "eleve"], name="lien_parent_eleve_unique")
        ]

    def __str__(self):
        return f"{self.parent} → {self.eleve} ({self.get_lien_display()})"

    def clean(self):
        if self.parent_id and self.parent.role != User.Role.PARENT:
            raise ValidationError("Le compte parent doit avoir le rôle Parent.")


class AppareilPush(models.Model):
    """Jeton Expo Push d'un téléphone, pour les notifications push."""

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appareils")
    jeton = models.CharField(max_length=200, unique=True)
    plateforme = models.CharField(max_length=10, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    vu_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "appareil (notifications push)"
        verbose_name_plural = "appareils (notifications push)"

    def __str__(self):
        return f"{self.utilisateur} — {self.plateforme}"
