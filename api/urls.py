"""
Routes de l'API mobile (préfixe /api/).
Toutes les vues sont exemptées du LoginRequiredMiddleware (pensé pour le site
web à sessions) : l'API s'authentifie par JWT via Django REST Framework.
"""
from django.contrib.auth.decorators import login_not_required
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views as v


def route(chemin, vue, nom):
    return path(chemin, login_not_required(vue.as_view()), name=nom)


app_name = "api"

urlpatterns = [
    route("auth/connexion/", v.Connexion, "connexion"),
    route("auth/rafraichir/", TokenRefreshView, "rafraichir"),
    route("auth/deconnexion/", v.Deconnexion, "deconnexion"),
    route("auth/mot-de-passe/", v.ChangerMotDePasse, "mot_de_passe"),
    route("moi/", v.Moi, "moi"),
    route("moi/preferences-push/", v.PreferencesPush, "preferences_push"),
    route("appareils/", v.Appareils, "appareils"),
    route("eleves/<int:eleve_id>/accueil/", v.Accueil, "accueil"),
    route("eleves/<int:eleve_id>/emploi-du-temps/", v.EmploiDuTemps, "edt"),
    route("eleves/<int:eleve_id>/notes/", v.Notes, "notes"),
    route("eleves/<int:eleve_id>/devoirs/", v.Devoirs, "devoirs"),
    route("devoirs/<int:devoir_id>/statut/", v.StatutDevoir, "statut_devoir"),
    route("eleves/<int:eleve_id>/absences/", v.Absences, "absences"),
    route("eleves/<int:eleve_id>/absences/declarer/", v.DeclarerAbsence, "declarer_absence"),
    route("absences/<int:absence_id>/justifier/", v.JustifierAbsence, "justifier"),
    route("conversations/", v.Conversations, "conversations"),
    route("conversations/<int:conv_id>/", v.ConversationDetail, "conversation"),
    route("contacts/", v.Contacts, "contacts"),
    route("notifications/", v.Notifications, "notifications"),
    route("notifications/lire/", v.LireNotifications, "lire_notifications"),
    route("vie-scolaire/", v.VieScolaire, "vie_scolaire"),
    route("eleves/<int:eleve_id>/frais/", v.Frais, "frais"),
    route("eleves/<int:eleve_id>/paiements/", v.Payer, "payer"),
    route("paiements/<int:paiement_id>/", v.PaiementDetail, "paiement"),
    route("liens/", v.LienFichier, "lien"),
    route("fichiers/<str:jeton>/", v.Fichier, "fichier"),
]
