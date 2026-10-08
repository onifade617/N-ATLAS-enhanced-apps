from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import LANGUAGES, LGA, SERVICES, Profile, State

CONSENT_TEXT = (
    "I agree that Lafiya AI may store my health information to send me reminders and alerts. "
    "My data is used only in aggregated, anonymous form for planning, and I can download or delete it at any time "
    "(Nigeria Data Protection Act 2023)."
)


def grouped_lga_choices():
    """LGAs grouped by state for <optgroup>s (all 36 states + FCT, 774 LGAs)."""
    choices = [("", "Select your LGA")]
    for state in State.objects.prefetch_related("lgas").order_by("name"):
        choices.append((state.name, [(lga.id, lga.name) for lga in state.lgas.all()]))
    return choices


class StyledMixin:
    def _style(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class SignupForm(StyledMixin, UserCreationForm):
    full_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=20, required=False)
    language = forms.ChoiceField(choices=LANGUAGES, help_text="Lafiya will talk to you in this language.")
    lga = forms.ModelChoiceField(queryset=LGA.objects.all(), label="LGA")
    has_hypertension = forms.BooleanField(required=False, label="I have high blood pressure")
    has_diabetes = forms.BooleanField(required=False, label="I have diabetes")
    consent = forms.BooleanField(required=True, label=CONSENT_TEXT)

    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lga"].choices = grouped_lga_choices()
        self.fields["lga"].widget.attrs["data-lga-picker"] = "1"
        self._style()


class ProfileForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "phone", "language", "lga", "has_hypertension", "has_diabetes"]
        labels = {"lga": "LGA", "has_hypertension": "I have high blood pressure", "has_diabetes": "I have diabetes"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lga"].choices = grouped_lga_choices()
        self.fields["lga"].widget.attrs["data-lga-picker"] = "1"
        self.fields["lga"].required = True
        self._style()


class FacilitySearchForm(StyledMixin, forms.Form):
    service = forms.ChoiceField(choices=[("", "Any service")] + SERVICES, required=False)
    open_now = forms.BooleanField(required=False, label="Open now")
    lat = forms.FloatField(required=False, widget=forms.HiddenInput)
    lon = forms.FloatField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
