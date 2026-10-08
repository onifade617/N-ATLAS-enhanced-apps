"""Seed Lafiya AI with reference data, an illustrative population and demo accounts.

    python manage.py seed_lafiya            # live weather if reachable
    python manage.py seed_lafiya --offline  # simulated weather only
    python manage.py seed_lafiya --reset    # wipe Lafiya data first

Facilities, families and phone numbers are SYNTHETIC demo data.
"""

import random
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from alerts.engine import run_loop
from alerts.models import Alert
from core.geo import nearest_facilities
from core.facilities_data import DATA_FILE as FACILITIES_FILE
from core.facilities_data import load_facilities
from core.geography import load_geography
from core.models import LGA, Child, Facility, Profile, State, Ward
from immunitrack.models import Immunization, Vaccine
from mamacare.models import DangerSign, Milestone, Pregnancy
from navigator.models import Referral

DEMO_PASSWORD = "lafiya123"

# LGAs that receive synthetic demo facilities and families (all 774 LGAs are loaded from
# core/data/nigeria_lgas.csv). Populations are approximate 2006-census figures.
DEMO_LGAS = {
    "LA": [("Ikeja", 313000), ("Alimosho", 1277000), ("Eti-Osa", 288000), ("Surulere", 504000), ("Badagry", 241000)],
    "KN": [("Kano Municipal", 371000), ("Fagge", 200000), ("Dala", 418000), ("Nasarawa", 596000), ("Ungogo", 365000)],
    "OY": [("Ibadan North", 306000), ("Ibadan South West", 283000), ("Ogbomosho North", 198000), ("Oyo West", 136000)],
    "EN": [("Enugu North", 243000), ("Enugu South", 198000), ("Nsukka", 309000), ("Udi", 238000)],
    "FC": [("Abuja Municipal", 776000), ("Bwari", 229000), ("Gwagwalada", 158000)],
    "KD": [("Kaduna North", 364000), ("Zaria", 406000), ("Chikun", 372000)],
    "RI": [("Port Harcourt", 541000), ("Obio/Akpor", 464000), ("Bonny", 215000)],
}

# Illustrative routine-immunization propensity per State (drives synthetic coverage gaps).
STATE_COVERAGE = {"LA": 0.86, "OY": 0.8, "EN": 0.78, "FC": 0.8, "RI": 0.7, "KD": 0.6, "KN": 0.5}
STATE_LANGUAGES = {
    "LA": [("yo", 55), ("en", 25), ("pcm", 15), ("ig", 5)],
    "KN": [("ha", 90), ("en", 5), ("pcm", 5)],
    "OY": [("yo", 85), ("en", 10), ("pcm", 5)],
    "EN": [("ig", 80), ("en", 10), ("pcm", 10)],
    "FC": [("ha", 30), ("en", 30), ("pcm", 20), ("yo", 10), ("ig", 10)],
    "KD": [("ha", 75), ("en", 15), ("pcm", 10)],
    "RI": [("pcm", 50), ("en", 40), ("ig", 10)],
}
NAMES = {
    "ha": (["Amina", "Hauwa", "Zainab", "Fatima", "Aisha", "Hadiza", "Maryam", "Halima", "Bilkisu", "Rukayya"],
           ["Musa", "Abubakar", "Bello", "Ibrahim", "Sani", "Yusuf", "Garba", "Usman"],
           ["Abdullahi", "Usman", "Khadija", "Safiya", "Musa", "Aisha", "Sadiq", "Nafisa"]),
    "yo": (["Funke", "Bisi", "Yetunde", "Kemi", "Shade", "Bukola", "Titilayo", "Ronke", "Adunni", "Folake"],
           ["Adeyemi", "Ogunleye", "Balogun", "Adebayo", "Oladipo", "Akinola", "Ojo", "Alabi"],
           ["Tobi", "Ayo", "Dami", "Tolu", "Seun", "Femi", "Bisola", "Ireti"]),
    "ig": (["Ngozi", "Chioma", "Adaeze", "Nkechi", "Ifeoma", "Amaka", "Obiageli", "Uchenna", "Chinyere", "Ebere"],
           ["Okafor", "Eze", "Nwosu", "Obi", "Okeke", "Chukwu", "Nwankwo", "Onyeka"],
           ["Chidi", "Obinna", "Ada", "Chiamaka", "Emeka", "Ifunanya", "Kelechi", "Nneka"]),
    "en": (["Blessing", "Joy", "Grace", "Esther", "Mercy", "Patience", "Comfort", "Gift", "Faith", "Peace"],
           ["Johnson", "Williams", "George", "Peters", "Amadi", "Douglas", "Briggs", "Tamuno"],
           ["David", "Daniel", "Mary", "Precious", "Favour", "Samuel", "Miracle", "Divine"]),
}
NAMES["pcm"] = NAMES["en"]

