from django.conf import settings


def notepro(request):
    ctx = {"ETABLISSEMENT_NOM": settings.ETABLISSEMENT_NOM}
    u = getattr(request, "user", None)
    if u is not None and u.is_authenticated:
        from messagerie.services import nb_messages_non_lus
        from messagerie.models import Notification

        ctx["nb_notifications"] = Notification.objects.filter(destinataire=u, lue=False).count()
        ctx["nb_messages"] = nb_messages_non_lus(u)
    return ctx
