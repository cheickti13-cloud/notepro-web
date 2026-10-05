from django.urls import path

from . import views

app_name = "messagerie"

urlpatterns = [
    path("", views.boite, name="boite"),
    path("nouveau/", views.nouveau, name="nouveau"),
    path("<int:pk>/", views.conversation, name="conversation"),
    path("<int:pk>/archiver/", views.archiver, name="archiver"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/", views.ouvrir_notification, name="ouvrir_notification"),
    path("notifications/tout-lu/", views.tout_marquer_lu, name="tout_lu"),
    path("annonces/", views.annonces, name="annonces"),
    path("annonces/nouvelle/", views.nouvelle_annonce, name="nouvelle_annonce"),
]
