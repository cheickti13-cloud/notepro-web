from django.urls import path

from . import views

app_name = "edt"

urlpatterns = [
    path("", views.mon_edt, name="mon_edt"),
    path("classe/<int:classe_id>/", views.edt_classe, name="classe"),
    path("enseignant/<int:user_id>/", views.edt_enseignant, name="enseignant"),
    path("eleve/<int:eleve_id>/", views.edt_eleve, name="eleve"),
    path("modifications/", views.modifications, name="modifications"),
    path("modifications/<int:pk>/supprimer/", views.supprimer_modification, name="supprimer_modification"),
]
