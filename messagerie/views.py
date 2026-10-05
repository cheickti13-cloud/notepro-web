from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.permissions import R, role_requis

from .forms import AnnonceForm, NouveauMessageForm, ReponseForm
from .models import Conversation, Notification, Participation
from .services import (
    annonces_visibles,
    conversations_de,
    creer_conversation,
    destinataires_autorises,
    marquer_lue,
    publier_annonce,
    repondre,
    verifier_participant,
)


def boite(request):
    parts = {
        p.conversation_id: p
        for p in Participation.objects.filter(utilisateur=request.user)
    }
    conversations = []
    for c in conversations_de(request.user):
        p = parts.get(c.pk)
        c.non_lu = p is not None and (p.derniere_lecture is None or c.dernier_message_le > p.derniere_lecture)
        c.autres = [u for u in c.participants.all() if u.pk != request.user.pk]
        conversations.append(c)
    return render(request, "messagerie/boite.html", {"conversations": conversations})


def nouveau(request):
    qs = destinataires_autorises(request.user).order_by("role", "last_name")
    initial = {}
    # Pré-remplissage : /messagerie/nouveau/?a=<id> (ex. « écrire au professeur »)
    a = request.GET.get("a")
    if a and a.isdigit() and qs.filter(pk=int(a)).exists():
        initial["destinataires"] = [int(a)]
    if request.method == "POST":
        form = NouveauMessageForm(request.POST, destinataires_qs=qs)
        if form.is_valid():
            try:
                conv = creer_conversation(
                    request.user, list(form.cleaned_data["destinataires"]), form.cleaned_data["sujet"], form.cleaned_data["corps"]
                )
            except PermissionDenied as exc:
                form.add_error("destinataires", str(exc))
            else:
                messages.success(request, "Message envoyé.")
                return redirect("messagerie:conversation", pk=conv.pk)
    else:
        form = NouveauMessageForm(destinataires_qs=qs, initial=initial)
    return render(request, "messagerie/nouveau.html", {"form": form})


def conversation(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    verifier_participant(request.user, conv)  # 403 si non participant
    if request.method == "POST":
        form = ReponseForm(request.POST)
        if form.is_valid():
            repondre(conv, request.user, form.cleaned_data["corps"])
            return redirect("messagerie:conversation", pk=conv.pk)
    else:
        form = ReponseForm()
    marquer_lue(conv, request.user)
    Notification.objects.filter(destinataire=request.user, lien=f"/messagerie/{conv.pk}/", lue=False).update(lue=True)
    contexte = {
        "conv": conv,
        "messages_conv": conv.messages.select_related("auteur"),
        "participants": conv.participants.all(),
        "form": form,
    }
    return render(request, "messagerie/conversation.html", contexte)


@require_POST
def archiver(request, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    p = verifier_participant(request.user, conv)
    p.archivee = True
    p.save(update_fields=["archivee"])
    messages.info(request, "Conversation archivée (elle réapparaîtra si quelqu'un répond).")
    return redirect("messagerie:boite")


def notifications(request):
    notifs = Notification.objects.filter(destinataire=request.user)[:100]
    return render(request, "messagerie/notifications.html", {"notifications": notifs})


@require_POST
def ouvrir_notification(request, pk):
    n = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    n.lue = True
    n.save(update_fields=["lue"])
    # Seuls les liens internes sont suivis (protection contre les redirections ouvertes)
    if n.lien and url_has_allowed_host_and_scheme(n.lien, allowed_hosts={request.get_host()}) and n.lien.startswith("/"):
        return HttpResponseRedirect(n.lien)
    return redirect("messagerie:notifications")


@require_POST
def tout_marquer_lu(request):
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    return redirect("messagerie:notifications")


def annonces(request):
    return render(request, "messagerie/annonces.html", {"annonces": annonces_visibles(request.user)[:50]})


@role_requis(R.ADMIN)
def nouvelle_annonce(request):
    if request.method == "POST":
        form = AnnonceForm(request.POST)
        if form.is_valid():
            annonce = form.save(commit=False)
            annonce.auteur = request.user
            annonce.save()
            publier_annonce(annonce)
            messages.success(request, "Annonce publiée et notifiée.")
            return redirect("messagerie:annonces")
    else:
        form = AnnonceForm()
    return render(request, "messagerie/annonce_form.html", {"form": form})
