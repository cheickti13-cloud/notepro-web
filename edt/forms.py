from django import forms

from accounts.models import User
from scolarite.models import Salle
from scolarite.services import annee_active

from .models import Creneau, ModificationCours


class ModificationCoursForm(forms.ModelForm):
    class Meta:
        model = ModificationCours
        fields = ["creneau", "date", "type", "nouvelle_salle", "remplacant", "motif"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        annee = annee_active()
        self.fields["creneau"].queryset = Creneau.objects.filter(
            enseignement__classe__annee=annee
        ).select_related("enseignement__matiere", "enseignement__classe", "enseignement__enseignant")
        self.fields["remplacant"].queryset = User.objects.filter(role=User.Role.ENSEIGNANT, is_active=True)
        self.fields["nouvelle_salle"].queryset = Salle.objects.all()
