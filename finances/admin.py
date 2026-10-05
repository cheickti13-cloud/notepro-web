from django.contrib import admin

from .fournisseurs import confirmer
from .models import FraisScolarite, Paiement


class PaiementInline(admin.TabularInline):
    model = Paiement
    extra = 0
    fields = ("montant", "moyen", "statut", "reference", "numero_recu", "cree_le")
    readonly_fields = ("reference", "numero_recu", "cree_le")


@admin.register(FraisScolarite)
class FraisScolariteAdmin(admin.ModelAdmin):
    list_display = ("eleve", "libelle", "categorie", "montant", "echeance", "reste_a_payer")
    list_filter = ("categorie", "annee", "eleve__classe")
    search_fields = ("eleve__user__last_name", "libelle")
    autocomplete_fields = ("eleve",)
    inlines = [PaiementInline]

    @admin.display(description="reste à payer")
    def reste_a_payer(self, obj):
        return obj.reste


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("reference", "frais", "montant", "moyen", "statut", "cree_le")
    list_filter = ("statut", "moyen")
    search_fields = ("reference", "numero_recu", "frais__eleve__user__last_name")
    readonly_fields = ("reference", "numero_recu", "confirme_le")
    actions = ["confirmer_paiements"]

    @admin.action(description="Confirmer (paiement reçu au guichet ou vérifié)")
    def confirmer_paiements(self, request, queryset):
        for p in queryset:
            confirmer(p)
        self.message_user(request, f"{queryset.count()} paiement(s) confirmé(s).")
