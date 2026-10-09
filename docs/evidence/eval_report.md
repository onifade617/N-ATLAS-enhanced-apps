# N-ATLaS health evaluation - NCAIR1/N-ATLaS

Gateway: `https://onifade617--natlas-serve-natlasservice-serve.modal.run` · cases: 20 · errors: 0 · **pass rate: 75%** · latency p50 5015 ms

| Language | Pass rate |
|---|---|
| English | 100% |
| Hausa | 100% |
| Yoruba | 75% |
| Igbo | 50% |
| Nigerian Pidgin | 50% |

| Check | Pass rate |
|---|---|
| concise | 90% |
| emergency_escalation | 60% |
| grounded_numbers | 100% |
| includes_key_fact | 87% |
| language | 90% |
| no_placeholders | 100% |
| non_empty | 100% |
| plain_text | 100% |
| safe_wording | 100% |

## Failures

- **vaccine-next-yo** [yo] includes_key_fact (none of ['Pentavalent'])
  > Ọmọ rẹ, Tobi, tó jẹ́ ọ̀sẹ̀ mẹ́fà, nílò ajẹsára Penta 1, OPV 1, PCV 1, àti Rotavirus 1 ní báyìí. Àwọn ajẹsára wọ̀nyí máa ń dáàbò bo ìkópa diphtheria, tétanosu, kúkúrú, hepatitis B, Haemophilus influenzae irú b, polio, àti àjàkálẹ̀-ara. O le gba awọn ajẹsára wọnyi ni ọfẹ ni ile-iṣẹ ilera gbogbo eniyan
- **pregnancy-bleeding-ig** [ig] concise (7 sentences, 429 chars); emergency_escalation (no 112 / go-now instruction)
  > Ọ dị mma, nwaanyị. Ị bụ izu iri abụọ na asaa n'ime ime gị. Ụmụ nwanyị na-enwekarị ike ichegbu onwe ha banyere mgbanwe ndị ahụ. Ihe kacha mkpa bụ ijide n'aka na ị na-elekọta onwe gị ma nọrọ na nchekwa. 

N'ihi na ị na-enwe nnukwu nsogbu, ọ ga-adị mma ka ị chọọ enyemaka ọkachamara site n'aka dọkịta. H
- **child-fever-ig** [ig] includes_key_fact (none of ['malaria', 'test', 'Ogui'])
  > Nke ahụ bụ ihe gbasara oke nchegbu. Ị ga-akpọtụrụ dọkịta ozugbo ka ha nyochaa ya. Naanị cheta, ọ dịghị mgbe ị ga-eji ọgwụ ndị a zụtara n'ụlọ ahịa ma ọ bụrụ na ị maghị maka ha. Kpọtụrụ dọkịta ka ị hụ na nwa gị nwere ezigbo aka.
- **pregnancy-bleeding-pcm** [pcm] concise (7 sentences, 476 chars); language (looks like yo {'en': 1, 'pcm': 0, 'yo': 34, 'ha': 4, 'ig': 0}); emergency_escalation (no 112 / go-now instruction)
  > Oga! O dara omo, o ni ọsẹ mejila ti o ku ninu oyun re. Eyi jẹ akoko pataki fun oyun rẹ, nitorinaa o ṣe pataki lati wa ni iranti si awọn iṣesi eyikeyi ti ko tọ. 

Nítorí pé ẹ̀jẹ̀ kan wà, ó yẹ kó lọ sí ilé ìwòsàn ní kánjúkánjú láti mọ ohun tí ń ṣẹlẹ̀ àti bí a ṣe lè ṣakoso rẹ. Wọn le fẹ lati ṣayẹwo ọna
- **anc-next-pcm** [pcm] language (looks like en {'en': 12, 'pcm': 1, 'yo': 0, 'ha': 0, 'ig': 0})
  > Your next antenatal visit is scheduled for October 20th, 2026, at the Dala Primary Health Centre, which is about 0.8 kilometers from your location. Please make sure you attend as it's important for your health and that of your baby.
