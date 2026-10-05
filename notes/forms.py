from django import forms

from scolarite.services import periodes_actives

from .models import Evaluation


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ["titre", "periode", "date", "bareme", "coefficient", "publiee"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periode"].queryset = periodes_actives()
