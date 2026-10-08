"""Vaccine schedules, due/overdue logic and coverage-gap calculations."""

from collections import OrderedDict
from datetime import date, timedelta

from .models import Vaccine

OVERDUE_GRACE_DAYS = 14
DUE_SOON_DAYS = 7

# Coverage indicators (WHO/UNICEF WUENIC style).
PENTA1, PENTA3, MCV1 = "PENTA1", "PENTA3", "MCV1"


def vaccine_status(due_date, given_date, today):
    if given_date:
        return "given"
    if today > due_date + timedelta(days=OVERDUE_GRACE_DAYS):
        return "overdue"
    if today >= due_date:
        return "due"
    if today >= due_date - timedelta(days=DUE_SOON_DAYS):
        return "due_soon"
    return "upcoming"


def child_schedule(child, today=None, vaccines=None):
    """Full schedule for a child: list of dicts with vaccine, due_date, status."""
    today = today or date.today()
    vaccines = vaccines if vaccines is not None else list(Vaccine.objects.all())
    given = {i.vaccine_id: i for i in child.immunizations.all()}
    rows = []
    for v in vaccines:
        due = child.date_of_birth + timedelta(days=v.age_days)
        imm = given.get(v.id)
        rows.append(
            {
                "vaccine": v,
                "due_date": due,
                "given_date": imm.given_date if imm else None,
                "status": vaccine_status(due, imm.given_date if imm else None, today),
            }
        )
    return rows


def grouped_schedule(child, today=None):
    groups = OrderedDict()
    for row in child_schedule(child, today):
        groups.setdefault(row["vaccine"].age_label, []).append(row)
    return groups


def next_due(child, today=None):
    """Next visit: the earliest due date among vaccines not yet given, and all vaccines on it."""
    pending = [r for r in child_schedule(child, today) if r["status"] != "given"]
    if not pending:
        return None
    first = min(r["due_date"] for r in pending)
    # Overdue doses are bundled with the next visit.
    visit = [r for r in pending if r["due_date"] == first or r["status"] == "overdue"]
    return {
        "due_date": first,
        "vaccines": [r["vaccine"] for r in visit],
        "status": "overdue" if any(r["status"] == "overdue" for r in visit) else visit[0]["status"],
    }


def coverage_for_children(children, today=None):
    """Coverage indicators over a set of children.

    - Penta1/Penta3/MCV1 coverage among children old enough (due date + grace passed).
    - Zero-dose: eligible for Penta1 but never received it (WHO definition).
    """
    today = today or date.today()
    vax = {v.code: v for v in Vaccine.objects.filter(code__in=[PENTA1, PENTA3, MCV1])}
    stats = {"children": 0, "zero_dose": 0}
    eligible = {code: 0 for code in vax}
    covered = {code: 0 for code in vax}
    for child in children:
        age = child.age_days(today)
        if age < 0 or age > 5 * 365:
            continue
        stats["children"] += 1
        given = {i.vaccine.code for i in child.immunizations.all()}
        for code, v in vax.items():
            if age >= v.age_days + 28:
                eligible[code] += 1
                if code in given:
                    covered[code] += 1
        if PENTA1 in vax and age >= vax[PENTA1].age_days + 28 and PENTA1 not in given:
            stats["zero_dose"] += 1
    for code in vax:
        stats[f"{code.lower()}_eligible"] = eligible[code]
        stats[f"{code.lower()}_coverage"] = round(100 * covered[code] / eligible[code]) if eligible[code] else None
    stats["dropout_penta1_3"] = (
        round(100 * (covered.get(PENTA1, 0) - covered.get(PENTA3, 0)) / covered[PENTA1])
        if covered.get(PENTA1)
        else None
    )
    return stats
