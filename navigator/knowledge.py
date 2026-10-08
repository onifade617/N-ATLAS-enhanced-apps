"""Curated guidance the Care Navigator is grounded in.

Summarised from WHO and NPHCDA public guidance. Lafiya educates and refers;
it never diagnoses or prescribes.
"""

SOURCES = {
    "who_anc": "WHO recommendations on antenatal care (2016)",
    "npi": "NPHCDA National Routine Immunization Schedule",
    "who_malaria": "WHO Guidelines for malaria (2024)",
    "who_htn": "WHO HEARTS technical package / hypertension guideline (2021)",
    "who_dm": "WHO diabetes fact sheet",
    "who_iycf": "WHO/UNICEF infant and young child feeding",
    "who_wash": "WHO diarrhoea & cholera guidance (ORS + zinc)",
    "who_heat": "WHO heat and health guidance",
    "who_imci": "WHO/UNICEF IMCI danger signs",
}

TOPICS = {
    "hypertension": {
        "title": "High blood pressure",
        "service": "ncd",
        "source": "who_htn",
        "points": [
            "High blood pressure often has no symptoms — the only way to know is to check it. Adults should check at least once a year.",
            "Eat less salt and seasoning cubes, more vegetables and fruit; stay active; avoid tobacco and limit alcohol.",
            "If you have been given BP medicine, take it every day, even when you feel well.",
            "Severe headache, chest pain, weakness on one side or trouble speaking needs emergency care.",
        ],
    },
    "diabetes": {
        "title": "Diabetes (high blood sugar)",
        "service": "ncd",
        "source": "who_dm",
        "points": [
            "Signs can include frequent urination, strong thirst, tiredness, blurred vision and slow-healing wounds.",
            "Get a blood sugar test at a PHC if you have these signs, are overweight or have family history.",
            "Choose whole grains, beans and vegetables; reduce sugary drinks and white bread; walk 30 minutes a day.",
            "Never stop prescribed diabetes medicine without talking to a health worker.",
        ],
    },
    "nutrition": {
        "title": "Nutrition and breastfeeding",
        "service": "nutrition",
        "source": "who_iycf",
        "points": [
            "Start breastfeeding within one hour of birth. Give only breast milk — not even water — for the first 6 months.",
            "From 6 months, add soft family foods (pap enriched with groundnut, egg, fish, beans, vegetables) and keep breastfeeding to 2 years.",
            "Children need Vitamin A every 6 months from 6 months of age, and growth checks at the clinic.",
            "Pregnant women should eat one extra small meal a day and take iron-folic acid.",
        ],
    },
    "hygiene": {
        "title": "Diarrhoea, cholera and hygiene",
        "service": "nutrition",
        "source": "who_wash",
        "points": [
            "Wash hands with soap after the toilet, before cooking and before feeding a child.",
            "Drink boiled or treated water; keep food covered.",
            "For diarrhoea, give ORS (oral rehydration salts) and zinc for 10–14 days, and keep breastfeeding or feeding.",
            "Go to a health facility at once if there is blood in stool, the child cannot drink, or is very weak or sleepy.",
        ],
    },
    "malaria": {
        "title": "Malaria prevention",
        "service": "malaria",
        "source": "who_malaria",
        "points": [
            "Sleep under an insecticide-treated net every night — especially pregnant women and children under five.",
            "Clear standing water, cover containers and cut bushes around the house.",
            "Any fever should be tested (RDT) at a clinic the same day. Do not self-treat.",
            "Pregnant women should take IPTp (SP) at antenatal visits from the second trimester.",
        ],
    },
    "heat": {
        "title": "Staying safe in extreme heat",
        "service": "ncd",
        "source": "who_heat",
        "points": [
            "Drink water often, even if you are not thirsty. Breastfed babies under 6 months only need more breastfeeds.",
            "Stay in shade or indoors between 12 and 4pm; wear light, loose clothing.",
            "People with high blood pressure, diabetes, pregnant women, babies and the elderly are at highest risk.",
            "Confusion, fainting or very hot dry skin is an emergency — cool the person and go to a facility.",
        ],
    },
    "flood": {
        "title": "Floods and health",
        "service": "emergency",
        "source": "who_wash",
        "points": [
            "Do not walk or drive through flood water; it can carry disease and hide dangers.",
            "Boil or treat all drinking water after flooding; watch for diarrhoea and cholera.",
            "Keep medicines, ANC and immunization cards in a waterproof bag in a high place.",
            "Sleep under a net — mosquitoes increase after floods.",
        ],
    },
    "pregnancy": {
        "title": "Antenatal care",
        "service": "antenatal",
        "source": "who_anc",
        "points": [
            "WHO recommends at least 8 antenatal contacts, starting before 12 weeks.",
            "At ANC you get BP checks, tests, iron-folic acid, tetanus vaccine and malaria prevention.",
            "Plan to deliver in a health facility with a skilled birth attendant.",
        ],
    },
    "milestones": {
        "title": "Child development",
        "service": "nutrition",
        "source": "who_imci",
        "points": [
            "Talk, sing and play with your child every day — it helps the brain grow.",
            "Bring your child for growth monitoring and all vaccines.",
            "If your child is not reaching milestones, ask a health worker; early help works best.",
        ],
    },
}

# Symptom → service referral. Lafiya refers; it does not diagnose.
SYMPTOMS = {
    "fever": {"service": "malaria", "urgency": "urgent", "reason": "Fever — malaria test (RDT) needed"},
    "diarrhoea": {"service": "nutrition", "urgency": "urgent", "reason": "Diarrhoea — ORS, zinc and assessment"},
    "cough": {"service": "nutrition", "urgency": "urgent", "reason": "Cough — child should be assessed"},
    "headache": {"service": "ncd", "urgency": "routine", "reason": "Headache — blood pressure check"},
    "thirst": {"service": "ncd", "urgency": "routine", "reason": "Possible diabetes signs — blood sugar test"},
}
