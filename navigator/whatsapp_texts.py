"""WhatsApp onboarding and system messages.

Hausa, Yoruba, Igbo and Pidgin strings are draft translations that need
native-speaker review before a pilot. Answers to health questions themselves are
written by N-ATLaS (or the localized template engine) — not from this file.
"""

LANGUAGE_MENU = (
    "Welcome to *Lafiya AI* 💚 — health guidance in your language, by voice note or text.\n\n"
    "Reply with a number · Zaɓi lamba · Yan nọ́mbà · Họrọ nọmba:\n"
    "1️⃣ English\n2️⃣ Hausa\n3️⃣ Yorùbá\n4️⃣ Igbo\n5️⃣ Pidgin"
)

LANGUAGE_CHOICES = {
    "1": "en", "english": "en", "2": "ha", "hausa": "ha", "3": "yo", "yoruba": "yo",
    "4": "ig", "igbo": "ig", "5": "pcm", "pidgin": "pcm", "naija": "pcm",
}

YES_WORDS = {"yes", "y", "yes o", "ok", "okay", "agree", "i agree", "eh", "na yarda", "beeni", "ee", "1"}
NO_WORDS = {"no", "n", "a'a", "aa", "rara", "mba", "no o"}
STOP_WORDS = {"stop", "delete", "unsubscribe", "daina", "duro", "kwusi"}
LANGUAGE_WORDS = {"language", "lang", "harshe", "ede", "asusu"}
MENU_WORDS = {"hi", "hello", "hey", "menu", "help", "start", "sannu", "bawo", "kedu", "ndewo", "how far", "good morning"}
SKIP_WORDS = {"skip", "later", "tsallake", "fo", "wufe"}

