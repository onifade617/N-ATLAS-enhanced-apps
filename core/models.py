from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

LANGUAGES = [
    ("en", "English"),
    ("ha", "Hausa"),
    ("yo", "Yoruba"),
    ("ig", "Igbo"),
    ("pcm", "Nigerian Pidgin"),
]
LANGUAGE_NAMES = dict(LANGUAGES)


class State(models.Model):
    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=5, unique=True, help_text="ISO 3166-2:NG code, e.g. LA")
    pcode = models.CharField(max_length=10, unique=True, null=True, blank=True, help_text="OCHA COD-AB code")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LGA(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="lgas")
    name = models.CharField(max_length=80)
    pcode = models.CharField(max_length=12, unique=True, null=True, blank=True, help_text="OCHA COD-AB code")
    latitude = models.FloatField()
    longitude = models.FloatField()
    area_sqkm = models.FloatField(null=True, blank=True)
    population = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["state__name", "name"]
        unique_together = ("state", "name")
        verbose_name = "LGA"

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Ward(models.Model):
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name="wards")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["lga__name", "name"]
        unique_together = ("lga", "name")

    def __str__(self):
        return f"{self.name} ({self.lga.name})"


SERVICES = [
    ("immunization", "Immunization"),
    ("antenatal", "Antenatal care"),
    ("delivery", "Delivery"),
    ("malaria", "Malaria testing & treatment"),
    ("ncd", "BP & diabetes screening"),
    ("nutrition", "Child nutrition"),
    ("emergency", "Emergency care"),
]
SERVICE_NAMES = dict(SERVICES)


class Facility(models.Model):
    TYPES = [
        ("phc", "Primary Health Centre"),
        ("hp", "Health Post"),
        ("clin", "Clinic"),
        ("mat", "Maternity Home"),
        ("chc", "Comprehensive Health Centre"),
        ("hosp", "Hospital"),
        ("gh", "General Hospital"),
        ("th", "Teaching / Tertiary Hospital"),
        ("oth", "Other"),
    ]
    HOSPITAL_TYPES = ("chc", "hosp", "gh", "th")
    name = models.CharField(max_length=150)
    facility_type = models.CharField(max_length=5, choices=TYPES, default="phc")
    level = models.CharField(max_length=10, blank=True, help_text="Primary / Secondary / Tertiary")
    ownership = models.CharField(max_length=10, blank=True, help_text="Public / Private")
    functional = models.CharField(max_length=25, blank=True)
    registry_code = models.CharField(max_length=40, blank=True, help_text="Nigeria Health Facility Registry code")
    source = models.CharField(max_length=20, default="manual", help_text="GRID3 v3.0 / GRID3 v2.0 / demo / manual")
    external_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    hours_verified = models.BooleanField(
        default=True, help_text="False = typical hours and likely services inferred from facility type"
    )
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name="facilities")
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    services = models.CharField(
        max_length=200, help_text="Comma-separated service codes, e.g. immunization,antenatal"
    )
    open_days = models.CharField(max_length=7, default="01234", help_text="Weekday digits, Monday=0")
    opens_at = models.TimeField(default="08:00")
    closes_at = models.TimeField(default="16:00")
    is_24h = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "facilities"
        indexes = [models.Index(fields=["latitude", "longitude"])]

    def __str__(self):
        return self.name

    @property
    def service_list(self):
        return [s.strip() for s in self.services.split(",") if s.strip()]

    @property
    def service_labels(self):
        return [SERVICE_NAMES.get(s, s) for s in self.service_list]

    def offers(self, service):
        return service in self.service_list

    def is_open_at(self, when=None):
        if self.is_24h:
            return True
        when = timezone.localtime(when or timezone.now())
        if str(when.weekday()) not in self.open_days:
            return False
        return self.opens_at <= when.time() < self.closes_at

    @property
    def open_now(self):
        return self.is_open_at()

    @property
    def hours_text(self):
        return self._hours()

    @property
    def opening_summary(self):
        typical = "" if self.hours_verified else " (typical hours, not confirmed)"
        return self._hours() + typical

    def _hours(self):
        if self.is_24h:
            return "Open 24 hours"
        names = "MTWTFSS"
        days = "".join(names[int(d)] for d in sorted(self.open_days))
        day_label = "Mon–Fri" if self.open_days == "01234" else ("Mon–Sat" if self.open_days == "012345" else days)
        return f"{day_label}, {self.opens_at:%H:%M}–{self.closes_at:%H:%M}"


class Profile(models.Model):
    ROLE_FAMILY = "family"
    ROLE_WORKER = "worker"
    ROLE_GOV = "government"
    ROLES = [
        (ROLE_FAMILY, "Family / individual"),
        (ROLE_WORKER, "Health worker"),
        (ROLE_GOV, "Government / partner"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="profile"
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=3, choices=LANGUAGES, default="en")
    role = models.CharField(max_length=12, choices=ROLES, default=ROLE_FAMILY)
    lga = models.ForeignKey(LGA, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True)
    facility = models.ForeignKey(
        Facility, on_delete=models.SET_NULL, null=True, blank=True, help_text="Health workers: facility of work"
    )
    has_hypertension = models.BooleanField(default=False)
    has_diabetes = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    consent_given = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    enrolled_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    is_demo = models.BooleanField(default=False, help_text="Synthetic/demo data — excluded from validation evidence")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def language_name(self):
        return LANGUAGE_NAMES.get(self.language, self.language)

    @property
    def is_worker(self):
        return self.role == self.ROLE_WORKER

    @property
    def is_government(self):
        return self.role == self.ROLE_GOV

    @property
    def active_pregnancy(self):
        return self.pregnancies.filter(active=True).order_by("-lmp_date").first()

    @property
    def under_five_children(self):
        return [c for c in self.children.all() if c.is_under_five]

    def location(self):
        """Best-known coordinates: home location, else LGA centroid."""
        if self.latitude is not None and self.longitude is not None:
            return self.latitude, self.longitude
        if self.lga:
            return self.lga.latitude, self.lga.longitude
        return None


class Child(models.Model):
    SEX = [("F", "Female"), ("M", "Male")]
    caregiver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=80)
    sex = models.CharField(max_length=1, choices=SEX)
    date_of_birth = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["date_of_birth"]
        verbose_name_plural = "children"

    def __str__(self):
        return self.name

    def age_days(self, today=None):
        return ((today or date.today()) - self.date_of_birth).days

    @property
    def is_under_five(self):
        return self.age_days() < 5 * 365 + 1

    @property
    def age_display(self):
        days = self.age_days()
        if days < 0:
            return "not yet born"
        if days < 7 * 16:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''}"
        months = days * 12 // 365
        if months < 24:
            return f"{months} months"
        return f"{months // 12} years"
