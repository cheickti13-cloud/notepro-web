from django.contrib import admin

from .models import Appreciation, AppreciationGenerale, PublicationBulletin


@admin.register(Appreciation)
class AppreciationAdmin(admin.ModelAdmin):
    list_display = ("eleve", "enseignement", "periode")
    list_filter = ("periode", "enseignement__classe")
    search_fields = ("eleve__user__last_name",)


@admin.register(AppreciationGenerale)
class AppreciationGeneraleAdmin(admin.ModelAdmin):
    list_display = ("eleve", "periode", "mention")
    list_filter = ("periode", "mention", "eleve__classe")


@admin.register(PublicationBulletin)
class PublicationBulletinAdmin(admin.ModelAdmin):
    list_display = ("classe", "periode", "publie_le", "publie_par")
