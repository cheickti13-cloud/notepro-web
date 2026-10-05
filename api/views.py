"""
API REST de l'application mobile NotePro.

Authentification : JWT (en-tête `Authorization: Bearer <jeton>`).
Contrôle d'accès : les mêmes règles que le site web, via core.permissions
(`eleves_visibles`, `verifier_acces_eleve`...). Aucune donnée d'un élève n'est
renvoyée sans passer par ces fonctions.
"""
from datetime import date as Date, timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from absences.models import Absence
from accounts.models import AppareilPush, Eleve, User
from cahier.models import Devoir, DevoirFait
from core.audit import tracer
from core.models import JournalAcces
from core.permissions import eleves_visibles, verifier_acces_eleve
from core.validators import valider_justificatif
from edt.services import lundi_de
from finances.fournisseurs import fournisseur
from finances.models import FraisScolarite, Paiement
from messagerie.models import Conversation, Message, Notification, Participation
from messagerie.services import (
    annonces_visibles,
    conversations_de,
    creer_conversation,
    destinataires_autorises,
    marquer_lue,
    notifier,
    repondre,
    verifier_participant,
)
from scolarite.models import DocumentEtablissement, Evenement, Periode
from scolarite.services import annee_active, periode_courante, periodes_actives

from . import donnees as D


def eleve_autorise(request, eleve_id):
    eleve = get_object_or_404(Eleve.objects.select_related("user", "classe"), pk=eleve_id)
    verifier_acces_eleve(request.user, eleve)
    return eleve


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
class ConnexionSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "Identifiant ou mot de passe incorrect."}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token


class Connexion(TokenObtainPairView):
    """POST {username, password} -> {access, refresh}. `username` accepte aussi un numéro de téléphone."""

    serializer_class = ConnexionSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion"


class Deconnexion(APIView):
    """POST {refresh} : révoque le jeton de rafraîchissement (liste noire)."""

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangerMotDePasse(APIView):
    def post(self, request):
        u = request.user
        if not u.check_password(request.data.get("ancien", "")):
            return Response({"detail": "Mot de passe actuel incorrect."}, status=400)
        nouveau = request.data.get("nouveau", "")
        try:
            password_validation.validate_password(nouveau, u)
        except ValidationError as e:
            return Response({"detail": " ".join(e.messages)}, status=400)
        u.set_password(nouveau)
        u.doit_changer_mdp = False
        u.save()
        return Response({"detail": "Mot de passe modifié."})


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------
class Moi(APIView):
    def get(self, request):
        u = request.user
        tel = u.telephone or ""
        chiffres = "".join(ch for ch in tel if ch.isdigit())
        masque = f"+{chiffres[:3]} {chiffres[3:5]} •• •• {chiffres[-4:-2]} {chiffres[-2:]}" if len(chiffres) >= 10 else ""
        eleves = list(eleves_visibles(u)) if (u.est_parent or u.est_eleve) else []
        return Response({
            "id": u.pk,
            "username": u.username,
            "prenom": u.first_name,
            "nom": u.last_name,
            "initiales": D.initiales(u),
            "role": u.role,
            "email": u.email,
            "telephone_masque": masque,
            "doit_changer_mdp": u.doit_changer_mdp,
            "etablissement": {"nom": settings.ETABLISSEMENT_NOM, "annee": str(annee_active() or "")},
            "enfants": [D.eleve_resume(e) for e in eleves],
            "preferences_push": u.preferences_push or {},
        })


class PreferencesPush(APIView):
    def put(self, request):
        prefs = {k: bool(v) for k, v in (request.data or {}).items() if k in Notification.Type.values}
        request.user.preferences_push = prefs
        request.user.save(update_fields=["preferences_push"])
        return Response(prefs)


