from django import forms

from .models import Annonce


class NouveauMessageForm(forms.Form):
    destinataires = forms.ModelMultipleChoiceField(queryset=None, help_text="Ctrl/Cmd + clic pour en choisir plusieurs.")
    sujet = forms.CharField(max_length=150)
    corps = forms.CharField(label="Message", widget=forms.Textarea(attrs={"rows": 6}), max_length=5000)

    def __init__(self, *args, destinataires_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destinataires"].queryset = destinataires_qs
        self.fields["destinataires"].label_from_instance = lambda u: f"{u} — {u.get_role_display()}"
        self.fields["destinataires"].widget.attrs["size"] = 10


class ReponseForm(forms.Form):
    corps = forms.CharField(label="Votre réponse", widget=forms.Textarea(attrs={"rows": 4}), max_length=5000)


class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = ["titre", "contenu", "pour_eleves", "pour_parents", "pour_enseignants", "classe", "importante"]
        widgets = {"contenu": forms.Textarea(attrs={"rows": 6})}

    def clean(self):
        d = super().clean()
        if not (d.get("pour_eleves") or d.get("pour_parents") or d.get("pour_enseignants")):
            raise forms.ValidationError("Choisissez au moins un public.")
        return d
