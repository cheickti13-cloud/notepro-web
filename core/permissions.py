"""
Contrôle d'accès centralisé.

Deux niveaux :
1. Par rôle : décorateur `role_requis` sur les vues.
2. Par objet : `eleves_visibles(user)` définit, pour chaque rôle, l'ensemble
   des élèves dont l'utilisateur peut voir les données. Toutes les vues qui
   affichent des données d'élève passent par ces fonctions : c'est le point
   unique à auditer.

    Admin      -> tous les élèves
    Enseignant -> élèves des classes où il enseigne (ou dont il est prof principal)
    Parent     -> ses enfants (LienParentEleve)
    Élève      -> lui-même uniquement
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from accounts.models import Eleve, User

R = User.Role


def role_requis(*roles):
    """Décorateur de vue : refuse (403) si le rôle de l'utilisateur n'est pas autorisé."""

    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            u = request.user
            if not u.is_authenticated:
                raise PermissionDenied
            role = R.ADMIN if u.is_superuser else u.role
            if role not in roles:
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur


def eleves_visibles(user):
    """QuerySet des élèves dont `user` peut consulter les données."""
    if not user.is_authenticated:
        return Eleve.objects.none()
    qs = Eleve.objects.select_related("user", "classe")
    if user.est_admin:
        return qs
    if user.est_enseignant:
        return qs.filter(
            Q(classe__enseignements__enseignant=user) | Q(classe__professeur_principal=user)
        ).distinct()
    if user.est_parent:
        return qs.filter(liens_parents__parent=user)
    if user.est_eleve:
        return qs.filter(user=user)
    return qs.none()


def peut_voir_eleve(user, eleve) -> bool:
    return eleves_visibles(user).filter(pk=eleve.pk).exists()


def verifier_acces_eleve(user, eleve):
    if not peut_voir_eleve(user, eleve):
        raise PermissionDenied("Accès refusé aux données de cet élève.")


def peut_gerer_enseignement(user, enseignement) -> bool:
    """Saisie (notes, cahier de texte, appréciations) : l'enseignant titulaire ou l'admin."""
    return user.est_admin or (user.est_enseignant and enseignement.enseignant_id == user.pk)


def verifier_gestion_enseignement(user, enseignement):
    if not peut_gerer_enseignement(user, enseignement):
        raise PermissionDenied("Vous n'êtes pas l'enseignant de ce cours.")


def eleve_courant(request):
    """
    Pour les vues « élève » consultées par un élève ou un parent :
    - élève  : son propre profil
    - parent : l'enfant choisi via ?eleve=<id> (par défaut le premier)
    - enseignant/admin : l'élève passé en paramètre s'il est visible
    Retourne (eleve, liste_des_eleves_selectionnables).
    """
    user = request.user
    visibles = eleves_visibles(user)
    eid = request.GET.get("eleve") or request.POST.get("eleve")
    if user.est_eleve:
        eleve = visibles.first()
        if eid and (eleve is None or str(eleve.pk) != str(eid)):
            raise PermissionDenied("Accès refusé aux données de cet élève.")
        return eleve, []
    choix = list(visibles) if user.est_parent else []
    if eid and str(eid).isdigit():
        eleve = visibles.filter(pk=int(eid)).first()
        if eleve is None:
            raise PermissionDenied("Accès refusé aux données de cet élève.")
        return eleve, choix
    return (choix[0] if choix else None), choix
