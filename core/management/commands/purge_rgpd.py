"""
Purge RGPD : supprime les données dont la durée de conservation est dépassée.
À planifier (ex. une fois par nuit) chez l'hébergeur :  python manage.py purge_rgpd
Durées configurables dans settings.RGPD_CONSERVATION (variables d'environnement).
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from absences.models import Absence
from core.models import JournalAcces
from messagerie.models import Conversation, Notification


class Command(BaseCommand):
    help = "Supprime les données personnelles au-delà de leur durée de conservation."

    def add_arguments(self, parser):
        parser.add_argument("--simulation", action="store_true", help="Affiche ce qui serait supprimé sans rien supprimer.")

    def handle(self, *args, simulation=False, **opts):
        c = settings.RGPD_CONSERVATION
        maintenant = timezone.now()
        resultats = {}

        notifs = Notification.objects.filter(cree_le__lt=maintenant - timedelta(days=c["notifications"]))
        convs = Conversation.objects.filter(dernier_message_le__lt=maintenant - timedelta(days=c["messages"]))
        journal = JournalAcces.objects.filter(date__lt=maintenant - timedelta(days=c["journal_acces"]))
        justifs = Absence.objects.filter(
            date__lt=(maintenant - timedelta(days=c["justificatifs"])).date()
        ).exclude(justificatif="", motif="")

        resultats["notifications"] = notifs.count()
        resultats["conversations"] = convs.count()
        resultats["journal d'accès"] = journal.count()
        resultats["justificatifs/motifs d'absence"] = justifs.count()

        if not simulation:
            notifs.delete()
            convs.delete()
            journal.delete()
            for a in justifs.iterator():
                if a.justificatif:
                    a.justificatif.delete(save=False)
                a.justificatif = ""
                a.motif = ""  # l'absence elle-même est conservée (historique scolaire), sans le motif
                a.save(update_fields=["justificatif", "motif"])

        prefixe = "[SIMULATION] " if simulation else ""
        for cle, n in resultats.items():
            self.stdout.write(f"{prefixe}{cle} : {n}")
        self.stdout.write(self.style.SUCCESS(f"{prefixe}Purge RGPD terminée."))
