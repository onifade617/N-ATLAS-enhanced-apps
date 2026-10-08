"""Fallback alert templates in Lafiya's five launch languages.

These are used when N-ATLAS is not configured or unreachable. The Hausa,
Yoruba, Igbo and Pidgin strings are draft translations and must be reviewed by
native speakers / State health educators before a pilot.
"""

TEMPLATES = {
    "malaria": {
        "en": "Malaria risk in {lga} is high this week. Sleep under a treated net every night, clear standing water, and if anyone has fever, get tested at {facility} today.",
        "pcm": "Malaria risk for {lga} don high this week. Make una sleep inside treated net every night, clear any water wey dey stand for compound, and if anybody get fever, go do test for {facility} today.",
        "yo": "Ewu àìsàn ibà (malaria) ga ní {lga} ní ọ̀sẹ̀ yìí. Ẹ máa sùn sínú àwọ̀n ẹ̀fọn ní gbogbo òru, ẹ mú omi tó dúró kúrò, bí ẹnikẹ́ni bá ní ibà, ẹ lọ ṣe àyẹ̀wò ní {facility} lónìí.",
        "ha": "Hadarin zazzabin cizon sauro (malaria) ya yi yawa a {lga} a wannan makon. Ku kwana cikin gidan sauro mai magani kowane dare, ku kawar da ruwan da ya tsaya, idan wani yana da zazzabi, ku je a yi gwaji a {facility} yau.",
        "ig": "Ihe egwu ịba (malaria) dị elu na {lga} n'izu a. Na-ehi n'ime ụgbụ anwụnta e tinyere ọgwụ kwa abalị, wepụ mmiri kwụ ọtọ, ma ọ bụrụ na onye ọ bụla nwere ahụ ọkụ, gaa nyocha na {facility} taa.",
    },
    "heat": {
        "en": "Very hot days are coming in {lga} (feels like up to {temp}°C). Drink plenty of clean water, stay in the shade from 12 to 4pm and keep babies cool. If you have high blood pressure, keep taking your medicine and check your BP at {facility}.",
        "pcm": "Hot go plenty for {lga} these days (e fit feel like {temp}°C). Drink plenty clean water, stay for shade from 12 to 4 for afternoon, and keep pikin cool. If you get high BP, no stop your medicine and check am for {facility}.",
        "yo": "Ooru gbígbóná ń bọ̀ ní {lga} (ó lè tó {temp}°C). Ẹ mu omi mímọ́ dáadáa, ẹ dúró sí ibòji láti agogo méjìlá sí mẹ́rin ọ̀sán, ẹ sì jẹ́ kí àwọn ọmọ ọwọ́ tutù. Bí ẹ bá ní ẹ̀jẹ̀ ríru, ẹ má dá oògùn dúró, kí ẹ sì yẹ̀ ẹ́ wò ní {facility}.",
        "ha": "Zafi mai tsanani na zuwa a {lga} (zai iya kai {temp}°C). Ku sha ruwa mai tsabta da yawa, ku zauna a inuwa daga karfe 12 zuwa 4 na rana, ku sa jarirai su ji sanyi. Idan kuna da hawan jini, kada ku daina magani, ku duba jinin ku a {facility}.",
        "ig": "Oke okpomọkụ na-abịa na {lga} (ọ nwere ike ịdị ka {temp}°C). Ṅụọ ọtụtụ mmiri dị ọcha, nọrọ na ndò site n'elekere 12 ruo 4 n'ehihie, ma mee ka ụmụaka dị jụụ. Ọ bụrụ na ọbara mgbali gị dị elu, aghala ọgwụ gị, ma lelee ya na {facility}.",
    },
    "flood": {
        "en": "Heavy rain ({rain} mm in 3 days) may cause flooding in {lga}. Boil or treat drinking water, keep medicines and health cards in a high dry place, and know your way to {facility}.",
        "pcm": "Heavy rain ({rain} mm for 3 days) fit cause flood for {lga}. Boil or treat the water wey you dey drink, keep una medicine and health card for high place wey dry, and know road to {facility}.",
        "yo": "Òjò ńlá ({rain} mm ní ọjọ́ mẹ́ta) lè fa àkúnya omi ní {lga}. Ẹ se omi mímu tàbí kí ẹ tọ́jú rẹ̀, ẹ gbé oògùn àti káàdì ìlera sí ibi gíga tó gbẹ, kí ẹ sì mọ ọ̀nà sí {facility}.",
        "ha": "Ruwan sama mai yawa ({rain} mm cikin kwana 3) na iya haifar da ambaliya a {lga}. Ku tafasa ko ku tace ruwan sha, ku ajiye magunguna da katin lafiya a wuri mai tsayi da bushe, ku san hanyar zuwa {facility}.",
        "ig": "Oke mmiri ozuzo ({rain} mm n'ụbọchị 3) nwere ike ibute iju mmiri na {lga}. Sie ma ọ bụ gwọọ mmiri ọṅụṅụ, debe ọgwụ na kaadị ahụike n'ebe dị elu ma kpọọ nkụ, ma mara ụzọ ga {facility}.",
    },
    "vaccine": {
        "en": "{child}'s next vaccines ({vaccines}) are due on {date}. Immunization is free at {facility}. Bring the child health card.",
        "pcm": "{child} next vaccine ({vaccines}) go reach on {date}. Immunization na free for {facility}. Carry the pikin health card come.",
        "yo": "Abẹ́rẹ́ àjẹsára tó kàn fún {child} ({vaccines}) yẹ ní {date}. Abẹ́rẹ́ àjẹsára jẹ́ ọ̀fẹ́ ní {facility}. Ẹ mú káàdì ìlera ọmọ wá.",
        "ha": "Allurar rigakafi ta gaba ta {child} ({vaccines}) ta kama ranar {date}. Rigakafi kyauta ne a {facility}. Ku zo da katin lafiyar yaro.",
        "ig": "Ọgwụ mgbochi ọzọ nke {child} ({vaccines}) ga-eru na {date}. Ọgwụ mgbochi bụ n'efu na {facility}. Bịa na kaadị ahụike nwatakịrị ahụ.",
    },
    "vaccine_overdue": {
        "en": "{child} has missed vaccines ({vaccines}) that were due on {date}. It is not too late — go to {facility} this week to catch up. It is free.",
        "pcm": "{child} don miss vaccine ({vaccines}) wey suppose happen on {date}. E never too late — go {facility} this week make dem give am. Na free.",
        "yo": "{child} kò tíì gba abẹ́rẹ́ àjẹsára ({vaccines}) tó yẹ ní {date}. Kò tíì pẹ́ jù — ẹ lọ sí {facility} ní ọ̀sẹ̀ yìí. Ọ̀fẹ́ ni.",
        "ha": "{child} ya rasa allurar rigakafi ({vaccines}) da ta kama ranar {date}. Bai yi latti ba — ku je {facility} a wannan makon. Kyauta ne.",
        "ig": "{child} agbaghị ọgwụ mgbochi ({vaccines}) nke kwesịrị na {date}. O teghị aka — gaa {facility} n'izu a. Ọ bụ n'efu.",
    },
    "anc": {
        "en": "Your antenatal visit (contact {n}, at {week} weeks) is due on {date}. Go to {facility} and bring your ANC card. Regular check-ups keep you and your baby safe.",
        "pcm": "Your antenatal visit (number {n}, for {week} weeks) go reach on {date}. Go {facility} and carry your ANC card. Check-up dey keep you and your baby safe.",
        "yo": "Ìbẹ̀wò ìtọ́jú oyún rẹ (nọ́mbà {n}, ní ọ̀sẹ̀ {week}) yẹ ní {date}. Lọ sí {facility} kí o sì mú káàdì ANC rẹ dání. Àyẹ̀wò déédéé ń dáàbò bo ìwọ àti ọmọ rẹ.",
        "ha": "Ziyarar awon ciki (ta {n}, a mako {week}) ta kama ranar {date}. Ki je {facility} ki zo da katin ANC dinki. Duba lafiya akai-akai na kare ki da jaririnki.",
        "ig": "Nleta nlekọta ime gị (nke {n}, n'izu {week}) ga-eru na {date}. Gaa {facility} ma bute kaadị ANC gị. Nlele mgbe niile na-echekwa gị na nwa gị.",
    },
}

TITLES = {
    "malaria": "Malaria risk rising in {lga}",
    "heat": "Heat warning for {lga}",
    "flood": "Flood risk in {lga}",
    "vaccine": "{child}'s vaccines due {date}",
    "vaccine_overdue": "{child} has missed vaccines",
    "anc": "Antenatal visit due {date}",
}


def render(key, language, **ctx):
    templates = TEMPLATES[key]
    text = templates.get(language) or templates["en"]
    return text.format(**ctx), TITLES[key].format(**ctx)
