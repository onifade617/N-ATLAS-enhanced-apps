from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import profile_required

from .guidance import TRIMESTER_GUIDANCE, week_message
from .models import ANCVisit, DangerSign, Milestone, Pregnancy


class PregnancyForm(forms.ModelForm):
    class Meta:
        model = Pregnancy
        fields = ["lmp_date"]
        widgets = {"lmp_date": forms.DateInput(attrs={"type": "date", "class": "form-control"})}
        help_texts = {"lmp_date": "If you are not sure, a health worker can estimate it from a scan or exam."}

    def clean_lmp_date(self):
        lmp = self.cleaned_data["lmp_date"]
        today = date.today()
        if lmp > today:
            raise forms.ValidationError("This date cannot be in the future.")
        if lmp < today - timedelta(weeks=44):
            raise forms.ValidationError("That is more than 44 weeks ago — please check the date.")
        return lmp


@profile_required
def overview(request, profile):
    preg = profile.active_pregnancy
    ctx = {"pregnancy": preg, "danger_signs": DangerSign.objects.all()}
    if preg:
        ctx.update(
            visits=preg.visits.all(),
            week_message=week_message(preg.weeks),
            trimester_tips=TRIMESTER_GUIDANCE[preg.trimester],
        )
    kids = []
    for child in profile.children.all():
        if child.is_under_five:
            months = child.age_days() * 12 // 365
            kids.append(
                {
                    "child": child,
                    "now": Milestone.objects.filter(age_months__lte=max(months, 1)).order_by("-age_months")[:4],
                    "next": Milestone.objects.filter(age_months__gt=months).order_by("age_months")[:3],
                }
            )
    ctx["kids"] = kids
    return render(request, "mamacare/overview.html", ctx)


@profile_required
def add_pregnancy(request, profile):
    form = PregnancyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile.pregnancies.filter(active=True).update(active=False)
        preg = form.save(commit=False)
        preg.profile = profile
        preg.save()
        messages.success(request, f"Pregnancy added. Your expected delivery date is {preg.edd:%d %B %Y}.")
        return redirect("mamacare")
    return render(request, "mamacare/pregnancy_form.html", {"form": form})


@require_POST
@profile_required
def end_pregnancy(request, profile, pk):
    preg = get_object_or_404(Pregnancy, pk=pk, profile=profile)
    preg.active = False
    preg.save(update_fields=["active"])
    messages.success(request, "Congratulations! Add your baby in ImmuniTrack to start their vaccine schedule.")
    return redirect("immunitrack_add_child")


@require_POST
@profile_required
def mark_visit(request, profile, pk):
    visit = get_object_or_404(ANCVisit, pk=pk, pregnancy__profile=profile)
    visit.attended_date = None if visit.attended_date else date.today()
    visit.save(update_fields=["attended_date"])
    return redirect("mamacare")
