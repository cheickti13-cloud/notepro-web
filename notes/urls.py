from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.mes_enseignements, name="mes_enseignements"),
    path("releve/", views.releve, name="releve"),
    path("enseignement/<int:enseignement_id>/", views.evaluations, name="evaluations"),
    path("enseignement/<int:enseignement_id>/nouvelle/", views.evaluation_form, name="evaluation_creer"),
    path("enseignement/<int:enseignement_id>/evaluation/<int:pk>/", views.evaluation_form, name="evaluation_modifier"),
    path("evaluation/<int:pk>/saisie/", views.saisie, name="saisie"),
    path("evaluation/<int:pk>/supprimer/", views.evaluation_supprimer, name="evaluation_supprimer"),
]
