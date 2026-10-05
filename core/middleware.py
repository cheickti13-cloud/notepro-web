from django.shortcuts import redirect
from django.urls import reverse


class SecurityHeadersMiddleware:
    """Ajoute une politique de sécurité du contenu (CSP) et quelques en-têtes."""

    CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # L'admin Django utilise des scripts inline : on ne lui applique pas la CSP stricte
        if not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", self.CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # Pas de mise en cache des pages contenant des données personnelles
        if request.user.is_authenticated:
            response.setdefault("Cache-Control", "no-store, private")
        return response


class ForcePasswordChangeMiddleware:
    """Oblige l'utilisateur à changer son mot de passe initial."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if u.is_authenticated and getattr(u, "doit_changer_mdp", False) and not u.is_superuser:
            autorises = {reverse("accounts:changer_mdp"), reverse("accounts:logout")}
            if request.path not in autorises and not request.path.startswith("/static/"):
                return redirect("accounts:changer_mdp")
        return self.get_response(request)
