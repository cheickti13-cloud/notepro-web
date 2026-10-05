from django.contrib import admin

from .models import JournalAcces


@admin.register(JournalAcces)
class JournalAccesAdmin(admin.ModelAdmin):
    list_display = ("date", "utilisateur", "action", "objet", "adresse_ip")
    list_filter = ("action",)
    search_fields = ("objet", "utilisateur__username")
    date_hierarchy = "date"

    # Journal en lecture seule : personne ne peut le modifier depuis l'admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