VACCINES = [
    # code, name, protects against, age_days, age label
    ("BCG", "BCG", "Tuberculosis", 0, "At birth"),
    ("OPV0", "OPV 0 (polio)", "Polio", 0, "At birth"),
    ("HEPB0", "Hepatitis B birth dose", "Hepatitis B", 0, "At birth"),
    ("OPV1", "OPV 1", "Polio", 42, "6 weeks"),
    ("PENTA1", "Pentavalent 1", "Diphtheria, tetanus, whooping cough, Hep B, Hib", 42, "6 weeks"),
    ("PCV1", "PCV 1", "Pneumonia", 42, "6 weeks"),
    ("ROTA1", "Rotavirus 1", "Rotavirus diarrhoea", 42, "6 weeks"),
    ("IPV1", "IPV 1", "Polio", 42, "6 weeks"),
    ("OPV2", "OPV 2", "Polio", 70, "10 weeks"),
    ("PENTA2", "Pentavalent 2", "Diphtheria, tetanus, whooping cough, Hep B, Hib", 70, "10 weeks"),
    ("PCV2", "PCV 2", "Pneumonia", 70, "10 weeks"),
    ("ROTA2", "Rotavirus 2", "Rotavirus diarrhoea", 70, "10 weeks"),
    ("OPV3", "OPV 3", "Polio", 98, "14 weeks"),
    ("PENTA3", "Pentavalent 3", "Diphtheria, tetanus, whooping cough, Hep B, Hib", 98, "14 weeks"),
    ("PCV3", "PCV 3", "Pneumonia", 98, "14 weeks"),
    ("IPV2", "IPV 2", "Polio", 98, "14 weeks"),
    ("VITA1", "Vitamin A (1st dose)", "Vitamin A deficiency", 183, "6 months"),
    ("MCV1", "Measles 1", "Measles", 274, "9 months"),
    ("YF", "Yellow fever", "Yellow fever", 274, "9 months"),
    ("MENA", "Meningitis A", "Meningitis A", 274, "9 months"),
    ("MCV2", "Measles 2", "Measles", 456, "15 months"),
]

MILESTONES = [
    (2, "social", "Smiles when you talk to or smile at them"),
    (2, "motor", "Holds head up when on tummy"),
    (4, "language", "Makes cooing sounds and babbles"),
    (4, "motor", "Holds head steady without support"),
    (6, "motor", "Rolls over; starts to sit with support"),
    (6, "care", "Starts soft family foods alongside breast milk; first Vitamin A dose"),
    (9, "motor", "Sits without support"),
    (9, "social", "Is shy or clingy with strangers; responds to their name"),
    (12, "motor", "Pulls up to stand; may take first steps"),
    (12, "language", "Says 'mama' or 'baba'; waves bye-bye"),
    (18, "motor", "Walks alone"),
    (18, "language", "Says several single words"),
    (24, "motor", "Kicks a ball; runs"),
    (24, "language", "Puts two words together, e.g. 'more water'"),
    (36, "language", "Talks in short sentences others can understand"),
    (36, "cognitive", "Plays pretend with toys or people"),
    (48, "motor", "Hops on one foot; catches a large ball"),
    (48, "cognitive", "Tells simple stories; names some colours"),
    (60, "cognitive", "Counts to 10; knows their address or village"),
    (60, "care", "Dresses mostly without help; ready for school"),
]

DANGER_SIGNS = [
    ("pregnancy", "Vaginal bleeding", "vaginal bleeding,bleeding in pregnancy"),
    ("pregnancy", "Convulsions or fits", "convulsion"),
    ("pregnancy", "Severe headache with blurred vision", "blurred vision,severe headache"),
    ("pregnancy", "Fever and too weak to get out of bed", "too weak"),
    ("pregnancy", "Severe abdominal pain", "severe abdominal pain"),
    ("pregnancy", "Fast or difficult breathing", "difficult breathing"),
    ("pregnancy", "Swelling of face and hands", "swollen face,swollen hands"),
    ("pregnancy", "Water breaks before labour", "water broke"),
    ("pregnancy", "Baby moves less or stops moving", "baby not moving,reduced movement"),
    ("newborn", "Not feeding well or unable to breastfeed", "not feeding,cannot breastfeed"),
    ("newborn", "Convulsions", "convulsion"),
    ("newborn", "Fast breathing or chest indrawing", "chest indrawing,fast breathing"),
    ("newborn", "High temperature or body too cold", "cold body,body too cold"),
    ("newborn", "Yellow palms or soles", "yellow palms,yellow soles,yellow eyes"),
    ("newborn", "Redness or pus around the umbilical cord", "pus,umbilical"),
    ("child", "Unable to drink or breastfeed", "unable to drink,cannot drink"),
    ("child", "Vomits everything", "vomits everything,vomiting everything"),
    ("child", "Convulsions", "convulsion"),
    ("child", "Very sleepy or unconscious", "very sleepy,unconscious"),
    ("child", "Blood in stool", "blood in stool"),
]


