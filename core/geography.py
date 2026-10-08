"""All 36 states + FCT and 774 LGAs of Nigeria.

Source: OCHA Nigeria Subnational Administrative Boundaries (COD-AB, v01, valid
from 2019-04-17), https://data.humdata.org/dataset/cod-ab-nga — names, P-codes
and polygon centre points, extracted to core/data/nigeria_lgas.csv.
"""

import csv
import re
from pathlib import Path

from django.db import transaction

from .models import LGA, State

DATA_FILE = Path(__file__).parent / "data" / "nigeria_lgas.csv"

# ISO 3166-2:NG state codes.
STATE_CODES = {
    "Abia": "AB", "Adamawa": "AD", "Akwa Ibom": "AK", "Anambra": "AN", "Bauchi": "BA", "Bayelsa": "BY",
    "Benue": "BE", "Borno": "BO", "Cross River": "CR", "Delta": "DE", "Ebonyi": "EB", "Edo": "ED", "Ekiti": "EK",
    "Enugu": "EN", "Federal Capital Territory": "FC", "Gombe": "GO", "Imo": "IM", "Jigawa": "JI", "Kaduna": "KD",
    "Kano": "KN", "Katsina": "KT", "Kebbi": "KE", "Kogi": "KO", "Kwara": "KW", "Lagos": "LA", "Nasarawa": "NA",
    "Niger": "NI", "Ogun": "OG", "Ondo": "ON", "Osun": "OS", "Oyo": "OY", "Plateau": "PL", "Rivers": "RI",
    "Sokoto": "SO", "Taraba": "TA", "Yobe": "YO", "Zamfara": "ZA",
}

# Misspellings / outdated names in the COD-AB v01 tables, corrected to the official LGA names.
NAME_CORRECTIONS = {
    "Obia/Akpor": "Obio/Akpor",
    "Port-Harcourt": "Port Harcourt",
    "Omumma": "Omuma",
    "Garum Mallam": "Garun Mallam",
    "Atigbo": "Atisbo",
    "Muya": "Munya",
    "Tarmua": "Tarmuwa",
    "Wamako": "Wamakko",
    "Markafi": "Makarfi",
    "Biriniwa": "Birniwa",
    "Olamabolo": "Olamaboro",
    "Isiukwuato": "Isuikwuato",
    "Atakumosa East": "Atakunmosa East",
    "Atakumosa West": "Atakunmosa West",
    "Birni Kudu": "Birnin Kudu",
    "Zango-Kataf": "Zangon Kataf",
    "Egbado North": "Yewa North",  # renamed; "Yewa" is the current official name
    "Egbado South": "Yewa South",
    "Barikin Ladi": "Barkin Ladi",
    "Oturkpo": "Otukpo",
    "Bekwara": "Bekwarra",
    "Unuimo": "Onuimo",
    "Ilejemeji": "Ilejemeje",
}


# Alternative spellings that may already exist in a database, mapped to the official name.
ALIASES = {
    "nassarawa": "nasarawa",
    "municipalareacouncil": "abujamunicipal",
    "amac": "abujamunicipal",
    "obinwga": "obingwa",
    "nasarawaegon": "nasarawaeggon",
    "ayedade": "aiyedade",
    "ayedaade": "aiyedade",
    "ayedire": "aiyedire",
    "birninmagajikiyaw": "birninmagaji",
    "egbadonorth": "yewanorth",
    "egbadosouth": "yewasouth",
    "uhunmwode": "uhunmwonde",
    "ezinihittembaise": "ezinihitte",
    "garummallam": "garunmallam",
    "omumma": "omuma",
}


def _key(name):
    """Match names regardless of case, hyphens, slashes and spacing ("Ibadan South-West" == "Ibadan South West")."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    return ALIASES.get(key, key)


def rows():
    with open(DATA_FILE, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            row["lga"] = NAME_CORRECTIONS.get(row["lga"], row["lga"])
            yield row


@transaction.atomic
def load_geography():
    """Create or update every state and LGA. Existing records are matched by code, then by name."""
    created = updated = 0
    states = {}
    for row in rows():
        sname = row["state"]
        if sname not in states:
            code = STATE_CODES[sname]
            state = (
                State.objects.filter(pcode=row["state_pcode"]).first()
                or State.objects.filter(code=code).first()
                or State(code=code)
            )
            state.name, state.code, state.pcode = sname, code, row["state_pcode"]
            state.save()
            states[sname] = (state, {_key(l.name): l for l in state.lgas.all()})
        state, existing = states[sname]
        lga = LGA.objects.filter(pcode=row["lga_pcode"]).first() or existing.get(_key(row["lga"]))
        if lga is None:
            lga = LGA(state=state)
            created += 1
        else:
            updated += 1
        lga.name = row["lga"]
        lga.pcode = row["lga_pcode"]
        lga.latitude = float(row["latitude"])
        lga.longitude = float(row["longitude"])
        lga.area_sqkm = float(row["area_sqkm"] or 0) or None
        lga.save()
    return {"states": len(states), "lgas_created": created, "lgas_updated": updated}
