"""Pregnancy and child guidance content (summarised from WHO / NPHCDA materials).

Lafiya educates and refers; it never diagnoses.
"""

TRIMESTER_GUIDANCE = {
    1: [
        "Start antenatal care early — your first contact should be before 12 weeks.",
        "Take iron and folic acid every day as given at the clinic.",
        "Avoid alcohol, smoking and medicines not prescribed by a health worker.",
        "Eat a variety of foods: beans, eggs, fish, green vegetables and fruit.",
    ],
    2: [
        "Sleep under an insecticide-treated net every night — malaria is dangerous in pregnancy.",
        "Ask for intermittent preventive treatment of malaria (IPTp/SP) at your ANC visits.",
        "Get your tetanus-diphtheria (Td) vaccine doses at the clinic.",
        "You should start to feel the baby move by about 20 weeks.",
    ],
    3: [
        "Make a birth plan: where you will deliver, transport, money and a blood donor.",
        "Deliver in a health facility with a skilled birth attendant.",
        "Count your baby's movements daily; tell a health worker if movements reduce.",
        "Prepare to start breastfeeding within one hour of birth.",
    ],
}


def week_message(weeks):
    if weeks < 4:
        return "Your pregnancy is just beginning. Book your first antenatal visit."
    if weeks < 13:
        return "First trimester: your baby's organs are forming. Folic acid and early ANC matter most now."
    if weeks < 20:
        return "Second trimester: many women feel better now. Keep your ANC visits and sleep under a net."
    if weeks < 28:
        return "Your baby is growing fast and you should feel movements. Watch for swelling of face and hands."
    if weeks < 37:
        return "Third trimester: finish your birth plan and know the danger signs."
    if weeks <= 42:
        return "Your baby could come any day. Keep your bag ready and go to the facility when labour starts."
    return "Your due date has passed. Please see a health worker now."
