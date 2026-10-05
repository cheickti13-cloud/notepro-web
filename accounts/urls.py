from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("connexion/", views.connexion, name="login"),
    path("deconnexion/", views.deconnexion, name="logout"),
    path("mot-de-passe/", views.changer_mdp, name="changer_mdp"),
    path("", views.mon_compte, name="mon_compte"),
    path("export/", views.exporter_mes_donnees, name="export"),
]
