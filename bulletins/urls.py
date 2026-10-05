from django.urls import path

from . import views

app_name = "bulletins"

urlpatterns = [
    path("", views.index, name="index"),
    path("appreciations/<int:enseignement_id>/", views.appreciations, name="appreciations"),
    path("conseil/<int:classe_id>/", views.conseil, name="conseil"),
    path("publier/<int:classe_id>/<int:periode_id>/", views.publier, name="publier"),
    path("pdf/eleve/<int:eleve_id>/<int:periode_id>/", views.pdf_eleve, name="pdf_eleve"),
    path("pdf/classe/<int:classe_id>/<int:periode_id>/", views.pdf_classe, name="pdf_classe"),
]