TEXTS = {
    "en": {
        "consent": "Lafiya gives health information and reminders. It does not diagnose. To help you, we store your "
                   "messages, language and area securely, and only share anonymous totals for planning (Nigeria Data "
                   "Protection Act 2023). Send STOP at any time to delete your data.\n\nReply *YES* to agree.",
        "consent_declined": "No problem. Lafiya will not store your information. Send HI any time if you change your mind.",
        "location": "Thank you! Which LGA or town do you live in? Type or say its name, or share your location "
                    "(📎 → Location). Reply SKIP to do this later.",
        "location_saved": "Got it: *{lga}*. 🎉 Ask me anything by voice note or text — for example: \"Which vaccine "
                          "does my baby need next?\" or \"Where is the nearest clinic?\"",
        "location_unknown": "I couldn't find that LGA. Please send the LGA and state (e.g. \"Surulere, Lagos\"), share your location (📎 → Location), or reply SKIP.",
        "menu": "Send a voice note 🎙️ or text in your language. I can help with: vaccines 💉, pregnancy 🤰, "
                "malaria/heat/flood alerts 🌦️, blood pressure & diabetes, nutrition, and the nearest clinic 🏥.\n"
                "Commands: LANGUAGE (change language), STOP (delete my data).\n"
                "Emergency? Go to the nearest facility or call 112.",
        "voice_failed": "Sorry, I couldn't hear that voice note clearly. Please try again, or type your question.",
        "stopped": "Your Lafiya data has been deleted. Thank you. Send HI if you want to start again.",
        "you_said": "🎙️ You said",
    },
    "ha": {
        "consent": "Lafiya na ba da bayanan lafiya da tunatarwa. Ba ta gano cuta. Domin taimaka muku, muna adana "
                   "sakonninku, harshe da yankinku cikin tsaro, kuma muna raba jimillar bayanai ba tare da suna ba don "
                   "tsare-tsare (Dokar Kare Bayanai ta Najeriya 2023). Aika STOP a kowane lokaci don share bayananku."
                   "\n\nAmsa *EH* domin amincewa.",
        "consent_declined": "Babu matsala. Lafiya ba za ta adana bayananku ba. Aika HI a kowane lokaci idan kun canja ra'ayi.",
        "location": "Na gode! A wace karamar hukuma (LGA) ko gari kuke zaune? Rubuta ko fadi sunanta, ko aiko wurin "
                    "da kuke (📎 → Location). Amsa SKIP don yin haka daga baya.",
        "location_saved": "Na gane: *{lga}*. 🎉 Yanzu kuna iya tambaya ta sakon murya ko rubutu — misali: \"Wace "
                          "allurar rigakafi jaririna yake bukata?\" ko \"Ina asibiti mafi kusa?\"",
        "location_unknown": "Ban sami wannan karamar hukuma ba. Don Allah aiko sunan karamar hukuma da jiha (misali \"Fagge, Kano\"), ko wurin da kuke (📎 → Location), ko amsa SKIP.",
        "menu": "Aiko sakon murya 🎙️ ko rubutu da harshenku. Zan iya taimakawa game da: rigakafi 💉, ciki 🤰, "
                "gargadin zazzabin cizon sauro/zafi/ambaliya 🌦️, hawan jini da ciwon suga, abinci, da asibiti mafi "
                "kusa 🏥.\nUmarni: LANGUAGE (canja harshe), STOP (share bayanaina).\n"
                "Gaggawa? Je asibiti mafi kusa ko kira 112.",
        "voice_failed": "Yi hakuri, ban ji sakon muryar sosai ba. Don Allah sake gwadawa, ko rubuta tambayarku.",
        "stopped": "An share bayananku na Lafiya. Na gode. Aika HI idan kuna son farawa.",
        "you_said": "🎙️ Kun ce",
    },
    "yo": {
        "consent": "Lafiya ń fúnni ní ìmọ̀ nípa ìlera àti ìrántí. Kò ṣe àyẹ̀wò àìsàn. Láti ràn yín lọ́wọ́, a ń tọ́jú "
                   "àwọn ìfiránṣẹ́, èdè àti agbègbè yín láìléwu, a sì máa ń pín àròpọ̀ láìsí orúkọ fún ètò nìkan (Òfin "
                   "Ààbò Data Nàìjíríà 2023). Ẹ fi STOP ránṣẹ́ nígbàkigbà láti pa data yín rẹ́.\n\n"
                   "Ẹ fèsì *BẸ́Ẹ̀NI* láti gbà.",
        "consent_declined": "Kò burú. Lafiya kò ní tọ́jú ìwífún yín. Ẹ fi HI ránṣẹ́ nígbàkigbà tí ẹ bá yí ọkàn padà.",
        "location": "Ẹ ṣé! Ìjọba ìbílẹ̀ (LGA) tàbí ìlú wo ni ẹ ń gbé? Ẹ kọ tàbí sọ orúkọ rẹ̀, tàbí kí ẹ fi ibi tí ẹ wà "
                    "ránṣẹ́ (📎 → Location). Ẹ fèsì SKIP láti ṣe é nígbà míràn.",
        "location_saved": "Ó yé mi: *{lga}*. 🎉 Ẹ lè bi mí ní ìbéèrè báyìí pẹ̀lú ohùn tàbí ọ̀rọ̀ — fún àpẹẹrẹ: "
                          "\"Abẹ́rẹ́ àjẹsára wo ni ọmọ mi nílò báyìí?\" tàbí \"Níbo ni ilé ìwòsàn tó súnmọ́ jùlọ wà?\"",
        "location_unknown": "Mi ò rí ìjọba ìbílẹ̀ yẹn. Ẹ jọ̀wọ́ kọ ìjọba ìbílẹ̀ àti ìpínlẹ̀ (bí àpẹẹrẹ \"Surulere, Lagos\"), tàbí fi ibi tí ẹ wà ránṣẹ́ (📎 → Location), tàbí kí ẹ fèsì SKIP.",
        "menu": "Ẹ fi ohùn 🎙️ tàbí ọ̀rọ̀ ránṣẹ́ ní èdè yín. Mo lè ràn yín lọ́wọ́ nípa: abẹ́rẹ́ àjẹsára 💉, oyún 🤰, "
                "ìkìlọ̀ ibà/ooru/àkúnya omi 🌦️, ẹ̀jẹ̀ ríru àti àtọ̀gbẹ, oúnjẹ, àti ilé ìwòsàn tó súnmọ́ 🏥.\n"
                "Àṣẹ: LANGUAGE (yí èdè padà), STOP (pa data mi rẹ́).\nPàjáwìrì? Ẹ lọ sí ilé ìwòsàn tó súnmọ́ tàbí pe 112.",
        "voice_failed": "Ẹ má bínú, mi ò gbọ́ ohùn yẹn dáadáa. Ẹ jọ̀wọ́ tún gbìyànjú, tàbí kí ẹ kọ ìbéèrè yín.",
        "stopped": "A ti pa data Lafiya yín rẹ́. Ẹ ṣé. Ẹ fi HI ránṣẹ́ tí ẹ bá fẹ́ bẹ̀rẹ̀ lẹ́ẹ̀kan sí i.",
        "you_said": "🎙️ Ẹ sọ pé",
    },
    "ig": {
        "consent": "Lafiya na-enye ozi ahụike na ihe ncheta. Ọ naghị achọpụta ọrịa. Iji nyere gị aka, anyị na-echekwa "
                   "ozi gị, asụsụ na mpaghara gị n'enweghị ihe egwu, ma na-ekesa naanị ọnụ ọgụgụ na-enweghị aha maka "
                   "atụmatụ (Iwu Nchekwa Data Naịjirịa 2023). Ziga STOP mgbe ọ bụla iji hichapụ data gị.\n\n"
                   "Zaa *EE* iji kwenye.",
        "consent_declined": "Ọ dị mma. Lafiya agaghị echekwa ozi gị. Ziga HI mgbe ọ bụla ị gbanwere obi.",
        "location": "Daalụ! Kedu LGA ma ọ bụ obodo ị bi? Dee ma ọ bụ kwuo aha ya, ma ọ bụ ziga ebe ị nọ "
                    "(📎 → Location). Zaa SKIP ime ya ma emechaa.",
        "location_saved": "Aghọtara m: *{lga}*. 🎉 Ị nwere ike ịjụ m ugbu a site na olu ma ọ bụ ederede — dịka: "
                          "\"Kedu ọgwụ mgbochi nwa m chọrọ ọzọ?\" ma ọ bụ \"Ebee ka ụlọ ọgwụ kacha nso dị?\"",
        "location_unknown": "Achọtaghị m LGA ahụ. Biko dee LGA na steeti (dịka \"Nsukka, Enugu\"), ma ọ bụ ziga ebe ị nọ (📎 → Location), ma ọ bụ zaa SKIP.",
        "menu": "Ziga ozi olu 🎙️ ma ọ bụ ederede n'asụsụ gị. Enwere m ike inyere gị aka maka: ọgwụ mgbochi 💉, ime 🤰, "
                "ịdọ aka na ntị ịba/okpomọkụ/iju mmiri 🌦️, ọbara mgbali na ọrịa shuga, nri, na ụlọ ọgwụ kacha nso 🏥.\n"
                "Iwu: LANGUAGE (gbanwee asụsụ), STOP (hichapụ data m).\n"
                "Ihe mberede? Gaa n'ụlọ ọgwụ kacha nso ma ọ bụ kpọọ 112.",
        "voice_failed": "Ndo, anụghị m ozi olu ahụ nke ọma. Biko nwaa ọzọ, ma ọ bụ dee ajụjụ gị.",
        "stopped": "Ehichapụla data Lafiya gị. Daalụ. Ziga HI ma ị chọrọ ịmalite ọzọ.",
        "you_said": "🎙️ Ị kwuru",
    },
    "pcm": {
        "consent": "Lafiya dey give health information and reminder. E no dey diagnose sickness. To help you, we go keep "
                   "your message, language and area safe, and na only total wey no get name we dey share for planning "
                   "(Nigeria Data Protection Act 2023). Send STOP anytime make we delete your data.\n\n"
                   "Reply *YES* if you gree.",
        "consent_declined": "No wahala. Lafiya no go keep your information. Send HI anytime if you change mind.",
        "location": "Thank you! Which LGA or town you dey stay? Type or talk the name, or share your location "
                    "(📎 → Location). Reply SKIP to do am later.",
        "location_saved": "I don get am: *{lga}*. 🎉 You fit ask me anything now with voice note or text — like: "
                          "\"Which vaccine my pikin need next?\" or \"Where the nearest clinic dey?\"",
        "location_unknown": "I no fit find that LGA. Abeg send the LGA and state (like \"Surulere, Lagos\"), share your location (📎 → Location), or reply SKIP.",
        "menu": "Send voice note 🎙️ or text for your language. I fit help with: vaccine 💉, belle 🤰, "
                "malaria/heat/flood alert 🌦️, BP and sugar, food, and the nearest clinic 🏥.\n"
                "Commands: LANGUAGE (change language), STOP (delete my data).\n"
                "Emergency? Go the nearest hospital or call 112.",
        "voice_failed": "Sorry, I no hear that voice note well. Abeg try again, or type your question.",
        "stopped": "We don delete your Lafiya data. Thank you. Send HI if you wan start again.",
        "you_said": "🎙️ You talk say",
    },
}


def text(language, key, **ctx):
    value = TEXTS.get(language, TEXTS["en"]).get(key) or TEXTS["en"][key]
    return value.format(**ctx) if ctx else value
