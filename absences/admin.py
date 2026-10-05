from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Absence, Appel


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ("date", "eleve", "type", "minutes_retard", "statut")
    list_filter = ("type", "statut", "eleve__classe")
    search_fields = ("eleve__user__last_name", "eleve__user__first_name")
    date_hierarchy = "date"
    autocomplete_fields = ("eleve", "creneau")
    readonly_fields = ("saisie_par", "saisie_le", "justifiee_par", "justifiee_le", "traitee_par", "lien_justificatif")
    exclude = ("justificatif",)  # jamais d'URL directe : passage obligé par la vue protégée

    @admin.display(description="justificatif")
    def lien_justificatif(self, obj):
        if obj.pk and obj.justificatif:
            return format_html('<a href="{}">Télécharger</a>', reverse("absences:justificatif", args=[obj.pk]))
        return "—"


@admin.register(Appel)
class AppelAdmin(admin.ModelAdmin):
    list_display = ("date", "creneau", "fait_par", "fait_le")
    date_hierarchy = "date"
