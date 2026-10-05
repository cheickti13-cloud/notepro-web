"""
Envoi des notifications push via le service Expo Push (Android et iOS).

L'envoi se fait dans un fil séparé pour ne jamais ralentir la requête.
En production à fort volume, déplacer cet envoi dans une file de tâches (Celery, RQ).
Le contenu reste volontairement générique : aucune note ni motif d'absence
dans la notification (elle peut s'afficher sur l'écran verrouillé).
"""
import json
import logging
import threading
import urllib.request

log = logging.getLogger(__name__)
EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _envoyer(messages):
    for i in range(0, len(messages), 100):
        lot = messages[i:i + 100]
        try:
            req = urllib.request.Request(
                EXPO_URL,
                data=json.dumps(lot).encode(),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                r.read()
        except Exception:
            log.exception("Échec d'envoi des notifications push")


def envoyer_push(utilisateurs, type_, titre, lien=""):
    from accounts.models import AppareilPush

    autorises = [u.pk for u in utilisateurs if (u.preferences_push or {}).get(type_, True)]
    jetons = list(AppareilPush.objects.filter(utilisateur_id__in=autorises).values_list("jeton", flat=True))
    if not jetons:
        return
    messages = [
        {"to": j, "title": "NotePro", "body": titre[:178], "sound": "default", "data": {"lien": lien, "type": type_}}
        for j in jetons
    ]
    threading.Thread(target=_envoyer, args=(messages,), daemon=True).start()
