from django import forms

from .models import ContenuSeance, Devoir

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class ContenuSeanceForm(forms.ModelForm):
    class Meta:
        model = ContenuSeance
        fields = ["date", "titre", "contenu"]
        widgets = {"date": DATE}


class DevoirForm(forms.ModelForm):
    class Meta:
        model = Devoir
        fields = ["donne_le", "pour_le", "titre", "description", "duree_estimee"]
        widgets = {"donne_le": DATE, "pour_le": DATE, "description": forms.Textarea(attrs={"rows": 4})}
