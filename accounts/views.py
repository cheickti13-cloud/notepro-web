import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from core.audit import tracer
from core.models import JournalAcces

from .forms import ChangementMdpForm, ConnexionForm, PreferencesForm
from .rgpd import exporter_donnees_utilisateur


class Connexion(LoginView):
    template_name = "accounts/login.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


connexion = login_not_required(Connexion.as_view())
deconnexion = LogoutView.as_view()  # POST uniquement (Django 5)


class ChangementMdp(PasswordChangeView):
    template_name = "accounts/changer_mdp.html"
    form_class = ChangementMdpForm
    success_url = reverse_lazy("dashboard:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.user
        user.doit_changer_mdp = False
        user.save(update_fields=["doit_changer_mdp"])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Mot de passe modifié.")
        return response


changer_mdp = ChangementMdp.as_view()


def mon_compte(request):
    user = request.user
    if request.method == "POST":
        form = PreferencesForm(request.POST)
        if form.is_valid():
            user.notifications_email = form.cleaned_data["notifications_email"]
            user.save(update_fields=["notifications_email"])
            messages.success(request, "Préférences enregistrées.")
            return redirect("accounts:mon_compte")
    else:
        form = PreferencesForm(initial={"notifications_email": user.notifications_email})
    contexte = {
        "form": form,
        "enfants": user.enfants.select_related("user", "classe") if user.est_parent else None,
    }
    return render(request, "accounts/mon_compte.html", contexte)


@require_POST
def exporter_mes_donnees(request):
    """Droit d'accès et à la portabilité (RGPD art. 15 et 20) : export JSON."""
    donnees = exporter_donnees_utilisateur(request.user)
    tracer(request, JournalAcces.Action.EXPORT, f"export de ses données ({request.user.username})")
    reponse = HttpResponse(
        json.dumps(donnees, ensure_ascii=False, indent=2, default=str),
        content_type="application/json; charset=utf-8",
    )
    reponse["Content-Disposition"] = 'attachment; filename="mes-donnees-notepro.json"'
    return reponse
