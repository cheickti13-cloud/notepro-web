from django.contrib import admin

from .models import Evaluation, Note


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    autocomplete_fields = ("eleve",)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("titre", "enseignement", "periode", "date", "bareme", "coefficient", "publiee")
    list_filter = ("periode", "enseignement__classe", "enseignement__matiere", "publiee")
    search_fields = ("titre",)
    inlines = [NoteInline]
    exclude = ("creee_par",)
