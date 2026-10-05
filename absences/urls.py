from django.urls import path

from . import views

app_name = "absences"

urlpatterns = [
    path("", views.mes_absences, name="mes_absences"),
    path("appel/", views.mes_appels, name="mes_appels"),
    path("appel/<int:creneau_id>/<str:jour>/", views.appel, name="appel"),
    path("<int:pk>/justifier/", views.justifier, name="justifier"),
    path("<int:pk>/justificatif/", views.justificatif, name="justificatif"),
    path("administration/", views.vue_admin, name="vue_admin"),
    path("administration/export.csv", views.export_csv, name="export_csv"),
    path("administration/saisie/", views.saisie_admin, name="saisie_admin"),
    path("administration/<int:pk>/traiter/", views.traiter, name="traiter"),
]
