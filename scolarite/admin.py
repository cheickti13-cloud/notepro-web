from django.contrib import admin

from .models import AnneeScolaire, Classe, DocumentEtablissement, Enseignement, Evenement, Matiere, Periode, Salle


class PeriodeInline(admin.TabularInline):
    model = Periode
    extra = 0


@admin.register(AnneeScolaire)
class AnneeScolaireAdmin(admin.ModelAdmin):
    list_display = ("libelle", "debut", "fin", "active")
    inlines = [PeriodeInline]


class EnseignementInline(admin.TabularInline):
    model = Enseignement
    extra = 0
    autocomplete_fields = ("matiere", "enseignant")


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ("nom", "niveau", "annee", "professeur_principal", "effectif")
    list_filter = ("annee", "niveau")
    search_fields = ("nom",)
    inlines = [EnseignementInline]

    @admin.display(description="effectif")
    def effectif(self, obj):
        return obj.eleves.count()


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ("nom", "code", "couleur")
    search_fields = ("nom", "code")


@admin.register(Salle)
class SalleAdmin(admin.ModelAdmin):
    list_display = ("nom", "capacite")
    search_fields = ("nom",)


@admin.register(Enseignement)
class EnseignementAdmin(admin.ModelAdmin):
    list_display = ("matiere", "classe", "enseignant", "coefficient")
    list_filter = ("classe", "matiere")
    search_fields = ("matiere__nom", "classe__nom", "enseignant__last_name")
    autocomplete_fields = ("matiere", "enseignant", "classe")


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ("titre", "type", "debut", "lieu", "classe")
    list_filter = ("type", "classe")
    date_hierarchy = "debut"


@admin.register(DocumentEtablissement)
class DocumentEtablissementAdmin(admin.ModelAdmin):
    list_display = ("titre", "publie_le", "classe")
