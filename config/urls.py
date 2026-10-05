from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "NotePro — Administration"
admin.site.site_title = "NotePro"
admin.site.index_title = "Gestion de l'établissement"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("compte/", include("accounts.urls")),
    path("emploi-du-temps/", include("edt.urls")),
    path("notes/", include("notes.urls")),
    path("absences/", include("absences.urls")),
    path("cahier-de-texte/", include("cahier.urls")),
    path("bulletins/", include("bulletins.urls")),
    path("messagerie/", include("messagerie.urls")),
    path("", include("dashboard.urls")),
]

handler403 = "core.views.erreur_403"
handler404 = "core.views.erreur_404"
