from django.contrib import admin

from .models import Creneau, ModificationCours
from .services import notifier_modification


@admin.register(Creneau)
class CreneauAdmin(admin.ModelAdmin):
    list_display = ("enseignement", "jour", "heure_debut", "heure_fin", "salle")
    list_filter = ("jour", "enseignement__classe", "enseignement__enseignant")
    search_fields = ("enseignement__matiere__nom", "enseignement__classe__nom")
    autocomplete_fields = ("enseignement", "salle")


@admin.register(ModificationCours)
class ModificationCoursAdmin(admin.ModelAdmin):
    list_display = ("date", "creneau", "type", "nouvelle_salle", "remplacant")
    list_filter = ("type", "date")
    autocomplete_fields = ("creneau", "nouvelle_salle", "remplacant")
    exclude = ("cree_par",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)
        notifier_modification(obj)
