from django.contrib import admin

from .models import ContenuSeance, Devoir


@admin.register(ContenuSeance)
class ContenuSeanceAdmin(admin.ModelAdmin):
    list_display = ("date", "enseignement", "titre")
    list_filter = ("enseignement__classe", "enseignement__matiere")
    date_hierarchy = "date"


@admin.register(Devoir)
class DevoirAdmin(admin.ModelAdmin):
    list_display = ("pour_le", "enseignement", "titre", "donne_le")
    list_filter = ("enseignement__classe", "enseignement__matiere")
    date_hierarchy = "pour_le"