class Command(BaseCommand):
    help = "Seed Lafiya AI with reference data, a synthetic population and demo accounts."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing Lafiya data first")
        parser.add_argument("--offline", action="store_true", help="Use simulated weather (no network)")
        parser.add_argument("--families", type=int, default=22, help="Average synthetic families per LGA")
        parser.add_argument("--seed", type=int, default=2026)
        parser.add_argument("--if-empty", action="store_true",
                            help="Do nothing if the demo accounts already exist (safe for every deploy)")
        parser.add_argument("--demo-facilities", action="store_true",
                            help="Use 81 synthetic facilities instead of the ~55,000 real ones")

    def handle(self, *args, **opts):
        if opts["if_empty"] and User.objects.filter(username="funke").exists():
            self.stdout.write("Demo data already present - skipping seed.")
            return
        self.rng = random.Random(opts["seed"])
        self.demo_facilities_only = opts["demo_facilities"]
        self.today = date.today()
        if opts["reset"]:
            self.stdout.write("Resetting Lafiya data...")
            User.objects.filter(profile__isnull=False).delete()
            User.objects.filter(username__in=["funke", "amina", "chinedu", "chw", "gov"]).delete()
            for model in (Alert, Referral, Profile, Facility, Ward, LGA, State, Vaccine, Milestone, DangerSign):
                # In batches: SQLite limits query parameters and there are ~55,000 facilities.
                ids = list(model.objects.values_list("pk", flat=True))
                for i in range(0, len(ids), 500):
                    model.objects.filter(pk__in=ids[i : i + 500]).delete()

        with transaction.atomic():
            self.reference_data()
            if Profile.objects.filter(role=Profile.ROLE_FAMILY, user__isnull=True).exists():
                self.stdout.write("Synthetic population already present (use --reset to rebuild).")
                population = False
            else:
                self.population(opts["families"])
                population = True
            self.demo_accounts()

        self.stdout.write("Running the Intelligence Loop (weather -> risk -> alerts)...")
        summary = run_loop(self.today, refresh_weather=True, live=not opts["offline"], use_natlas=False)
        self.stdout.write(f"  {summary}")
        if population:
            self.simulate_engagement()
        self.stdout.write(self.style.SUCCESS(
            f"Done. Log in with funke / amina / chinedu (families), chw (health worker) or gov (government, "
            f"also Django admin). Password: {DEMO_PASSWORD}"
        ))

    # ------------------------------------------------------------------ reference
    def reference_data(self):
        self.stdout.write(f"Loading all states and LGAs: {load_geography()}")
        if not self.demo_facilities_only and FACILITIES_FILE.exists():
            self.stdout.write("Loading real health facilities (GRID3 / Health Facility Registry)...")
            self.stdout.write(f"  {load_facilities()}")
        for code, lgas in DEMO_LGAS.items():
            for name, pop in lgas:
                lga = LGA.objects.get(state__code=code, name=name)
                if lga.population != pop:
                    lga.population = pop
                    lga.save(update_fields=["population"])
                if not lga.facilities.exists():
                    self.facilities_for(lga)
        for i, (code, name, protects, days, label) in enumerate(VACCINES):
            Vaccine.objects.update_or_create(
                code=code, defaults={"name": name, "protects_against": protects, "age_days": days,
                                     "age_label": label, "sort_order": i}
            )
        if not Milestone.objects.exists():
            Milestone.objects.bulk_create(Milestone(age_months=m, domain=d, description=t) for m, d, t in MILESTONES)
        if not DangerSign.objects.exists():
            DangerSign.objects.bulk_create(DangerSign(category=c, sign=s, keywords=k) for c, s, k in DANGER_SIGNS)

    def facilities_for(self, lga):
        wards = [Ward.objects.get_or_create(lga=lga, name=f"{lga.name} Ward {i}")[0] for i in (1, 2, 3)]
        jitter = lambda: self.rng.uniform(-0.025, 0.025)  # noqa: E731
        phone = lambda: f"+234 800 {self.rng.randint(100, 999)} {self.rng.randint(1000, 9999)}"  # noqa: E731
        Facility.objects.create(
            source="demo", name=f"{lga.name} Model Primary Health Centre", facility_type="phc", lga=lga, ward=wards[0],
            latitude=lga.latitude + jitter(), longitude=lga.longitude + jitter(), phone=phone(),
            services="immunization,antenatal,delivery,malaria,nutrition,ncd", open_days="01234",
            opens_at=time(8), closes_at=time(16), address=f"{wards[0].name}",
        )
        Facility.objects.create(
            source="demo", name=f"Primary Health Centre, {wards[1].name}", facility_type="phc", lga=lga, ward=wards[1],
            latitude=lga.latitude + jitter(), longitude=lga.longitude + jitter(), phone=phone(),
            services="immunization,antenatal,malaria,nutrition", open_days="012345",
            opens_at=time(8), closes_at=time(14), address=f"{wards[1].name}",
        )
        Facility.objects.create(
            source="demo", name=f"General Hospital {lga.name}", facility_type="gh", lga=lga, ward=wards[2],
            latitude=lga.latitude + jitter(), longitude=lga.longitude + jitter(), phone=phone(),
            services="immunization,antenatal,delivery,malaria,ncd,nutrition,emergency", is_24h=True,
            open_days="0123456", address=f"{wards[2].name}",
        )

    # ----------------------------------------------------------------- population
    def pick_language(self, code):
        langs = STATE_LANGUAGES[code]
        return self.rng.choices([l for l, _ in langs], weights=[w for _, w in langs])[0]

    def population(self, avg_families):
        vaccines = list(Vaccine.objects.all())
        imms = []
        self.stdout.write("Creating synthetic families, pregnancies and immunization histories...")
        demo = [(c, n) for c, lgas in DEMO_LGAS.items() for n, _ in lgas]
        for lga in LGA.objects.select_related("state").prefetch_related("wards").filter(facilities__isnull=False).distinct():
            if (lga.state.code, lga.name) not in demo:
                continue
            base = STATE_COVERAGE[lga.state.code]
            propensity = min(0.97, max(0.25, base + self.rng.uniform(-0.12, 0.08)))
            wards = list(lga.wards.all()) or [None]  # real facility data has no ward records
            for _ in range(max(5, avg_families + self.rng.randint(-6, 8))):
                lang = self.pick_language(lga.state.code)
                first, last, kids = NAMES[lang]
                created_at = timezone.now() - timedelta(days=self.rng.randint(5, 200))
                p = Profile.objects.create(
                    full_name=f"{self.rng.choice(first)} {self.rng.choice(last)}", language=lang, lga=lga,
                    ward=self.rng.choice(wards), phone=f"+234 80{self.rng.randint(10000000, 99999999)}",
                    has_hypertension=self.rng.random() < 0.18, has_diabetes=self.rng.random() < 0.06,
                    consent_given=True, consent_at=created_at, created_at=created_at, is_demo=True,
                    latitude=lga.latitude + self.rng.uniform(-0.03, 0.03),
                    longitude=lga.longitude + self.rng.uniform(-0.03, 0.03),
                )
                if self.rng.random() < 0.25:
                    preg = Pregnancy.objects.create(profile=p, lmp_date=self.today - timedelta(weeks=self.rng.randint(5, 39)))
                    for v in preg.visits.filter(scheduled_date__lt=self.today):
                        if self.rng.random() < propensity:
                            v.attended_date = v.scheduled_date + timedelta(days=self.rng.randint(0, 6))
                            v.save(update_fields=["attended_date"])
                for _ in range(self.rng.choice([0, 1, 1, 1, 2, 2])):
                    dob = self.today - timedelta(days=self.rng.randint(3, 5 * 365 - 10))
                    child = Child.objects.create(caregiver=p, name=self.rng.choice(kids), sex=self.rng.choice("FM"), date_of_birth=dob)
                    imms.extend(self.immunization_history(child, vaccines, propensity))
        Immunization.objects.bulk_create(imms, ignore_conflicts=True)

    def immunization_history(self, child, vaccines, propensity):
        age = child.age_days(self.today)
        if self.rng.random() < (1 - propensity) * 0.55:  # zero-dose child
            if self.rng.random() < 0.3 and age > 0:
                bcg = next(v for v in vaccines if v.code == "BCG")
                return [Immunization(child=child, vaccine=bcg, given_date=child.date_of_birth + timedelta(days=1))]
            return []
        out = []
        p = propensity + 0.1
        last_label = None
        for v in vaccines:
            delay = self.rng.randint(0, 20)
            if age < v.age_days + delay:
                break
            if v.age_label != last_label:
                last_label = v.age_label
                p -= 0.03  # drop-out across visits
                visit_ok = self.rng.random() < p
            if visit_ok:
                out.append(Immunization(child=child, vaccine=v, given_date=min(self.today, child.date_of_birth + timedelta(days=v.age_days + delay))))
        return out

    # -------------------------------------------------------------- demo accounts
    def demo_accounts(self):
        def account(username, full_name, lga_name, language, role=Profile.ROLE_FAMILY, **extra):
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": full_name.split()[0]})
            if created:
                user.set_password(DEMO_PASSWORD)
                if role == Profile.ROLE_GOV:
                    user.is_staff = user.is_superuser = True
                user.save()
            lga = LGA.objects.get(name=lga_name)
            profile, p_created = Profile.objects.get_or_create(
                user=user,
                defaults={"full_name": full_name, "language": language, "lga": lga, "role": role,
                          "consent_given": True, "consent_at": timezone.now(), "phone": "+234 800 000 0000",
                          "is_demo": True, **extra},
            )
            return profile, p_created

        # The pitch scenario: a Yoruba-speaking mother whose baby is ~6 weeks old.
        funke, new = account("funke", "Funke Adeyemi", "Ibadan North", "yo")
        if new:
            tobi = Child.objects.create(caregiver=funke, name="Tobi", sex="M", date_of_birth=self.today - timedelta(days=41))
            for code in ("BCG", "OPV0", "HEPB0"):
                Immunization.objects.create(child=tobi, vaccine=Vaccine.objects.get(code=code), given_date=tobi.date_of_birth + timedelta(days=1))

        amina, new = account("amina", "Amina Bello", "Kano Municipal", "ha", has_hypertension=True)
        if new:
            preg = Pregnancy.objects.create(profile=amina, lmp_date=self.today - timedelta(weeks=25, days=4))
            for v in preg.visits.filter(scheduled_date__lt=self.today):
                v.attended_date = v.scheduled_date + timedelta(days=2)
                v.save(update_fields=["attended_date"])
            khadija = Child.objects.create(caregiver=amina, name="Khadija", sex="F", date_of_birth=self.today - timedelta(days=30 * 17))
            for v in Vaccine.objects.exclude(code__in=["MCV1", "YF", "MENA", "MCV2"]):
                Immunization.objects.create(child=khadija, vaccine=v, given_date=khadija.date_of_birth + timedelta(days=v.age_days + 3))

        chinedu, new = account("chinedu", "Chinedu Okafor", "Enugu North", "ig", has_diabetes=True)
        if new:
            ada = Child.objects.create(caregiver=chinedu, name="Ada", sex="F", date_of_birth=self.today - timedelta(days=130))
            for v in Vaccine.objects.filter(age_days__lte=42):
                Immunization.objects.create(child=ada, vaccine=v, given_date=ada.date_of_birth + timedelta(days=v.age_days + 2))

        ibadan = LGA.objects.get(name="Ibadan North")
        account("chw", "Kemi Balogun (CHEW)", "Ibadan North", "yo", role=Profile.ROLE_WORKER,
                facility=Facility.objects.filter(lga=ibadan, facility_type="phc").first())
        account("gov", "State Health Planner", "Ibadan North", "en", role=Profile.ROLE_GOV)

    def simulate_engagement(self):
        """Illustrative engagement history so impact metrics are not empty in the demo."""
        now = timezone.now()
        for alert in Alert.objects.filter(profile__user__isnull=True):
            if self.rng.random() < 0.62:
                alert.opened_at = now - timedelta(hours=self.rng.randint(1, 48))
                if self.rng.random() < 0.55:
                    alert.acted_on_at = alert.opened_at + timedelta(hours=self.rng.randint(1, 24))
                alert.save(update_fields=["opened_at", "acted_on_at"])
        services = ["malaria", "immunization", "antenatal", "ncd"]
        reasons = {"malaria": "Fever — malaria test (RDT) needed", "immunization": "Missed vaccines",
                   "antenatal": "ANC visit", "ncd": "Blood pressure check"}
        for p in Profile.objects.filter(role=Profile.ROLE_FAMILY, user__isnull=True):
            if self.rng.random() < 0.2:
                service = self.rng.choice(services)
                near = nearest_facilities(p.location(), service=service, limit=1)
                if near:
                    done = self.rng.random() < 0.55
                    Referral.objects.create(
                        profile=p, facility=near[0][0], service=service, reason=reasons[service],
                        status="completed" if done else self.rng.choice(["suggested", "accepted"]),
                        completed_at=now if done else None,
                    )
