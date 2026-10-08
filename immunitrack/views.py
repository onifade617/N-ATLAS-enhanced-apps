from datetime import date

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import profile_required
from core.models import Child

from .models import Immunization, Vaccine
from .services import grouped_schedule, next_due


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ["name", "sex", "date_of_birth"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sex": forms.Select(attrs={"class": "form-select"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        if dob > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return dob


@profile_required
def overview(request, profile):
    today = date.today()
    kids = [{"child": c, "next": next_due(c, today)} for c in profile.children.all() if c.is_under_five]
    return render(request, "immunitrack/overview.html", {"kids": kids, "vaccines": Vaccine.objects.all()})


@profile_required
def add_child(request, profile):
    form = ChildForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        child = form.save(commit=False)
        child.caregiver = profile
        child.save()
        messages.success(request, f"{child.name} added. Here is the personal vaccine schedule.")
        return redirect("immunitrack_child", pk=child.pk)
    return render(request, "immunitrack/child_form.html", {"form": form})


@profile_required
def child_detail(request, profile, pk):
    child = get_object_or_404(Child, pk=pk, caregiver=profile)
    return render(
        request,
        "immunitrack/child_detail.html",
        {"child": child, "groups": grouped_schedule(child), "next": next_due(child), "today": date.today()},
    )


@require_POST
@profile_required
def record_vaccine(request, profile, pk):
    child = get_object_or_404(Child, pk=pk, caregiver=profile)
    vaccine = get_object_or_404(Vaccine, pk=request.POST.get("vaccine"))
    try:
        given = date.fromisoformat(request.POST.get("given_date") or date.today().isoformat())
    except ValueError:
        given = date.today()
    if given < child.date_of_birth or given > date.today():
        messages.error(request, "The vaccine date must be between the date of birth and today.")
    else:
        Immunization.objects.update_or_create(
            child=child, vaccine=vaccine, defaults={"given_date": given, "recorded_by": profile}
        )
        messages.success(request, f"{vaccine.name} recorded for {child.name}.")
    return redirect("immunitrack_child", pk=child.pk)
