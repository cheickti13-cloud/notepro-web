from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.crypto import get_random_string

from core.audit import tracer
from core.models import JournalAcces

from .models import AppareilPush, Eleve, LienParentEleve, User
from .rgpd import anonymiser_utilisateur


class EleveInline(admin.StackedInline):
    model = Eleve
    can_delete = False
    fk_name = "user"
    fields = ("classe", "date_naissance")
    extra = 0
    max_num = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "last_name", "first_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("last_name", "first_name")
    actions = ["reinitialiser_mdp", "anonymiser"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "email", "telephone", "adresse")}),
        ("Rôle", {"fields": ("role", "is_active", "doit_changer_mdp", "notifications_email")}),
        ("Dates", {"fields": ("last_login", "date_joined", "anonymise_le")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username", "first_name", "last_name", "email", "role",
                    "usable_password", "password1", "password2",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined", "anonymise_le")

    def get_inlines(self, request, obj):
        # Le profil scolaire n'apparaît que pour les comptes élèves
        if obj is not None and obj.role == User.Role.ELEVE:
            return [EleveInline]
        return []

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == User.Role.ELEVE:
            Eleve.objects.get_or_create(user=obj)

    @admin.action(description="Réinitialiser le mot de passe (mot de passe temporaire)")
    def reinitialiser_mdp(self, request, queryset):
        lignes = []
        for user in queryset:
            mdp = get_random_string(12)
            user.set_password(mdp)
            user.doit_changer_mdp = True
            user.save()
            lignes.append(f"{user.username} : {mdp}")
        # Affiché une seule fois à l'administrateur, jamais stocké en clair
        self.message_user(
            request,
            "Mots de passe temporaires (à transmettre de façon sécurisée) — " + " | ".join(lignes),
            messages.WARNING,
        )

    @admin.action(description="Anonymiser (RGPD) — irréversible")
    def anonymiser(self, request, queryset):
        n = 0
        for user in queryset.exclude(pk=request.user.pk).filter(is_superuser=False):
            tracer(request, JournalAcces.Action.SUPPRESSION, f"anonymisation de {user.username}")
            anonymiser_utilisateur(user)
            n += 1
        self.message_user(request, f"{n} compte(s) anonymisé(s).")


class LienParentInline(admin.TabularInline):
    model = LienParentEleve
    extra = 1
    autocomplete_fields = ("parent",)


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ("__str__", "classe")
    list_filter = ("classe",)
    search_fields = ("user__first_name", "user__last_name", "user__username")
    autocomplete_fields = ("user", "classe")
    inlines = [LienParentInline]


@admin.register(LienParentEleve)
class LienParentEleveAdmin(admin.ModelAdmin):
    list_display = ("parent", "eleve", "lien")
    search_fields = ("parent__last_name", "eleve__user__last_name")
    autocomplete_fields = ("parent", "eleve")


@admin.register(AppareilPush)
class AppareilPushAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "plateforme", "vu_le")
    search_fields = ("utilisateur__username",)
