from .models import JournalAcces


def ip_client(request):
    # Derrière un proxy cloud, la première IP de X-Forwarded-For est celle du client
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
    return ip or None


def tracer(request, action, objet):
    """Enregistre un accès à une donnée sensible. Ne bloque jamais la requête."""
    try:
        JournalAcces.objects.create(
            utilisateur=request.user if request.user.is_authenticated else None,
            action=action,
            objet=str(objet)[:200],
            adresse_ip=ip_client(request),
        )
    except Exception:  # pragma: no cover - la traçabilité ne doit pas casser la page
        import logging

        logging.getLogger(__name__).exception("Échec d'écriture du journal d'accès")
