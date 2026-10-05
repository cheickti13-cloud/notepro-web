from django.contrib import admin

from .models import Annonce, Notification
from .services import publier_annonce


@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ("titre", "publiee_le", "importante", "classe", "pour_eleves", "pour_parents", "pour_enseignants")
    list_filter = ("importante", "classe")
    exclude = ("auteur",)

    def save_model(self, request, obj, form, change):
        nouveau = obj.pk is None
        if nouveau:
            obj.auteur = request.user
        super().save_model(request, obj, form, change)
        if nouveau:
            publier_annonce(obj)


# Les conversations privées ne sont volontairement PAS exposées dans l'admin
# (confidentialité des échanges). Seules les notifications techniques le sont.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("cree_le", "destinataire", "type", "titre", "lue")
    list_filter = ("type", "lue")
