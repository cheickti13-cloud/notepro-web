from django import forms

from accounts.models import Eleve
from edt.models import Creneau
from scolarite.models import Classe
from scolarite.services import annee_active

from .models import Absence


class JustificationForm(forms.ModelForm):
    """Formulaire du parent : un motif est obligatoire, le document est facultatif."""

    class Meta:
        model = Absence
        fields = ["motif", "justificatif"]
        widgets = {"motif": forms.Textarea(attrs={"rows": 3, "maxlength": 500})}
        labels = {"motif": "Motif de l'absence", "justificatif": "Document justificatif (PDF, PNG ou JPG, 5 Mo max.)"}

    def clean_motif(self):
        motif = (self.cleaned_data.get("motif") or "").strip()
        if len(motif) < 3:
            raise forms.ValidationError("Indiquez le motif de l'absence.")
        return motif[:500]


class SaisieAdminForm(forms.ModelForm):
    """Saisie directe par la vie scolaire (absence à la journée, oubli d'appel...)."""

    class Meta:
        model = Absence
        fields = ["eleve", "date", "creneau", "type", "minutes_retard", "statut", "motif"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "motif": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annee = annee_active()
        self.fields["eleve"].queryset = Eleve.objects.filter(classe__annee=annee).select_related("user", "classe")
        self.fields["eleve"].label_from_instance = lambda e: f"{e} ({e.classe})"
        self.fields["creneau"].queryset = Creneau.objects.filter(enseignement__classe__annee=annee).select_related(
            "enseignement__matiere", "enseignement__classe"
        )
        self.fields["creneau"].required = False

    def clean(self):
        donnees = super().clean()
        eleve, creneau = donnees.get("eleve"), donnees.get("creneau")
        if eleve and creneau and creneau.enseignement.classe_id != eleve.classe_id:
            raise forms.ValidationError("Ce cours n'est pas celui de la classe de l'élève.")
        return donnees


class TraitementForm(forms.Form):
    decision = forms.ChoiceField(choices=[("JUSTIFIEE", "Valider"), ("REFUSEE", "Refuser")])
    commentaire = forms.CharField(max_length=200, required=False)


class FiltreAdminForm(forms.Form):
    debut = forms.DateField(required=False, label="Du", widget=forms.DateInput(attrs={"type": "date"}))
    fin = forms.DateField(required=False, label="Au", widget=forms.DateInput(attrs={"type": "date"}))
    classe = forms.ModelChoiceField(queryset=Classe.objects.none(), required=False)
    type = forms.ChoiceField(choices=[("", "Tous")] + list(Absence.Type.choices), required=False)
    statut = forms.ChoiceField(choices=[("", "Tous")] + list(Absence.Statut.choices), required=False)
    eleve = forms.CharField(required=False, label="Nom de l'élève")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classe"].queryset = Classe.objects.filter(annee=annee_active())