class Appareils(APIView):
    """Enregistre (POST) ou supprime (DELETE) le jeton Expo Push de l'appareil."""

    def post(self, request):
        jeton = str(request.data.get("jeton", ""))[:200]
        if not jeton.startswith(("ExponentPushToken[", "ExpoPushToken[")):
            return Response({"detail": "Jeton invalide."}, status=400)
        AppareilPush.objects.update_or_create(
            jeton=jeton, defaults={"utilisateur": request.user, "plateforme": str(request.data.get("plateforme", ""))[:10]}
        )
        return Response(status=201)

    def delete(self, request):
        AppareilPush.objects.filter(utilisateur=request.user, jeton=request.data.get("jeton", "")).delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Élève : accueil, emploi du temps, notes, devoirs, absences
# ---------------------------------------------------------------------------
class Accueil(APIView):
    def get(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        p = periode_courante()
        notes = D.notes_eleve(e, p) if p else None
        devoirs = D.devoirs_eleve(e, depuis_jours=7)
        a_rendre = [d for d in devoirs if d["statut"] in ("a_faire", "en_cours", "en_retard")]
        demain = (timezone.localdate() + timedelta(days=1)).isoformat()
        abs_ = D.absences_eleve(e)
        evolution = notes["evolution"] if notes else []
        evts = Evenement.objects.filter(debut__gte=timezone.now()).filter(Q(classe__isnull=True) | Q(classe=e.classe))[:4]
        return Response({
            "eleve": D.eleve_resume(e),
            "moyenne": {
                "valeur": notes["moyenne_generale"] if notes else None,
                "classe": notes["moyenne_classe"] if notes else None,
                "rang": notes["rang"] if notes else None,
                "effectif": notes["effectif"] if notes else 0,
                "periode": p.nom if p else "",
                "evolution": round(evolution[-1]["moyenne"] - evolution[-2]["moyenne"], 2) if len(evolution) >= 2 else None,
            },
            "prochaine_echeance": next((d for d in a_rendre if d["statut"] != "en_retard"), None),
            "absences": {
                "absences": abs_["stats"]["absences"],
                "retards": abs_["stats"]["retards"],
                "a_justifier": abs_["stats"]["non_justifiees"],
            },
            "devoirs": {"a_rendre": len(a_rendre), "urgents": len([d for d in a_rendre if d["pour_le"] <= demain])},
            "devoirs_urgents": [d for d in a_rendre if d["pour_le"] <= demain][:5],
            "dernieres_notes": D.dernieres_notes(e, 4),
            "cours_du_jour": D.cours_du_jour(e),
            "notifications": D.notifications_importantes(request.user),
            "evenements": [evenement_json(x) for x in evts],
        })


class EmploiDuTemps(APIView):
    def get(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        try:
            jour = Date.fromisoformat(request.query_params.get("semaine", ""))
        except ValueError:
            jour = timezone.localdate()
        return Response(D.semaine_eleve(e, lundi_de(jour)))


class Notes(APIView):
    def get(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        pid = request.query_params.get("periode")
        p = periodes_actives().filter(pk=pid).first() if pid and pid.isdigit() else periode_courante()
        return Response(D.notes_eleve(e, p))


class Devoirs(APIView):
    def get(self, request, eleve_id):
        return Response(D.devoirs_eleve(eleve_autorise(request, eleve_id), depuis_jours=30))


class StatutDevoir(APIView):
    """POST {statut: a_faire|en_cours|termine} — réservé à l'élève lui-même."""

    def post(self, request, devoir_id):
        if not request.user.est_eleve:
            raise PermissionDenied
        eleve = request.user.eleve
        devoir = get_object_or_404(Devoir, pk=devoir_id, enseignement__classe=eleve.classe)
        statut = request.data.get("statut")
        if statut == "a_faire":
            DevoirFait.objects.filter(devoir=devoir, eleve=eleve).delete()
        elif statut in ("en_cours", "termine"):
            DevoirFait.objects.update_or_create(
                devoir=devoir, eleve=eleve,
                defaults={"statut": DevoirFait.Statut.EN_COURS if statut == "en_cours" else DevoirFait.Statut.TERMINE},
            )
        else:
            return Response({"detail": "Statut invalide."}, status=400)
        return Response({"statut": statut})


class Absences(APIView):
    def get(self, request, eleve_id):
        return Response(D.absences_eleve(eleve_autorise(request, eleve_id)))


class JustifierAbsence(APIView):
    """POST multipart {motif, justificatif?} — parent de l'élève uniquement."""

    def post(self, request, absence_id):
        a = get_object_or_404(Absence.objects.select_related("eleve"), pk=absence_id)
        if not (request.user.est_parent and request.user.enfants.filter(pk=a.eleve_id).exists()):
            raise PermissionDenied
        if not a.est_justifiable:
            return Response({"detail": "Cette absence est déjà justifiée ou en cours de traitement."}, status=400)
        motif = str(request.data.get("motif", "")).strip()[:500]
        if len(motif) < 3:
            return Response({"detail": "Indiquez le motif."}, status=400)
        fichier = request.FILES.get("justificatif")
        if fichier:
            try:
                valider_justificatif(fichier)
            except ValidationError as e:
                return Response({"detail": " ".join(e.messages)}, status=400)
            a.justificatif = fichier
        a.motif = motif
        a.statut = Absence.Statut.EN_ATTENTE
        a.justifiee_par = request.user
        a.justifiee_le = timezone.now()
        a.save()
        notifier(User.objects.filter(role=User.Role.ADMIN, is_active=True), Notification.Type.ABSENCE,
                 f"Justificatif à valider : {a.eleve} ({a.date:%d/%m})", lien="/absences/administration/?statut=EN_ATTENTE")
        return Response({"statut": a.statut})


class DeclarerAbsence(APIView):
    """POST {date, motif, commentaire} — un parent prévient d'une absence à venir (journée)."""

    def post(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        if not request.user.est_parent:
            raise PermissionDenied
        try:
            jour = Date.fromisoformat(str(request.data.get("date")))
        except ValueError:
            return Response({"detail": "Date invalide."}, status=400)
        if jour < timezone.localdate():
            return Response({"detail": "La date doit être aujourd'hui ou à venir."}, status=400)
        motif = (str(request.data.get("motif", "")) + " — " + str(request.data.get("commentaire", ""))).strip(" —")[:500]
        a, _ = Absence.objects.update_or_create(
            eleve=e, date=jour, creneau=None,
            defaults={"type": Absence.Type.ABSENCE, "statut": Absence.Statut.EN_ATTENTE, "motif": motif,
                      "saisie_par": request.user, "justifiee_par": request.user, "justifiee_le": timezone.now()},
        )
        fichier = request.FILES.get("justificatif")
        if fichier:
            try:
                valider_justificatif(fichier)
            except ValidationError as err:
                return Response({"detail": " ".join(err.messages)}, status=400)
            a.justificatif = fichier
            a.save(update_fields=["justificatif"])
        notifier(User.objects.filter(role=User.Role.ADMIN, is_active=True), Notification.Type.ABSENCE,
                 f"Absence déclarée : {e} le {jour:%d/%m}", lien="/absences/administration/?statut=EN_ATTENTE")
        return Response({"id": a.pk}, status=201)


# ---------------------------------------------------------------------------
# Messagerie
# ---------------------------------------------------------------------------
def message_json(m, user, lectures):
    autres = [d for uid, d in lectures.items() if uid != m.auteur_id]
    lu = bool(autres) and all(d is not None and d >= m.envoye_le for d in autres)
    return {
        "id": m.pk,
        "auteur": str(m.auteur) if m.auteur else "Compte supprimé",
        "de_moi": m.auteur_id == user.pk,
        "texte": m.corps,
        "date": m.envoye_le.isoformat(),
        "lu": lu,
        "piece_jointe": m.piece_jointe.name.rsplit("/", 1)[-1] if m.piece_jointe else None,
    }


def contact_json(u):
    detail = u.get_role_display()
    if u.est_enseignant:
        matieres = sorted({e.matiere.nom for e in u.enseignements.select_related("matiere")})
        if matieres:
            detail = ", ".join(matieres[:2])
    return {"id": u.pk, "nom": str(u), "initiales": D.initiales(u), "role": u.role, "detail": detail}


class Conversations(APIView):
    def get(self, request):
        u = request.user
        lectures = {p.conversation_id: p.derniere_lecture for p in Participation.objects.filter(utilisateur=u)}
        sortie = []
        for c in conversations_de(u).prefetch_related("participants")[:100]:
            dernier = c.messages.order_by("-envoye_le").select_related("auteur").first()
            lu = lectures.get(c.pk)
            sortie.append({
                "id": c.pk,
                "sujet": c.sujet,
                "interlocuteurs": [contact_json(x) for x in c.participants.all() if x.pk != u.pk],
                "dernier_message": {"texte": dernier.corps, "date": dernier.envoye_le.isoformat(), "de_moi": dernier.auteur_id == u.pk} if dernier else None,
                "non_lu": lu is None or c.dernier_message_le > lu,
            })
        return Response(sortie)

    def post(self, request):
        ids = request.data.get("destinataires") or []
        sujet = str(request.data.get("sujet", "")).strip()[:150]
        texte = str(request.data.get("texte", "")).strip()[:5000]
        if not (ids and sujet and texte):
            return Response({"detail": "Destinataire, sujet et message sont obligatoires."}, status=400)
        dest = list(User.objects.filter(pk__in=ids, is_active=True))
        conv = creer_conversation(request.user, dest, sujet, texte)
        return Response({"id": conv.pk}, status=201)


class Contacts(APIView):
    def get(self, request):
        return Response([contact_json(u) for u in destinataires_autorises(request.user).order_by("role", "last_name")[:300]])


class ConversationDetail(APIView):
    def get(self, request, conv_id):
        conv = get_object_or_404(Conversation, pk=conv_id)
        verifier_participant(request.user, conv)
        marquer_lue(conv, request.user)
        Notification.objects.filter(destinataire=request.user, lien=f"/messagerie/{conv.pk}/", lue=False).update(lue=True)
        lectures = {p.utilisateur_id: p.derniere_lecture for p in conv.participations.all()}
        return Response({
            "id": conv.pk,
            "sujet": conv.sujet,
            "interlocuteurs": [contact_json(x) for x in conv.participants.exclude(pk=request.user.pk)],
            "messages": [message_json(m, request.user, lectures) for m in conv.messages.select_related("auteur")],
        })

    def post(self, request, conv_id):
        """Nouveau message (texte et/ou pièce jointe en multipart)."""
        conv = get_object_or_404(Conversation, pk=conv_id)
        texte = str(request.data.get("texte", "")).strip()[:5000]
        fichier = request.FILES.get("piece_jointe")
        if not texte and not fichier:
            return Response({"detail": "Message vide."}, status=400)
        if fichier:
            try:
                valider_justificatif(fichier)
            except ValidationError as e:
                return Response({"detail": " ".join(e.messages)}, status=400)
        msg = repondre(conv, request.user, texte or "Pièce jointe")
        if fichier:
            msg.piece_jointe = fichier
            msg.save(update_fields=["piece_jointe"])
        lectures = {p.utilisateur_id: p.derniere_lecture for p in conv.participations.all()}
        return Response(message_json(msg, request.user, lectures), status=201)


# ---------------------------------------------------------------------------
# Notifications et vie scolaire
# ---------------------------------------------------------------------------
class Notifications(APIView):
    def get(self, request):
        return Response([D.notification_json(n) for n in Notification.objects.filter(destinataire=request.user)[:100]])


class LireNotifications(APIView):
    """POST {ids: [..]} ou {tout: true}."""

    def post(self, request):
        qs = Notification.objects.filter(destinataire=request.user, lue=False)
        if not request.data.get("tout"):
            qs = qs.filter(pk__in=request.data.get("ids") or [])
        n = qs.update(lue=True)
        return Response({"lues": n})


def evenement_json(e):
    return {
        "id": e.pk,
        "titre": e.titre,
        "type": e.type,
        "debut": e.debut.isoformat(),
        "fin": e.fin.isoformat() if e.fin else None,
        "lieu": e.lieu,
        "description": e.description,
    }


class VieScolaire(APIView):
    def get(self, request):
        u = request.user
        classes = set()
        if u.est_eleve and hasattr(u, "eleve"):
            classes.add(u.eleve.classe_id)
        elif u.est_parent:
            classes |= set(u.enfants.values_list("classe_id", flat=True))
        filtre = Q(classe__isnull=True) | Q(classe_id__in=classes) if not (u.est_admin or u.est_enseignant) else Q()
        annonces = annonces_visibles(u)[:30]
        return Response({
            "annonces": [{"id": a.pk, "titre": a.titre, "contenu": a.contenu, "date": a.publiee_le.isoformat(), "importante": a.importante} for a in annonces],
            "evenements": [evenement_json(e) for e in Evenement.objects.filter(filtre).filter(debut__gte=timezone.now() - timedelta(days=60))[:60]],
            "documents": [{"id": d.pk, "titre": d.titre, "date": d.publie_le.isoformat()} for d in DocumentEtablissement.objects.filter(filtre)[:50]],
        })


# ---------------------------------------------------------------------------
# Frais et paiements
# ---------------------------------------------------------------------------
def paiement_json(p):
    return {
        "id": p.pk,
        "frais": p.frais.libelle,
        "montant": p.montant,
        "moyen": p.moyen,
        "moyen_libelle": p.get_moyen_display(),
        "statut": p.statut,
        "reference": p.reference,
        "numero_recu": p.numero_recu,
        "date": (p.confirme_le or p.cree_le).isoformat(),
    }


class Frais(APIView):
    def get(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        frais = list(FraisScolarite.objects.filter(eleve=e, annee=annee_active()).prefetch_related("paiements"))
        total = sum(f.montant for f in frais)
        paye = sum(f.paye for f in frais)
        aujourd_hui = timezone.localdate()
        return Response({
            "total": total,
            "paye": paye,
            "reste": total - paye,
            "echeances": [{
                "id": f.pk, "libelle": f.libelle, "categorie": f.categorie, "montant": f.montant, "reste": f.reste,
                "echeance": f.echeance.isoformat(),
                "statut": "payee" if f.reste == 0 else "en_retard" if f.echeance < aujourd_hui else "a_venir",
            } for f in frais],
            "paiements": [paiement_json(p) for p in Paiement.objects.filter(frais__in=frais).exclude(statut=Paiement.Statut.ANNULE).select_related("frais")],
        })


class Payer(APIView):
    """POST {frais_id, moyen, telephone} — réservé aux parents de l'élève."""

    def post(self, request, eleve_id):
        e = eleve_autorise(request, eleve_id)
        if not request.user.est_parent:
            raise PermissionDenied
        frais = get_object_or_404(FraisScolarite, pk=request.data.get("frais_id"), eleve=e)
        moyen = request.data.get("moyen")
        if moyen not in Paiement.Moyen.values or moyen == Paiement.Moyen.ESPECES:
            return Response({"detail": "Moyen de paiement invalide."}, status=400)
        if frais.reste == 0:
            return Response({"detail": "Ces frais sont déjà réglés."}, status=400)
        p = Paiement.objects.create(
            frais=frais, payeur=request.user, montant=frais.reste, moyen=moyen,
            telephone=str(request.data.get("telephone", ""))[:20],
        )
        instructions = fournisseur().initier(p)
        return Response({"paiement": paiement_json(p), "instructions": instructions}, status=201)


class PaiementDetail(APIView):
    """GET : vérifie le statut auprès du fournisseur (l'app interroge jusqu'à confirmation)."""

    def get(self, request, paiement_id):
        p = get_object_or_404(Paiement.objects.select_related("frais"), pk=paiement_id, payeur=request.user)
        fournisseur().verifier(p)
        p.refresh_from_db()
        return Response(paiement_json(p))


# ---------------------------------------------------------------------------
# Liens de téléchargement signés (valables quelques minutes)
# ---------------------------------------------------------------------------
SEL = "notepro.fichier"


class LienFichier(APIView):
    """GET ?type=bulletin|recu|document|devoir|message|justificatif&id=..&periode=.. -> {url}"""

    def get(self, request):
        t, oid = request.query_params.get("type"), request.query_params.get("id", "")
        u = request.user
        if not oid.isdigit():
            raise Http404
        oid = int(oid)
        extra = ""
        if t == "bulletin":
            from bulletins.services import est_publie

            e = eleve_autorise(request, oid)
            p = get_object_or_404(Periode, pk=request.query_params.get("periode"))
            if (u.est_eleve or u.est_parent) and not (e.classe and est_publie(e.classe, p)):
                raise PermissionDenied("Bulletin non publié.")
            extra = str(p.pk)
        elif t == "recu":
            get_object_or_404(Paiement, pk=oid, statut=Paiement.Statut.CONFIRME, frais__eleve__in=eleves_visibles(u))
        elif t == "document":
            get_object_or_404(DocumentEtablissement, pk=oid)
        elif t == "devoir":
            d = get_object_or_404(Devoir, pk=oid)
            if not (u.est_admin or u.est_enseignant or eleves_visibles(u).filter(classe=d.enseignement.classe_id).exists()):
                raise PermissionDenied
        elif t == "message":
            m = get_object_or_404(Message, pk=oid)
            verifier_participant(u, m.conversation)
        elif t == "justificatif":
            a = get_object_or_404(Absence, pk=oid)
            if not (u.est_admin or (u.est_parent and u.enfants.filter(pk=a.eleve_id).exists())):
                raise PermissionDenied
        else:
            raise Http404
        jeton = signing.dumps({"t": t, "id": oid, "x": extra, "u": u.pk}, salt=SEL)
        return Response({"url": request.build_absolute_uri(f"/api/fichiers/{jeton}/")})


class Fichier(APIView):
    """Sert le fichier désigné par un jeton signé (aucune autre authentification : le jeton fait foi)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, jeton):
        try:
            d = signing.loads(jeton, salt=SEL, max_age=settings.LIEN_FICHIER_SECONDES)
        except signing.BadSignature:
            raise Http404("Lien expiré ou invalide.")
        user = User.objects.filter(pk=d["u"], is_active=True).first()
        if user is None:
            raise Http404
        request.user = user
        t, oid = d["t"], d["id"]
        tracer(request, JournalAcces.Action.TELECHARGEMENT, f"{t} #{oid} (app mobile)")
        if t == "bulletin":
            from bulletins.pdf import generer_pdf
            from bulletins.services import donnees_bulletins

            e = get_object_or_404(Eleve, pk=oid)
            p = get_object_or_404(Periode, pk=int(d["x"]))
            r = HttpResponse(generer_pdf(donnees_bulletins(e.classe, p, eleves=[e])), content_type="application/pdf")
            r["Content-Disposition"] = f'inline; filename="bulletin-{p.nom}.pdf"'
            return r
        if t == "recu":
            from finances.recu import recu_pdf

            p = get_object_or_404(Paiement, pk=oid)
            r = HttpResponse(recu_pdf(p), content_type="application/pdf")
            r["Content-Disposition"] = f'inline; filename="recu-{p.numero_recu}.pdf"'
            return r
        champ = {
            "document": (DocumentEtablissement, "fichier"),
            "devoir": (Devoir, "piece_jointe"),
            "message": (Message, "piece_jointe"),
            "justificatif": (Absence, "justificatif"),
        }.get(t)
        if not champ:
            raise Http404
        obj = get_object_or_404(champ[0], pk=oid)
        f = getattr(obj, champ[1])
        if not f:
            raise Http404
        return FileResponse(f.open("rb"), filename=f.name.rsplit("/", 1)[-1])
