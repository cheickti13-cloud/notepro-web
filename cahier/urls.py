from django.urls import path

from . import views

app_name = "cahier"

urlpatterns = [
    path("", views.index, name="index"),
    path("classe/<int:classe_id>/", views.classe, name="classe"),
    path("enseignement/<int:enseignement_id>/", views.enseignement, name="enseignement"),
    path("enseignement/<int:enseignement_id>/contenu/", views.contenu_form, name="contenu_creer"),
    path("enseignement/<int:enseignement_id>/contenu/<int:pk>/", views.contenu_form, name="contenu_modifier"),
    path("enseignement/<int:enseignement_id>/devoir/", views.devoir_form, name="devoir_creer"),
    path("enseignement/<int:enseignement_id>/devoir/<int:pk>/", views.devoir_form, name="devoir_modifier"),
    path("supprimer/<str:type_>/<int:pk>/", views.supprimer, name="supprimer"),
    path("devoir/<int:pk>/fait/", views.basculer_fait, name="basculer_fait"),
]
