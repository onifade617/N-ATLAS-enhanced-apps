from datetime import date, timedelta

from django.db import models

from core.models import Facility, Profile

# WHO 2016 ANC model: 8 contacts, at these gestational weeks.
ANC_CONTACT_WEEKS = [12, 20, 26, 30, 34, 36, 38, 40]


class Pregnancy(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="pregnancies")
    lmp_date = models.DateField("first day of last menstrual period")
    edd = models.DateField("expected date of delivery", blank=True)
    active = models.BooleanField(default=True)
    high_risk = models.BooleanField(default=False, help_text="Flagged by a health worker")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-lmp_date"]
        verbose_name_plural = "pregnancies"

    def __str__(self):
        return f"{self.profile} — EDD {self.edd}"

    def save(self, *args, **kwargs):
        self.edd = self.lmp_date + timedelta(days=280)
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.build_anc_schedule()

    def build_anc_schedule(self):
        for i, week in enumerate(ANC_CONTACT_WEEKS, start=1):
            ANCVisit.objects.get_or_create(
                pregnancy=self,
                contact_number=i,
                defaults={"gestation_week": week, "scheduled_date": self.lmp_date + timedelta(weeks=week)},
            )

    def gestational_days(self, today=None):
        return ((today or date.today()) - self.lmp_date).days

    def gestational_weeks(self, today=None):
        return max(0, self.gestational_days(today) // 7)

    @property
    def weeks(self):
        return self.gestational_weeks()

    @property
    def trimester(self):
        w = self.weeks
        return 1 if w < 14 else (2 if w < 28 else 3)

    @property
    def days_to_edd(self):
        return (self.edd - date.today()).days

    @property
    def progress_percent(self):
        return min(100, round(self.gestational_days() / 280 * 100))

    def next_visit(self, today=None):
        """Next contact to attend. Long-missed contacts (e.g. before enrolment) don't block the schedule."""
        today = today or date.today()
        pending = self.visits.filter(attended_date__isnull=True).order_by("scheduled_date")
        return pending.filter(scheduled_date__gte=today - timedelta(days=14)).first() or pending.last()

    @property
    def missed_visits(self):
        return self.visits.filter(attended_date__isnull=True, scheduled_date__lt=date.today() - timedelta(days=14)).count()


class ANCVisit(models.Model):
    pregnancy = models.ForeignKey(Pregnancy, on_delete=models.CASCADE, related_name="visits")
    contact_number = models.PositiveSmallIntegerField()
    gestation_week = models.PositiveSmallIntegerField()
    scheduled_date = models.DateField()
    attended_date = models.DateField(null=True, blank=True)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["contact_number"]
        unique_together = ("pregnancy", "contact_number")
        verbose_name = "ANC visit"

    def __str__(self):
        return f"ANC contact {self.contact_number} ({self.scheduled_date})"

    def status(self, today=None):
        today = today or date.today()
        if self.attended_date:
            return "attended"
        if today > self.scheduled_date + timedelta(days=14):
            return "overdue"
        if today >= self.scheduled_date - timedelta(days=7):
            return "due"
        return "upcoming"

    @property
    def status_now(self):
        return self.status()


class Milestone(models.Model):
    DOMAINS = [
        ("motor", "Movement"),
        ("social", "Social & emotional"),
        ("language", "Language"),
        ("cognitive", "Learning"),
        ("care", "Care & feeding"),
    ]
    age_months = models.PositiveSmallIntegerField()
    domain = models.CharField(max_length=10, choices=DOMAINS)
    description = models.CharField(max_length=250)

    class Meta:
        ordering = ["age_months", "domain"]

    def __str__(self):
        return f"{self.age_months}m: {self.description}"


class DangerSign(models.Model):
    CATEGORIES = [("pregnancy", "Pregnancy"), ("newborn", "Newborn (0–28 days)"), ("child", "Child under 5")]
    category = models.CharField(max_length=10, choices=CATEGORIES)
    sign = models.CharField(max_length=200)
    keywords = models.CharField(max_length=250, blank=True, help_text="Comma-separated, used by the Care Navigator")

    class Meta:
        ordering = ["category", "id"]

    def __str__(self):
        return self.sign
