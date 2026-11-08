# Synthetic complaints dataset generator for Township One
# Constructs balanced dataset across categories, urgencies, and languages.

import os
import pandas as pd

complaints_data = [
    # =========================================================================
    # PLUMBING (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: pipe_burst_leakage
    {"text": "Main water pipe in kitchen ceiling burst suddenly, massive water cascade flooding entire flat!", "category": "PLUMBING", "urgency": "CRITICAL", "language": "en", "incident_family": "pipe_burst_leakage"},
    {"text": "Severe pipe leakage in bathroom wall seepage spreading into electrical conduit rapidly.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "en", "incident_family": "pipe_burst_leakage"},
    {"text": "Balcony drainage pipe has a major fracture leaking dirty runoff water onto downstairs neighbor.", "category": "PLUMBING", "urgency": "HIGH", "language": "en", "incident_family": "pipe_burst_leakage"},
    {"text": "किचन की मुख्य सप्लाई पाइप फट गई है और पूरे घर में तेजी से पानी भर रहा है तुरंत प्लंबर भेजें।", "category": "PLUMBING", "urgency": "CRITICAL", "language": "hi", "incident_family": "pipe_burst_leakage"},
    {"text": "रसोई की सीलिंग से बहुत भारी पानी का रिसाव हो रहा है, फर्नीचर खराब हो रहा है।", "category": "PLUMBING", "urgency": "HIGH", "language": "hi", "incident_family": "pipe_burst_leakage"},
    {"text": "Main pipeline phat gayi hai bathroom me paani floor par overflow ho raha hai emergency plumber bhejo.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "hi", "incident_family": "pipe_burst_leakage"},
    {"text": "स्वयंपाकघरातील मुख्य पाण्याची पाईप अचानक फुटली असून घरात सर्वत्र पाणी साचले आहे तातडीने मदत हवी.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "mr", "incident_family": "pipe_burst_leakage"},
    {"text": "बाथरूमच्या छतावरून पाण्याचा सतत मोठा प्रवाह गळत आहे आणि भिंती खराब झाल्या आहेत.", "category": "PLUMBING", "urgency": "HIGH", "language": "mr", "incident_family": "pipe_burst_leakage"},
    {"text": "Kitchen chi main pipe futli ahe aani paani hall madhe yet ahe emergency plumber lavkar pathva.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "mr", "incident_family": "pipe_burst_leakage"},

    # Family 2: tap_damage
    {"text": "Kitchen sink mixer tap handle is loose and dripping constantly when shut off.", "category": "PLUMBING", "urgency": "LOW", "language": "en", "incident_family": "tap_damage"},
    {"text": "Master bedroom washbasin faucet is jammed and does not turn fully to hot water.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "en", "incident_family": "tap_damage"},
    {"text": "Guest bathroom tap thread is stripped and spraying mist under high pressure around vanity.", "category": "PLUMBING", "urgency": "HIGH", "language": "en", "incident_family": "tap_damage"},
    {"text": "वॉश बेसिन का नल ढीला हो गया है और बंद करने के बाद भी लगातार बूंद-बूंद टपक रहा है।", "category": "PLUMBING", "urgency": "LOW", "language": "hi", "incident_family": "tap_damage"},
    {"text": "बाथरूम का मुख्य नल अटक गया है और पानी का प्रेशर कंट्रोल नहीं हो रहा है।", "category": "PLUMBING", "urgency": "MEDIUM", "language": "hi", "incident_family": "tap_damage"},
    {"text": "Kitchen sink ka tap tut gaya hai handle alag ho gaya continuous paani beh raha hai band nahi ho raha.", "category": "PLUMBING", "urgency": "HIGH", "language": "hi", "incident_family": "tap_damage"},
    {"text": "वॉश बेसिनचा नळ सैल झाला असून तो बंद केला तरी सतत पाणी गळत राहते.", "category": "PLUMBING", "urgency": "LOW", "language": "mr", "incident_family": "tap_damage"},
    {"text": "बाथरूमचा नळ जाम झाला आहे आणि उघडताना खूप आवाज करतो कृपया बदलून द्या.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "mr", "incident_family": "tap_damage"},
    {"text": "Washbasin cha tap loose ahe aani continuous paani thibaktay plumber la pathva.", "category": "PLUMBING", "urgency": "LOW", "language": "mr", "incident_family": "tap_damage"},

    # Family 3: drainage_blockage
    {"text": "Shower floor drain is completely blocked with stagnant dirty water backing up into bathroom.", "category": "PLUMBING", "urgency": "HIGH", "language": "en", "incident_family": "drainage_blockage"},
    {"text": "Kitchen sink drain is draining extremely slowly causing greasy foul-smelling buildup.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "en", "incident_family": "drainage_blockage"},
    {"text": "Utility balcony washing machine drain line is clogged and overflowing during rinse cycles.", "category": "PLUMBING", "urgency": "HIGH", "language": "en", "incident_family": "drainage_blockage"},
    {"text": "बाथरूम की नाली पूरी तरह जाम है और नहाने के बाद गंदा पानी घंटों तक भरा रहता है।", "category": "PLUMBING", "urgency": "HIGH", "language": "hi", "incident_family": "drainage_blockage"},
    {"text": "किचन सिंक का ड्रेन चोक हो गया है, बर्तन धोने का गंदा पानी धीरे-धीरे निकल रहा है।", "category": "PLUMBING", "urgency": "MEDIUM", "language": "hi", "incident_family": "drainage_blockage"},
    {"text": "Shower drain bilkul block ho gaya hai paani bahar bathroom me phail raha hai.", "category": "PLUMBING", "urgency": "HIGH", "language": "hi", "incident_family": "drainage_blockage"},
    {"text": "बाथरूममधील पाण्याचा निचरा होणारी मोरी तुंबली असून दुर्गंधीयुक्त पाणी साचून राहत आहे.", "category": "PLUMBING", "urgency": "HIGH", "language": "mr", "incident_family": "drainage_blockage"},
    {"text": "स्वयंपाकघरातील सिंकची ड्रेनेज पाईप चोक झाली आहे, पाणी खूप हळू वाहत आहे.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "mr", "incident_family": "drainage_blockage"},
    {"text": "Bathroom chya mori madhe kachra adakun drainage block zala ahe cleaning garjeche ahe.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "mr", "incident_family": "drainage_blockage"},

    # Family 4: flush_cistern_fault
    {"text": "Toilet flush tank button is stuck depressed and water is running down the pan nonstop.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "en", "incident_family": "flush_cistern_fault"},
    {"text": "Commode flush tank inlet valve does not refill automatically unless manually wiggled.", "category": "PLUMBING", "urgency": "LOW", "language": "en", "incident_family": "flush_cistern_fault"},
    {"text": "Flush valve seal is deteriorated causing constant faint hissing sound and water waste.", "category": "PLUMBING", "urgency": "LOW", "language": "en", "incident_family": "flush_cistern_fault"},
    {"text": "टॉयलेट का फ्लश टैंक बटन अटक गया है और फ्लश में लगातार पानी बहता जा रहा है।", "category": "PLUMBING", "urgency": "MEDIUM", "language": "hi", "incident_family": "flush_cistern_fault"},
    {"text": "कमोड की टंकी में पानी भरने वाला वाल्व खराब है और भरता ही नहीं है।", "category": "PLUMBING", "urgency": "LOW", "language": "hi", "incident_family": "flush_cistern_fault"},
    {"text": "Flush tank ka button dabane ke baad wapas nahi aata paani waste ho raha hai continuously.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "hi", "incident_family": "flush_cistern_fault"},
    {"text": "टॉयलेट फ्लश टँकचे बटण अडकले असून फ्लशमधून न थांबता पाणी वाहत आहे.", "category": "PLUMBING", "urgency": "MEDIUM", "language": "mr", "incident_family": "flush_cistern_fault"},
    {"text": "कमोडच्या फ्लश टँकमध्ये पाणी भरत नसून इनलेट पाईपमधून पाणी जोरात गळत आहे.", "category": "PLUMBING", "urgency": "HIGH", "language": "mr", "incident_family": "flush_cistern_fault"},
    {"text": "Flush cistern madhun satat paani wahat ahe button dable tari leak hot ahe.", "category": "PLUMBING", "urgency": "LOW", "language": "mr", "incident_family": "flush_cistern_fault"},

    # Family 5: sewage_backflow
    {"text": "Raw sewage blackwater is backing up out of the ground floor toilet commode into bathroom!", "category": "PLUMBING", "urgency": "CRITICAL", "language": "en", "incident_family": "sewage_backflow"},
    {"text": "Severe sewage odor and black sludge bubbling up through kitchen floor gully trap.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "en", "incident_family": "sewage_backflow"},
    {"text": "External sewage chamber near building entrance is overflowing with foul sludge.", "category": "PLUMBING", "urgency": "HIGH", "language": "en", "incident_family": "sewage_backflow"},
    {"text": "ग्राउंड फ्लोर के टॉयलेट से गटर का गंदा सीवेज पानी उल्टा बहकर घर में आ रहा है!", "category": "PLUMBING", "urgency": "CRITICAL", "language": "hi", "incident_family": "sewage_backflow"},
    {"text": "सीवर लाइन जाम होने से नाली से गंदा बदबूदार कीचड़ बाहर निकल रहा है भारी दुर्गंध है।", "category": "PLUMBING", "urgency": "HIGH", "language": "hi", "incident_family": "sewage_backflow"},
    {"text": "Toilet se gutter ka badbudaar paani backflow ho raha hai bahut gandagi fail rahi hai.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "hi", "incident_family": "sewage_backflow"},
    {"text": "तळमजल्यावरील टॉयलेटमधून गटाराचे दुर्गंधीयुक्त घाण पाणी उलटे वर येत आहे त्वरित प्लंबर पाठवा!", "category": "PLUMBING", "urgency": "CRITICAL", "language": "mr", "incident_family": "sewage_backflow"},
    {"text": "ड्रेनेज चेंबर तुंबल्यामुळे इमारतीच्या प्रवेशद्वाराजवळ सांडपाणी साचले असून दुर्गंधी पसरली आहे.", "category": "PLUMBING", "urgency": "HIGH", "language": "mr", "incident_family": "sewage_backflow"},
    {"text": "Commode madhun gutter che kaale paani baher yet ahe flat madhe saachle ahe urgent cleaning.", "category": "PLUMBING", "urgency": "CRITICAL", "language": "mr", "incident_family": "sewage_backflow"},

    # =========================================================================
    # ELECTRICAL (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: sparking_switchboard
    {"text": "Electrical switchboard in bedroom is actively sparking with loud crackling and burning plastic smell!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "en", "incident_family": "sparking_switchboard"},
    {"text": "Corridor main distribution board throwing visible sparks and smoking, fire risk imminent!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "en", "incident_family": "sparking_switchboard"},
    {"text": "Living room light switch sparks intermittently when flipped on and feels hot to touch.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "en", "incident_family": "sparking_switchboard"},
    {"text": "बेडरूम के स्विचबोर्ड से तेज चिंगारियां निकल रही हैं और तार जलने की गंध आ रही है तुरंत बिजली काटें!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "sparking_switchboard"},
    {"text": "मीटर बॉक्स के अंदर शॉर्ट सर्किट होकर स्पार्किंग हो रही है आग लगने का गंभीर खतरा है।", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "sparking_switchboard"},
    {"text": "Switch board me se spark aur chingari nikal rahi hai aur plastic smell aa rahi hai jaldi electrician bhejo.", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "sparking_switchboard"},
    {"text": "मीटर रूममधील स्विचबोर्डमधून मोठ्या ठिणग्या उडत असून वायर जळण्याचा वास येत आहे तातडीने मदत पाठवा!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "sparking_switchboard"},
    {"text": "हॉलमधील मुख्य बोर्डवर स्पार्किंग होत आहे आणि बटण गरम झाले आहे शॉर्ट सर्किटची भीती आहे.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "mr", "incident_family": "sparking_switchboard"},
    {"text": "Switchboard madhun heavy sparks aani dhur yet ahe emergency electrician la bolva fire hazard ahe.", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "sparking_switchboard"},

    # Family 2: geyser_short_circuit
    {"text": "Bathroom geyser gave mild electric shock when resident touched the metallic braided hose pipe!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "en", "incident_family": "geyser_short_circuit"},
    {"text": "Water heater trip switch burned out with loud pop and sparks flew from power socket.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "en", "incident_family": "geyser_short_circuit"},
    {"text": "Geyser heating light turns on but water pipe carries noticeable electric tingling sensation.", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "en", "incident_family": "geyser_short_circuit"},
    {"text": "बाथरूम के गीजर का पाइप छूने पर करंट लगा है, गीजर में अर्थिंग की समस्या है तुरंत जांचें!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "geyser_short_circuit"},
    {"text": "वॉटर हीटर चालू करते ही जोर की आवाज के साथ धुआं निकला और पावर सॉकेट काला हो गया।", "category": "ELECTRICAL", "urgency": "HIGH", "language": "hi", "incident_family": "geyser_short_circuit"},
    {"text": "Geyser on karne par tap me current aa raha hai hath lagaya toh electric shock laga jaldi dekho.", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "geyser_short_circuit"},
    {"text": "बाथरूममधील गिझर सुरू असताना नळाला स्पर्श केल्यावर जोरदार विजेचा धक्का बसला तातडीने दुरुस्ती करा!", "category": "ELECTRICAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "geyser_short_circuit"},
    {"text": "वॉटर हीटरच्या सॉकेटमधून ठिणग्या निघाल्या असून गिझरचे प्लग जळाले आहे.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "mr", "incident_family": "geyser_short_circuit"},
    {"text": "Geyser pipe la hath lavlyavar current basla ahe earthing problem ahe electrician pathva.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "mr", "incident_family": "geyser_short_circuit"},

    # Family 3: power_outage_partial
    {"text": "One complete supply line is down in Flat 804, AC and refrigerator sockets have no power.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "en", "incident_family": "power_outage_partial"},
    {"text": "Entire 12th floor corridor has no lighting, complete dark hallway creating safety hazard.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "en", "incident_family": "power_outage_partial"},
    {"text": "Partial power failure across three apartments in Tower 4 after voltage fluctuation.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "en", "incident_family": "power_outage_partial"},
    {"text": "फ्लैट में एक फेज की बिजली गुल है, फ्रिज और गीजर के प्लग में करंट नहीं आ रहा है।", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "power_outage_partial"},
    {"text": "9वीं मंजिल की पूरी लॉबी में लाइट बंद है और अंधेरे में लोगों को आने-जाने में परेशानी हो रही है।", "category": "ELECTRICAL", "urgency": "HIGH", "language": "hi", "incident_family": "power_outage_partial"},
    {"text": "Ghar ke aadhe kamro me light nahi hai, single line fuse udd gaya hai fuse check karo.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "power_outage_partial"},
    {"text": "फ्लॅटमधील एका फेजचा वीजपुरवठा खंडित झाला असून एसी आणि फ्रिजचे सॉकेट बंद पडले आहेत.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "power_outage_partial"},
    {"text": "सातव्या मजल्यावरील कॉरिडॉरची संपूर्ण वीज गेली असून अंधार पसरला आहे कृपया दिवा लावा.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "mr", "incident_family": "power_outage_partial"},
    {"text": "Flat madhye partial power cut ahe hall chi light chalat nahi supply line geley vatate.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "power_outage_partial"},

    # Family 4: corridor_light_fused
    {"text": "Ceiling light tube outside flat 302 has fused and is flickering continuously.", "category": "ELECTRICAL", "urgency": "LOW", "language": "en", "incident_family": "corridor_light_fused"},
    {"text": "Emergency stairwell light on 5th floor landing is blown and pitch black stairs fall risk.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "en", "incident_family": "corridor_light_fused"},
    {"text": "Tower entrance foyer decorative LED panel light is dim and making a buzzing noise.", "category": "ELECTRICAL", "urgency": "LOW", "language": "en", "incident_family": "corridor_light_fused"},
    {"text": "फ्लैट 501 के सामने की सीलिंग लाइट फ्यूज हो गई है और लॉबी में मंद रोशनी है।", "category": "ELECTRICAL", "urgency": "LOW", "language": "hi", "incident_family": "corridor_light_fused"},
    {"text": "सीढ़ियों की 3 ट्यूबलाइट बंद पड़ी हैं अंधेरे में लोग ठोकर खाकर गिर रहे हैं तुरंत बदलें।", "category": "ELECTRICAL", "urgency": "HIGH", "language": "hi", "incident_family": "corridor_light_fused"},
    {"text": "Corridor ki tube light fuse ho gayi hai blink kar rahi hai replacement chahiye.", "category": "ELECTRICAL", "urgency": "LOW", "language": "hi", "incident_family": "corridor_light_fused"},
    {"text": "तिसऱ्या मजल्यावरील जिन्यावरील दिवा निकामी झाला असून नवीन बल्ब लावणे आवश्यक आहे.", "category": "ELECTRICAL", "urgency": "LOW", "language": "mr", "incident_family": "corridor_light_fused"},
    {"text": "फ्लॅटच्या समोरील कॉरिडॉरची ट्यूबलाईट सतत लुकलुकत आहे व डोळ्यांना त्रास होत आहे.", "category": "ELECTRICAL", "urgency": "LOW", "language": "mr", "incident_family": "corridor_light_fused"},
    {"text": "Floor chya passage madhla bulb fuse zala ahe andhar ahe bulb change kara.", "category": "ELECTRICAL", "urgency": "LOW", "language": "mr", "incident_family": "corridor_light_fused"},

    # Family 5: circuit_breaker_tripping
    {"text": "Distribution board main MCB trips every time kitchen microwave and kettle are on simultaneously.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "en", "incident_family": "circuit_breaker_tripping"},
    {"text": "Sub-circuit breaker trips randomly twice a day without any high power appliance running.", "category": "ELECTRICAL", "urgency": "LOW", "language": "en", "incident_family": "circuit_breaker_tripping"},
    {"text": "Master bedroom MCB switch is loose inside board with burned terminal and smells heated.", "category": "ELECTRICAL", "urgency": "HIGH", "language": "en", "incident_family": "circuit_breaker_tripping"},
    {"text": "रसोई में ओवन चालू करते ही एमसीबी बार-बार ट्रिप हो रही है लोड चेक करें।", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "circuit_breaker_tripping"},
    {"text": "बिजली का मुख्य कट-आउट स्विच बहुत ढीला हो गया है और अपने आप नीचे गिर जाता है।", "category": "ELECTRICAL", "urgency": "LOW", "language": "hi", "incident_family": "circuit_breaker_tripping"},
    {"text": "MCB bar bar trip ho raha hai bina kisi heavy appliance ke wiring check karwao.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "circuit_breaker_tripping"},
    {"text": "किचनमध्ये मिक्सर सुरू करताच मेन एमसीबी वारंवार ट्रिप होत आहे वायरिंग तपासावी.", "category": "ELECTRICAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "circuit_breaker_tripping"},
    {"text": "एमसीबी बॉक्समधील एक स्वीच सैल झाला असून विद्युत पुरवठा वारंवार खंडित होतो.", "category": "ELECTRICAL", "urgency": "LOW", "language": "mr", "incident_family": "circuit_breaker_tripping"},
    {"text": "Board cha MCB thodya velane trip hotoy fuse madhe problem vatato.", "category": "ELECTRICAL", "urgency": "LOW", "language": "mr", "incident_family": "circuit_breaker_tripping"},

    # =========================================================================
    # LIFT (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: lift_stuck_with_passengers
    {"text": "Passenger elevator stuck between 14th and 15th floors with four residents trapped inside!", "category": "LIFT", "urgency": "CRITICAL", "language": "en", "incident_family": "lift_stuck_with_passengers"},
    {"text": "Tower 6 Lift A stopped abruptly mid-shaft, pregnant woman trapped inside calling for emergency help!", "category": "LIFT", "urgency": "CRITICAL", "language": "en", "incident_family": "lift_stuck_with_passengers"},
    {"text": "Service lift stopped between basement and ground floor, maintenance worker trapped inside with heavy load.", "category": "LIFT", "urgency": "CRITICAL", "language": "en", "incident_family": "lift_stuck_with_passengers"},
    {"text": "टावर 8 की लिफ्ट 9वें और 10वें फ्लोर के बीच अटक गई है, अंदर बुजुर्ग और बच्चे फंसे हैं जल्दी निकालो!", "category": "LIFT", "urgency": "CRITICAL", "language": "hi", "incident_family": "lift_stuck_with_passengers"},
    {"text": "लिफ्ट अचानक बीच में रुक गई है पंखा बंद हो गया है और 3 लोग अंदर फंसे हुए घबरा रहे हैं।", "category": "LIFT", "urgency": "CRITICAL", "language": "hi", "incident_family": "lift_stuck_with_passengers"},
    {"text": "Tower B lift beech me band ho gayi hai family andar phasi hui hai bachao jaldi emergency technician bhejo.", "category": "LIFT", "urgency": "CRITICAL", "language": "hi", "incident_family": "lift_stuck_with_passengers"},
    {"text": "टावर ३ ची लिफ्ट सहाव्या मजल्यावर अडकली असून आत ४ नागरिक अडकले आहेत तातडीने मदत पाठवा!", "category": "LIFT", "urgency": "CRITICAL", "language": "mr", "incident_family": "lift_stuck_with_passengers"},
    {"text": "लिफ्ट अचानक बंद पडली आहे आणि प्रवासी आत अडकले आहेत, आतील फॅनही बंद झाला आहे.", "category": "LIFT", "urgency": "CRITICAL", "language": "mr", "incident_family": "lift_stuck_with_passengers"},
    {"text": "Lift number 2 madhe lok adakle ahet gate ughadat nahi emergency service team la lavkar bolva.", "category": "LIFT", "urgency": "CRITICAL", "language": "mr", "incident_family": "lift_stuck_with_passengers"},

    # Family 2: lift_door_jammed
    {"text": "Lift outer door is jammed half open on 7th floor with exposed elevator shaft hazard!", "category": "LIFT", "urgency": "CRITICAL", "language": "en", "incident_family": "lift_door_jammed"},
    {"text": "Lift door repeatedly closes violently with excessive force without retracting when sensor blocked.", "category": "LIFT", "urgency": "HIGH", "language": "en", "incident_family": "lift_door_jammed"},
    {"text": "Lift door safety infrared sensor is defective, trapping passengers' arms upon closing.", "category": "LIFT", "urgency": "HIGH", "language": "en", "incident_family": "lift_door_jammed"},
    {"text": "7वीं मंजिल पर लिफ्ट का दरवाजा आधा खुला अटक गया है और नीचे का शाफ्ट खुला दिख रहा है बेहद खतरनाक है!", "category": "LIFT", "urgency": "CRITICAL", "language": "hi", "incident_family": "lift_door_jammed"},
    {"text": "लिफ्ट का दरवाजा बहुत जोर से बंद हो रहा है, सेंसर काम नहीं कर रहा किसी को चोट लग सकती है।", "category": "LIFT", "urgency": "HIGH", "language": "hi", "incident_family": "lift_door_jammed"},
    {"text": "Lift ka gate jam ho gaya hai floor par nahi khul raha log bahar nahi aa pa rahe the.", "category": "LIFT", "urgency": "HIGH", "language": "hi", "incident_family": "lift_door_jammed"},
    {"text": "पाचव्या मजल्यावर लिफ्टचे दार उघडेच अडकले असून लिफ्टची पोकळी उघडी दिसत आहे मोठा अपघात होऊ शकतो!", "category": "LIFT", "urgency": "CRITICAL", "language": "mr", "incident_family": "lift_door_jammed"},
    {"text": "लिफ्टचा सेन्सर खराब झाला असून दार अचानक आणि जोरात आपटत बंद होत आहे.", "category": "LIFT", "urgency": "HIGH", "language": "mr", "incident_family": "lift_door_jammed"},
    {"text": "Lift cha door jam zala ahe aani jorat band hotoy sensors check kara safety risk ahe.", "category": "LIFT", "urgency": "HIGH", "language": "mr", "incident_family": "lift_door_jammed"},

    # Family 3: lift_jerking_noise
    {"text": "Lift produces violent jerking motions and grinding metallic screeching during descent between floors 10 and 6.", "category": "LIFT", "urgency": "HIGH", "language": "en", "incident_family": "lift_jerking_noise"},
    {"text": "Heavy vibrations and shuddering felt inside lift car when carrying more than 3 people.", "category": "LIFT", "urgency": "MEDIUM", "language": "en", "incident_family": "lift_jerking_noise"},
    {"text": "Elevator cables emit rhythmic clanking sound during motion causing alarm among residents.", "category": "LIFT", "urgency": "MEDIUM", "language": "en", "incident_family": "lift_jerking_noise"},
    {"text": "लिफ्ट नीचे आते समय बहुत जोर से झटके खा रही है और लोहे की घिसने जैसी डरावनी आवाज आ रही है।", "category": "LIFT", "urgency": "HIGH", "language": "hi", "incident_family": "lift_jerking_noise"},
    {"text": "लिफ्ट चलने पर बहुत ज्यादा कंपन और आवाज होती है, केबल की जांच करवाई जाए।", "category": "LIFT", "urgency": "MEDIUM", "language": "hi", "incident_family": "lift_jerking_noise"},
    {"text": "Lift me chalte waqt achanak jhatke lag rahe hai aur ajeeb sound aa raha hai safety check karo.", "category": "LIFT", "urgency": "HIGH", "language": "hi", "incident_family": "lift_jerking_noise"},
    {"text": "लिफ्ट वर-खाली जाताना प्रचंड हादरे बसत आहेत आणि लोखंड घासण्याचा विचित्र आवाज येत आहे.", "category": "LIFT", "urgency": "HIGH", "language": "mr", "incident_family": "lift_jerking_noise"},
    {"text": "लिफ्टच्या केबिनमध्ये खूप कंपन जाणवते आहे, रोप किंवा मोटरची तपासणी करणे गरजेचे आहे.", "category": "LIFT", "urgency": "MEDIUM", "language": "mr", "incident_family": "lift_jerking_noise"},
    {"text": "Lift chalताना khup mothe jhatke det ahe aani aawaz yetoy technician pathva.", "category": "LIFT", "urgency": "MEDIUM", "language": "mr", "incident_family": "lift_jerking_noise"},

    # Family 4: lift_button_unresponsive
    {"text": "Floor buttons for 8th and 9th floor inside Lift 1 do not illuminate or register trapping passengers from reaching floor.", "category": "LIFT", "urgency": "HIGH", "language": "en", "incident_family": "lift_button_unresponsive"},
    {"text": "External landing call button on 11th floor is physically broken pushed into the wall socket.", "category": "LIFT", "urgency": "MEDIUM", "language": "en", "incident_family": "lift_button_unresponsive"},
    {"text": "Alarm and fan buttons inside lift cabin are unresponsive when pressed.", "category": "LIFT", "urgency": "MEDIUM", "language": "en", "incident_family": "lift_button_unresponsive"},
    {"text": "लिफ्ट के अंदर 4 और 5 नंबर का बटन काम नहीं कर रहा है, दबाने पर लाइट नहीं जलती।", "category": "LIFT", "urgency": "LOW", "language": "hi", "incident_family": "lift_button_unresponsive"},
    {"text": "तीसरी मंजिल पर बाहर लगा लिफ्ट का अप-बटन टूट गया है और अंदर धंस गया है।", "category": "LIFT", "urgency": "MEDIUM", "language": "hi", "incident_family": "lift_button_unresponsive"},
    {"text": "Lift ka calling button floor 6 par press karne par respond nahi kar raha floor skip ho raha hai.", "category": "LIFT", "urgency": "HIGH", "language": "hi", "incident_family": "lift_button_unresponsive"},
    {"text": "लिफ्टमधील आठव्या मजल्याचे बटण चालत नाहीये, दाबल्यावर प्रतिसाद मिळत नाही.", "category": "LIFT", "urgency": "LOW", "language": "mr", "incident_family": "lift_button_unresponsive"},
    {"text": "दुसऱ्या मजल्यावरील लिफ्ट बोलवण्याचे बाहेरील बटण तुटून आत गेले आहे दुरुस्त करा.", "category": "LIFT", "urgency": "MEDIUM", "language": "mr", "incident_family": "lift_button_unresponsive"},
    {"text": "Lift cabin che button dabun pan light lagat nahi floor select hot nahi.", "category": "LIFT", "urgency": "LOW", "language": "mr", "incident_family": "lift_button_unresponsive"},

    # Family 5: lift_display_error
    {"text": "Digital floor indicator inside lift car is flickering rapidly showing erroneous inverted characters.", "category": "LIFT", "urgency": "LOW", "language": "en", "incident_family": "lift_display_error"},
    {"text": "Ground floor outside lift position display shows floor 18 permanently while lift moves normally.", "category": "LIFT", "urgency": "LOW", "language": "en", "incident_family": "lift_display_error"},
    {"text": "Direction arrow LED display inside lift car is unlit during upward motion.", "category": "LIFT", "urgency": "LOW", "language": "en", "incident_family": "lift_display_error"},
    {"text": "लिफ्ट की डिजिटल स्क्रीन पर गलत फ्लोर नंबर दिख रहा है और डिस्प्ले लगातार ब्लिंक कर रहा है।", "category": "LIFT", "urgency": "LOW", "language": "hi", "incident_family": "lift_display_error"},
    {"text": "भूतल पर लिफ्ट का इंडिकेटर बंद पड़ा है जिससे पता नहीं चलता लिफ्ट कहां है।", "category": "LIFT", "urgency": "LOW", "language": "hi", "incident_family": "lift_display_error"},
    {"text": "Lift display screen par arrow ulta dikh raha hai indicator reset karne ki zaroorat hai.", "category": "LIFT", "urgency": "LOW", "language": "hi", "incident_family": "lift_display_error"},
    {"text": "लिफ्टच्या आतील मजला दर्शवणारा डिजिटल डिस्प्ले बंद पडला असून मजला समजत नाही.", "category": "LIFT", "urgency": "MEDIUM", "language": "mr", "incident_family": "lift_display_error"},
    {"text": "तळमजल्यावरील लिफ्टच्या फलकावर सतत चुकीचा मजला क्रमांक दाखवत आहे.", "category": "LIFT", "urgency": "LOW", "language": "mr", "incident_family": "lift_display_error"},
    {"text": "Lift display panel blink hot ahe floor number neat disat nahi reset kara.", "category": "LIFT", "urgency": "MEDIUM", "language": "mr", "incident_family": "lift_display_error"},

    # =========================================================================
    # CLEANLINESS (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: garbage_pile_corridor
    {"text": "Huge heap of decomposing organic waste and garbage bags dumped on 3rd floor staircase spreading foul odor.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "en", "incident_family": "garbage_pile_corridor"},
    {"text": "Maggots and toxic rot observed from leaking garbage pile abandoned in lobby corridor for 4 days!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "en", "incident_family": "garbage_pile_corridor"},
    {"text": "Multiple overflowing trash bags blocking emergency fire exit passage completely on 12th floor!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "en", "incident_family": "garbage_pile_corridor"},
    {"text": "तीसरी मंजिल की लॉबी में सड़ा हुआ कचरा पड़ा है, कीड़े रेंग रहे हैं और भयानक बदबू फैल रही है!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "hi", "incident_family": "garbage_pile_corridor"},
    {"text": "सीढ़ियों के पास कूड़े का ढेर लगा है जिससे पूरा फ्लोर बदबू से भर गया है तुरंत सफाई कराएं।", "category": "CLEANLINESS", "urgency": "HIGH", "language": "hi", "incident_family": "garbage_pile_corridor"},
    {"text": "Lobby me 3 din se garbage bags pade hue hai smell bohot gandi aa rahi hai health risk hai.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "hi", "incident_family": "garbage_pile_corridor"},
    {"text": "चौथ्या मजल्यावरील जिन्यामध्ये सडलेल्या कचऱ्याचे ढीग साचले असून भयानक दुर्गंधी व कीडे झाले आहेत!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "mr", "incident_family": "garbage_pile_corridor"},
    {"text": "कॉरिडॉरमध्ये कचऱ्याच्या पिशव्यांचा ढीग पडला असून आपत्कालीन दरवाजा बंद झाला आहे तातडीने उचला!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "mr", "incident_family": "garbage_pile_corridor"},
    {"text": "Staircase javal kachra jama zala ahe aani gand yet ahe housekeeping team la pathva.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "mr", "incident_family": "garbage_pile_corridor"},

    # Family 2: cockroach_pest_infestation
    {"text": "Severe German cockroach infestation swarming out of garbage chute duct into 5th floor flats.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "en", "incident_family": "cockroach_pest_infestation"},
    {"text": "Aggressive sewer rats infesting podium lobby biting electrical cables and posing rabies hazard!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "en", "incident_family": "cockroach_pest_infestation"},
    {"text": "Common hallway has visible cockroach clusters near duct covers requiring pest control spraying.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "en", "incident_family": "cockroach_pest_infestation"},
    {"text": "गारबेज डक्ट से सैकड़ों कॉकरोच निकलकर घरों में घुस रहे हैं तत्काल पेस्ट कंट्रोल करवाएं।", "category": "CLEANLINESS", "urgency": "HIGH", "language": "hi", "incident_family": "cockroach_pest_infestation"},
    {"text": "सीढ़ियों पर बड़े सीवर के चूहे बच्चों पर झपट रहे हैं और तार काट रहे हैं जानलेवा खतरा है!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "hi", "incident_family": "cockroach_pest_infestation"},
    {"text": "Floor duct ke paas cockroaches aur pest kaafi badh gaye hai pest control spray karwana hai.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "hi", "incident_family": "cockroach_pest_infestation"},
    {"text": "कचरा डक्टमधून शेकडो झुरळे बाहेर पडून फ्लॅट्समध्ये शिरत आहेत तातडीने औषध फवारणी करा.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "mr", "incident_family": "cockroach_pest_infestation"},
    {"text": "इमारतीच्या कॉरिडॉरमध्ये विषारी किटक आणि मोठे उंदीर फिरत असून नागरिकांच्या आरोग्यास गंभीर धोका आहे!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "mr", "incident_family": "cockroach_pest_infestation"},
    {"text": "Lobby madhe zural aani kidyanchi sankhya waadhli ahe pest control treatment lavkar karave.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "mr", "incident_family": "cockroach_pest_infestation"},

    # Family 3: stray_dog_poop
    {"text": "Stray dog feces and urine on 2nd floor elevator entrance tiles left uncleaned since morning.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "en", "incident_family": "stray_dog_poop"},
    {"text": "Cat urine stains on podium lobby doormat causing irritating pungent smell.", "category": "CLEANLINESS", "urgency": "LOW", "language": "en", "incident_family": "stray_dog_poop"},
    {"text": "Animal droppings found near basement parking pillar B4 need disinfectant washing.", "category": "CLEANLINESS", "urgency": "LOW", "language": "en", "incident_family": "stray_dog_poop"},
    {"text": "लिफ्ट के बाहर कुत्ते की गंदगी पड़ी है, लोग फिसल सकते हैं फिनाइल से पोछा लगवाएं।", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "hi", "incident_family": "stray_dog_poop"},
    {"text": "पार्किंग क्षेत्र में बिल्ली का मल पड़ा है सफाई कर्मचारी को भेजें।", "category": "CLEANLINESS", "urgency": "LOW", "language": "hi", "incident_family": "stray_dog_poop"},
    {"text": "Lift ke aage dog poop pada hai morning se kisi ne saaf nahi kiya smell aa rahi hai.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "hi", "incident_family": "stray_dog_poop"},
    {"text": "लिफ्टच्या प्रवेशद्वारासमोर भटक्या कुत्र्याची घाण पडली असून फिनाईलने साफ करणे आवश्यक आहे.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "mr", "incident_family": "stray_dog_poop"},
    {"text": "पार्किंग परिसरात प्राण्यांची विष्ठा पडली असून दुर्गंधी येत आहे सफाई कामगारास पाठवा.", "category": "CLEANLINESS", "urgency": "LOW", "language": "mr", "incident_family": "stray_dog_poop"},
    {"text": "Basement madhe dog feces ahe uncleaned ahe housekeeping la bolo disinfectant marayla.", "category": "CLEANLINESS", "urgency": "LOW", "language": "mr", "incident_family": "stray_dog_poop"},

    # Family 4: staircase_spill_stain
    {"text": "Sticky syrup and oil spill along 4th floor staircase stairs causing slippery hazard for residents.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "en", "incident_family": "staircase_spill_stain"},
    {"text": "Heavy industrial chemical lubricant spilled in staircase landing causing residents dizziness and nausea!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "en", "incident_family": "staircase_spill_stain"},
    {"text": "Dust and construction debris coating corridor floor tiles outside flat 903.", "category": "CLEANLINESS", "urgency": "LOW", "language": "en", "incident_family": "staircase_spill_stain"},
    {"text": "सीढ़ियों पर तेल गिर गया है जिससे फिसलन हो रही है किसी का पैर फिसल सकता है।", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "hi", "incident_family": "staircase_spill_stain"},
    {"text": "दीवारों पर गुटखा और पान की पीक थूकी हुई है, दीवारों को साफ कराया जाए।", "category": "CLEANLINESS", "urgency": "LOW", "language": "hi", "incident_family": "staircase_spill_stain"},
    {"text": "Staircase par oil gira hua hai slip hone ka khatra hai jaldi mopping karwao.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "hi", "incident_family": "staircase_spill_stain"},
    {"text": "जिन्यावरील पायऱ्यांवर तेल सांडले असून घसरून पडण्याचा धोका निर्माण झाला आहे.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "mr", "incident_family": "staircase_spill_stain"},
    {"text": "जिन्याच्या पायऱ्यांवर रासायनिक तेलाची गळती झाल्याने विषारी धूर व वास येत आहे तातडीने मदत पाठवा!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "mr", "incident_family": "staircase_spill_stain"},
    {"text": "Stairs var tel saandla ahe floor slippery zala ahe housekeeping la pocha marayla sanga.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "mr", "incident_family": "staircase_spill_stain"},

    # Family 5: duct_waste_dumping
    {"text": "Plumbing shaft bottom filled with combustible scrap paper, plastics and smoldering cigarette butts fire risk!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "en", "incident_family": "duct_waste_dumping"},
    {"text": "Bottom of plumbing duct filled with stagnant rotting garbage causing foul stench and heavy mosquito breeding.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "en", "incident_family": "duct_waste_dumping"},
    {"text": "Accumulation of pigeon droppings and dry feathers choking open utility shaft sill spreading allergy risk.", "category": "CLEANLINESS", "urgency": "HIGH", "language": "en", "incident_family": "duct_waste_dumping"},
    {"text": "डक्ट में ज्वलनशील कचरा और सिगरेट के टुकड़े फेंके गए हैं आग का बड़ा खतरा है तुरंत हटाएं!", "category": "CLEANLINESS", "urgency": "CRITICAL", "language": "hi", "incident_family": "duct_waste_dumping"},
    {"text": "प्लंबिंग शाफ्ट के नीचे सूखा कचरा जमा हो गया है सफाई कराएं।", "category": "CLEANLINESS", "urgency": "LOW", "language": "hi", "incident_family": "duct_waste_dumping"},
    {"text": "Duct me kachra aur bottle phenki hui hai niche deposit ho gaya hai safai karwao.", "category": "CLEANLINESS", "urgency": "LOW", "language": "hi", "incident_family": "duct_waste_dumping"},
    {"text": "प्लंबिंग डक्टमध्ये नागरिकांनी कचरा फेकला असून तिथे घाण साचली आहे साफ करावी.", "category": "CLEANLINESS", "urgency": "LOW", "language": "mr", "incident_family": "duct_waste_dumping"},
    {"text": "शाफ्टच्या खिडकीवर कबुतरांची विष्ठा आणि पिसे साचली असून अस्वच्छता पसरली आहे.", "category": "CLEANLINESS", "urgency": "LOW", "language": "mr", "incident_family": "duct_waste_dumping"},
    {"text": "Duct shaft madhe bottle aani plastic kachra saachla ahe safai kamgar pathva.", "category": "CLEANLINESS", "urgency": "MEDIUM", "language": "mr", "incident_family": "duct_waste_dumping"},

    # =========================================================================
    # WATER_SUPPLY (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: no_water_tower
    {"text": "Total water outage across all 80 flats in Tower 11 since morning, dry taps and no drinking water!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "en", "incident_family": "no_water_tower"},
    {"text": "Complete water failure throughout entire wing, emergency tanker delivery required immediately!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "en", "incident_family": "no_water_tower"},
    {"text": "Both domestic and flushing water lines bone dry across high rise floors 15 through 20.", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "en", "incident_family": "no_water_tower"},
    {"text": "टावर 11 में सुबह 6 बजे से एक बूंद पानी नहीं आ रहा है, सभी फ्लैट में पानी खत्म हो गया है तुरंत टैंकर भेजो!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "hi", "incident_family": "no_water_tower"},
    {"text": "पूरी बिल्डिंग में पानी की सप्लाई बंद है, पीने और टॉयलेट के लिए पानी नहीं बचा है।", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "hi", "incident_family": "no_water_tower"},
    {"text": "Tower 9 me bilkul paani nahi hai subah se, tanki poori khali hai emergency water tanker chahiye.", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "hi", "incident_family": "no_water_tower"},
    {"text": "टावर १२ मध्ये सकाळपासून पाणीपुरवठा पूर्णपणे बंद झाला असून सर्व नळ कोरडे पडले आहेत तातडीने टँकर पाठवा!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "mr", "incident_family": "no_water_tower"},
    {"text": "संपूर्ण विंगमध्ये पाणी नाही, पिण्याच्या पाण्याचे मोठे दुर्भिक्ष निर्माण झाले आहे.", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "mr", "incident_family": "no_water_tower"},
    {"text": "Building madhe paani bilkul nahi ahe, taps dry ahet emergency water supply chalu kara.", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "mr", "incident_family": "no_water_tower"},

    # Family 2: low_water_pressure
    {"text": "Water pressure in kitchen faucet is barely a trickle, taking 10 minutes to fill a cooking pot.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "en", "incident_family": "low_water_pressure"},
    {"text": "Bathroom shower water pressure is too low to trigger geyser heating mechanism.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "en", "incident_family": "low_water_pressure"},
    {"text": "Mild drop in water pressure noticed during evening peak hours in master bathroom.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "en", "incident_family": "low_water_pressure"},
    {"text": "रसोई के नल में पानी का दबाव बहुत कम है, एक बाल्टी भरने में आधा घंटा लग रहा है।", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "hi", "incident_family": "low_water_pressure"},
    {"text": "शाम के समय पानी का प्रेशर कम हो जाता है, प्रेशर पंप चालू करें।", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "hi", "incident_family": "low_water_pressure"},
    {"text": "Washbasin me paani ka flow bohot slow hai, geyser chalu nahi ho pa raha pressure badhao.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "hi", "incident_family": "low_water_pressure"},
    {"text": "स्वयंपाकघरातील नळात पाण्याचा दाब अत्यंत कमी असून भांडी धुण्यासाठी पाणी पुरेसे येत नाही.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "mr", "incident_family": "low_water_pressure"},
    {"text": "संध्याकाळी पाण्याच्या दाबात घट होते, बूस्टर पंप व्यवस्थित सुरू आहे का तपासावे.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "mr", "incident_family": "low_water_pressure"},
    {"text": "Bathroom madhe paani cha pressure kami ahe barik dhaar yet ahe booster pump check kara.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "mr", "incident_family": "low_water_pressure"},

    # Family 3: dirty_muddy_water
    {"text": "Taps are discharging dark brownish muddy water with heavy sediment unfit for bathing or washing.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "en", "incident_family": "dirty_muddy_water"},
    {"text": "Drinking water supply contaminated with severe sewage odor and toxic oil sheen health catastrophe!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "en", "incident_family": "dirty_muddy_water"},
    {"text": "Black particulate sediment accumulating at bottom of water filter inlet every hour.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "en", "incident_family": "dirty_muddy_water"},
    {"text": "नलों से मटमैला गंदा भूरा पानी आ रहा है, कपड़े धोने और नहाने लायक भी नहीं है।", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "hi", "incident_family": "dirty_muddy_water"},
    {"text": "पीने के पानी में सीवर का पानी मिल गया है, बदबूदार जहरीला पानी आ रहा है तुरंत सप्लाई बंद करें!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "hi", "incident_family": "dirty_muddy_water"},
    {"text": "Taps se muddy brown paani aa raha hai ganda paani supplies me mix ho gaya hai.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "hi", "incident_family": "dirty_muddy_water"},
    {"text": "नळातून चिखलमिश्रित तपकिरी घाण पाणी येत असून ते वापरण्यायोग्य नाही तातडीने टाकी स्वच्छ करा.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "mr", "incident_family": "dirty_muddy_water"},
    {"text": "पिण्याच्या पाण्यात गटाराचे पाणी मिसळले असून विषबाधा होण्याची भीती आहे त्वरित कारवाई करा!", "category": "WATER_SUPPLY", "urgency": "CRITICAL", "language": "mr", "incident_family": "dirty_muddy_water"},
    {"text": "Nalatun ghaan maati mishrit paani yet ahe tank cleaning urgent ahe water sample test kara.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "mr", "incident_family": "dirty_muddy_water"},

    # Family 4: overhead_tank_overflow
    {"text": "Overhead rooftop water tank is overflowing massively, cascades pouring down exterior building facade.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "en", "incident_family": "overhead_tank_overflow"},
    {"text": "Rooftop water tank sensor failed, thousands of liters of clean water wasting down storm drain.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "en", "incident_family": "overhead_tank_overflow"},
    {"text": "Water pump automation controller not shutting down when storage tank reaches 100 percent.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "en", "incident_family": "overhead_tank_overflow"},
    {"text": "छत पर रखी पानी की टंकी ओवरफ्लो होकर लगातार बह रही है और हजारों लीटर पानी बर्बाद हो रहा है!", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "hi", "incident_family": "overhead_tank_overflow"},
    {"text": "वाटर पंप बंद नहीं हो रहा है और छत से पानी झरने की तरह नीचे गिर रहा है मोटर बंद कराएं।", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "hi", "incident_family": "overhead_tank_overflow"},
    {"text": "Terrace tanki overflow ho rahi hai paani building ke bahar gir raha hai motor switch off karo.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "hi", "incident_family": "overhead_tank_overflow"},
    {"text": "छतावरील पाण्याची टाकी ओव्हरफ्लो होऊन हजारो लिटर पाणी वाया जात आहे मोटर त्वरित बंद करा!", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "mr", "incident_family": "overhead_tank_overflow"},
    {"text": "टाकीचा स्वयंचलित सेन्सर बंद पडल्यामुळे पाणी इमारतीच्या बाहेरील भिंतीवरून वाहत आहे.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "mr", "incident_family": "overhead_tank_overflow"},
    {"text": "Terrace varil paani tanki overflow hot ahe pump operator la sangun motor band kara.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "mr", "incident_family": "overhead_tank_overflow"},

    # Family 5: hot_water_line_empty
    {"text": "Central solar hot water line is completely cold at 7:00 AM on cold winter morning.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "en", "incident_family": "hot_water_line_empty"},
    {"text": "Solar hot water pipeline airlock causing cold water output in master bathroom.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "en", "incident_family": "hot_water_line_empty"},
    {"text": "Kitchen utility hot water line has negligible warmth despite sunny day.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "en", "incident_family": "hot_water_line_empty"},
    {"text": "सुबह से सोलर का गरम पानी नहीं आ रहा है, नल से बर्फ जैसा ठंडा पानी निकल रहा है।", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "hi", "incident_family": "hot_water_line_empty"},
    {"text": "सोलर पाइपलाइन में एयरलॉक लग गया है गरम पानी का प्रेशर नहीं बन रहा है।", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "hi", "incident_family": "hot_water_line_empty"},
    {"text": "Solar hot water bilkul thanda aa raha hai subah se system check karwao.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "hi", "incident_family": "hot_water_line_empty"},
    {"text": "सकाळच्या वेळी सोलरचे गरम पाणी अजिबात येत नसून गार पाणी येत आहे सोलर पॅनल तपासा.", "category": "WATER_SUPPLY", "urgency": "MEDIUM", "language": "mr", "incident_family": "hot_water_line_empty"},
    {"text": "सोलर गरम पाण्याच्या पाईपमध्ये एअर लॉक झाला असावा, पाणी खूप संथ येत आहे.", "category": "WATER_SUPPLY", "urgency": "LOW", "language": "mr", "incident_family": "hot_water_line_empty"},
    {"text": "Solar paani thanda ahe garm paani pipeline blockage mule yet nahi ahe urgent check kara.", "category": "WATER_SUPPLY", "urgency": "HIGH", "language": "mr", "incident_family": "hot_water_line_empty"},

    # =========================================================================
    # SECURITY (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: unauthorized_visitor_entry
    {"text": "Unknown aggressive male entered Tower 3 lobby without gate security register entry or resident approval!", "category": "SECURITY", "urgency": "CRITICAL", "language": "en", "incident_family": "unauthorized_visitor_entry"},
    {"text": "Suspicious trespassers roaming 14th floor corridor late at night trying door latches!", "category": "SECURITY", "urgency": "CRITICAL", "language": "en", "incident_family": "unauthorized_visitor_entry"},
    {"text": "Delivery riders tailgating through boom barrier without OTP verification or luggage scanning.", "category": "SECURITY", "urgency": "HIGH", "language": "en", "incident_family": "unauthorized_visitor_entry"},
    {"text": "एक अज्ञात संदिग्ध व्यक्ति बिना किसी एंट्री के टावर 5 में घुस गया और फ्लैट्स के दरवाजे खटखटा रहा है तुरंत गार्ड भेजें!", "category": "SECURITY", "urgency": "CRITICAL", "language": "hi", "incident_family": "unauthorized_visitor_entry"},
    {"text": "रात को दो अजनबी बेसमेंट पार्किंग में गाड़ियों की रेकी कर रहे थे, सुरक्षा में भारी चूक है।", "category": "SECURITY", "urgency": "HIGH", "language": "hi", "incident_family": "unauthorized_visitor_entry"},
    {"text": "Gate par koi checking nahi hai unverified delivery boy building me ghoom raha hai security dispatch karo.", "category": "SECURITY", "urgency": "CRITICAL", "language": "hi", "incident_family": "unauthorized_visitor_entry"},
    {"text": "संशयास्पद अज्ञात व्यक्ती विनापरवानगी इमारतीत शिरली असून फ्लॅटचे कडे वाजवत फिरत आहे तातडीने सुरक्षा रक्षक पाठवा!", "category": "SECURITY", "urgency": "CRITICAL", "language": "mr", "incident_family": "unauthorized_visitor_entry"},
    {"text": "मुख्य गेटवरून कोणतीही नोंद न करता अनोळखी व्यक्ती थेट लिफ्टमध्ये गेली, सुरक्षेत गंभीर त्रुटी आहे.", "category": "SECURITY", "urgency": "HIGH", "language": "mr", "incident_family": "unauthorized_visitor_entry"},
    {"text": "Unknown person lobby madhe firat ahe verification zale nahi ahe security alert pathva.", "category": "SECURITY", "urgency": "CRITICAL", "language": "mr", "incident_family": "unauthorized_visitor_entry"},

    # Family 2: guard_sleeping_gate
    {"text": "Night shift security guard at North Gate was found sound asleep on a chair with open gate unattended.", "category": "SECURITY", "urgency": "HIGH", "language": "en", "incident_family": "guard_sleeping_gate"},
    {"text": "Gate 2 security post completely abandoned during evening peak rush hours, no guard present.", "category": "SECURITY", "urgency": "HIGH", "language": "en", "incident_family": "guard_sleeping_gate"},
    {"text": "Security guard physically drunk and verbally abusing residents at main entry gate!", "category": "SECURITY", "urgency": "CRITICAL", "language": "en", "incident_family": "guard_sleeping_gate"},
    {"text": "रात में गेट नंबर 2 पर गार्ड गहरी नींद में सो रहा था और बैरियर खुला पड़ा था भारी लापरवाही है।", "category": "SECURITY", "urgency": "HIGH", "language": "hi", "incident_family": "guard_sleeping_gate"},
    {"text": "शाम के समय मेन गेट पर कोई गार्ड मौजूद नहीं था और गाड़ियां बिना रोक-टोक आ रही थीं।", "category": "SECURITY", "urgency": "HIGH", "language": "hi", "incident_family": "guard_sleeping_gate"},
    {"text": "मेन गेट पर सुरक्षा गार्ड शराब के नशे में धुत होकर निवासियों से मारपीट पर उतारू है तुरंत पुलिस बुलाएं!", "category": "SECURITY", "urgency": "CRITICAL", "language": "hi", "incident_family": "guard_sleeping_gate"},
    {"text": "रात्रीच्या वेळी उत्तर गेटवरील सुरक्षा रक्षक खुर्चीवर झोपलेला आढळला आणि गेट उघडेच होते सुरक्षेचा मोठा प्रश्न आहे.", "category": "SECURITY", "urgency": "HIGH", "language": "mr", "incident_family": "guard_sleeping_gate"},
    {"text": "गेट क्रमांक १ वर सुरक्षा रक्षक दारू पिऊन नागरिकांशी वाद घालत असून मारहाण करत आहे तात्काळ मदत पाठवा!", "category": "SECURITY", "urgency": "CRITICAL", "language": "mr", "incident_family": "guard_sleeping_gate"},
    {"text": "Security guard phone var video baghat basla hota visitors kade laksha navhte complaint note kara.", "category": "SECURITY", "urgency": "MEDIUM", "language": "mr", "incident_family": "guard_sleeping_gate"},

    # Family 3: cctv_camera_offline
    {"text": "Tower 7 lobby CCTV camera feed is completely black on security monitor, blind spot created.", "category": "SECURITY", "urgency": "HIGH", "language": "en", "incident_family": "cctv_camera_offline"},
    {"text": "Basement 2 parking camera is hanging by its wire loose and misaligned from ceiling.", "category": "SECURITY", "urgency": "MEDIUM", "language": "en", "incident_family": "cctv_camera_offline"},
    {"text": "Main perimeter wall CCTV infrared night vision LED is defective causing unmonitored dark zone.", "category": "SECURITY", "urgency": "HIGH", "language": "en", "incident_family": "cctv_camera_offline"},
    {"text": "टावर 7 की लॉबी का सीसीटीवी कैमरा बंद पड़ा है स्क्रीन पर कोई फुटेज नहीं आ रही है।", "category": "SECURITY", "urgency": "HIGH", "language": "hi", "incident_family": "cctv_camera_offline"},
    {"text": "बेसमेंट का कैमरा तार से लटक रहा है और उसकी दिशा गलत हो गई है तुरंत ठीक करवाएं।", "category": "SECURITY", "urgency": "MEDIUM", "language": "hi", "incident_family": "cctv_camera_offline"},
    {"text": "Boundary wall ka CCTV camera offline hai security desk monitor pe no signal aa raha.", "category": "SECURITY", "urgency": "HIGH", "language": "hi", "incident_family": "cctv_camera_offline"},
    {"text": "टावर ७ च्या प्रवेशद्वारावरील सीसीटीव्ही कॅमेरा बंद पडला असून सुरक्षा कक्षात डिस्प्ले येत नाहीये.", "category": "SECURITY", "urgency": "HIGH", "language": "mr", "incident_family": "cctv_camera_offline"},
    {"text": "तळघरातील सीसीटीव्ही कॅमेऱ्याची दिशा बदलली असून वायर लटकत आहे दुरुस्ती करावी.", "category": "SECURITY", "urgency": "MEDIUM", "language": "mr", "incident_family": "cctv_camera_offline"},
    {"text": "Main gate CCTV camera offline ahe footage record hot nahi security technician pathva.", "category": "SECURITY", "urgency": "HIGH", "language": "mr", "incident_family": "cctv_camera_offline"},

    # Family 4: intercom_system_down
    {"text": "Flat intercom audio is crackling loudly and security gate cannot connect for visitor authorization.", "category": "SECURITY", "urgency": "MEDIUM", "language": "en", "incident_family": "intercom_system_down"},
    {"text": "Intercom handset has no dial tone, gate guards unable to confirm visitor entry.", "category": "SECURITY", "urgency": "MEDIUM", "language": "en", "incident_family": "intercom_system_down"},
    {"text": "Intercom buzzer rings continuously even when handset is on hook.", "category": "SECURITY", "urgency": "LOW", "language": "en", "incident_family": "intercom_system_down"},
    {"text": "फ्लैट का इंटरकॉम खराब है, गेट से कोई आवाज सुनाई नहीं देती और विजिटर खड़े रहते हैं।", "category": "SECURITY", "urgency": "MEDIUM", "language": "hi", "incident_family": "intercom_system_down"},
    {"text": "इंटरकॉम में डायल टोन नहीं आ रहा है, सुरक्षा गार्ड से संपर्क नहीं हो पा रहा।", "category": "SECURITY", "urgency": "MEDIUM", "language": "hi", "incident_family": "intercom_system_down"},
    {"text": "Intercom handset dead hai gate se visitor call connect nahi ho raha check karwao.", "category": "SECURITY", "urgency": "LOW", "language": "hi", "incident_family": "intercom_system_down"},
    {"text": "फ्लॅटमधील इंटरकॉम बंद पडल्यामुळे मुख्य प्रवेशद्वारावरून सुरक्षारक्षकांचे फोन येत नाहीत.", "category": "SECURITY", "urgency": "MEDIUM", "language": "mr", "incident_family": "intercom_system_down"},
    {"text": "इंटरकॉममध्ये प्रचंड खरखर आवाज येत असून संवाद साधणे अशक्य झाले आहे.", "category": "SECURITY", "urgency": "MEDIUM", "language": "mr", "incident_family": "intercom_system_down"},
    {"text": "Intercom chi wire loose zali ahe gate varun visitor approval sathi ring yet nahi.", "category": "SECURITY", "urgency": "LOW", "language": "mr", "incident_family": "intercom_system_down"},

    # Family 5: boom_barrier_damaged
    {"text": "Vehicle exit boom barrier arm is bent and stuck in halfway raised position causing vehicle delays.", "category": "SECURITY", "urgency": "MEDIUM", "language": "en", "incident_family": "boom_barrier_damaged"},
    {"text": "RFID tag scanner at entry boom barrier taking over 30 seconds per car causing traffic jam.", "category": "SECURITY", "urgency": "LOW", "language": "en", "incident_family": "boom_barrier_damaged"},
    {"text": "Boom barrier reflective warning stickers peeled off and safety rubber strip missing.", "category": "SECURITY", "urgency": "LOW", "language": "en", "incident_family": "boom_barrier_damaged"},
    {"text": "गेट का बूम बैरियर आधा टूटकर अटक गया है और गाड़ियों की लंबी कतार लग गई है।", "category": "SECURITY", "urgency": "MEDIUM", "language": "hi", "incident_family": "boom_barrier_damaged"},
    {"text": "आरएफआईडी स्कैनर काम नहीं कर रहा और बैरियर अपने आप नहीं खुल रहा है।", "category": "SECURITY", "urgency": "LOW", "language": "hi", "incident_family": "boom_barrier_damaged"},
    {"text": "Exit gate boom barrier crash hokar tut gaya hai entrance blocked ho gaya hai emergency!", "category": "SECURITY", "urgency": "CRITICAL", "language": "hi", "incident_family": "boom_barrier_damaged"},
    {"text": "वाहनांच्या मुख्य प्रवेशद्वारावरील बूम बॅरिअर मोडून पडले असून गेटवर वाहनांचा मार्ग पूर्णपणे ठप्प झाला आहे!", "category": "SECURITY", "urgency": "CRITICAL", "language": "mr", "incident_family": "boom_barrier_damaged"},
    {"text": "फाटकावरील फास्टॅग/आरएफआयडी स्कॅनर अत्यंत धीमे चालत असल्याने वाहतूक कोंडी होत आहे.", "category": "SECURITY", "urgency": "LOW", "language": "mr", "incident_family": "boom_barrier_damaged"},
    {"text": "Boom barrier sensor read karat nahi achanak barrier gaadi var padla ahe emergency repair kara!", "category": "SECURITY", "urgency": "CRITICAL", "language": "mr", "incident_family": "boom_barrier_damaged"},

    # =========================================================================
    # COMMON_AREA (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: children_park_swing_broken
    {"text": "Children park big swing iron chain snapped while toddler was swinging, child suffered bruising and heavy steel link exposed!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "en", "incident_family": "children_park_swing_broken"},
    {"text": "Toddler slide has cracked sharp plastic edge that cut a child's leg, urgent cordoning off needed!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "en", "incident_family": "children_park_swing_broken"},
    {"text": "See-saw pivot joint has lost its retaining bolt, wobbling noticeably when kids play.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "en", "incident_family": "children_park_swing_broken"},
    {"text": "बच्चों के पार्क का झूला टूट गया है और लोहे की नुकीली पत्ती बाहर निकली है तुरंत बंद कराएं बड़ा हादसा हो सकता है!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "hi", "incident_family": "children_park_swing_broken"},
    {"text": "फिसलपट्टी की सीढ़ी टूटी हुई है और बच्चे गिर सकते हैं मरम्मत करवाएं।", "category": "COMMON_AREA", "urgency": "HIGH", "language": "hi", "incident_family": "children_park_swing_broken"},
    {"text": "Children playground swing ki chain toot gayi hai dangerous hai bacho ko chot lag sakti hai jaldi repair karo.", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "hi", "incident_family": "children_park_swing_broken"},
    {"text": "लहान मुलांच्या बागेतील झोपाळ्याची लोखंडी साखळी तुटली असून टोकेरी भाग उघडा पडला आहे मोठा अपघात होऊ शकतो तातडीने दुरुस्त करा!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "mr", "incident_family": "children_park_swing_broken"},
    {"text": "घसरगुंडीच्या पायऱ्या सैल झाल्या असून लहान मुलांना खेळताना तोल जाण्याची भीती आहे.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "mr", "incident_family": "children_park_swing_broken"},
    {"text": "Playground swing chain tutli ahe kids sathi dangerous ahe park equipment repair technician pathva.", "category": "COMMON_AREA", "urgency": "HIGH", "language": "mr", "incident_family": "children_park_swing_broken"},

    # Family 2: swimming_pool_dirty
    {"text": "Live underwater pool light detached with exposed 230V live wire submerged in pool water extreme electrocution hazard!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "en", "incident_family": "swimming_pool_dirty"},
    {"text": "Pool filtration pump has been shut down for 3 days and dead insects floating on surface.", "category": "COMMON_AREA", "urgency": "HIGH", "language": "en", "incident_family": "swimming_pool_dirty"},
    {"text": "Chlorine smell in pool area is overpoweringly noxious causing eye burning and coughing.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "en", "incident_family": "swimming_pool_dirty"},
    {"text": "स्विमिंग पूल में अंडरवाटर बिजली की नंगी तार पानी में डूबी है करंट लगने का भयानक खतरा है!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "hi", "incident_family": "swimming_pool_dirty"},
    {"text": "स्विमिंग पूल का पानी हरा हो गया है और नीचे काई जम गई है, बच्चों की स्किन में रैशेज हो रहे हैं।", "category": "COMMON_AREA", "urgency": "HIGH", "language": "hi", "incident_family": "swimming_pool_dirty"},
    {"text": "Swimming pool ka paani bohot dirty aur green ho gaya hai chlorine treatment aur filtration chahiye.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "hi", "incident_family": "swimming_pool_dirty"},
    {"text": "जलतरण तलावातील अंडरवॉटर दिव्याची वायर उघडी पडून पाण्यात विजेचा प्रवाह उतरला आहे जीवघेणा धोका आहे!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "mr", "incident_family": "swimming_pool_dirty"},
    {"text": "स्विमिंग पूलचा फिल्टर पंप बंद असून पाण्यावर अस्वच्छता पसरली आहे स्वच्छता करावी.", "category": "COMMON_AREA", "urgency": "HIGH", "language": "mr", "incident_family": "swimming_pool_dirty"},
    {"text": "Pool che paani khup ghaan zala ahe green algae ahe filtration system chalu kara.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "mr", "incident_family": "swimming_pool_dirty"},

    # Family 3: gym_equipment_broken
    {"text": "Main cardio treadmill belt slips severely at speeds above 6 kmph throwing users off balance.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "en", "incident_family": "gym_equipment_broken"},
    {"text": "Cable crossover machine heavy cast iron weight stack guide rod sheared off falling dangerously!", "category": "COMMON_AREA", "urgency": "CRITICAL", "language": "en", "incident_family": "gym_equipment_broken"},
    {"text": "Adjustable bench pin is missing preventing angle locking mechanism.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "gym_equipment_broken"},
    {"text": "जिम की ट्रेडमिल का बेल्ट चलते-चलते स्लिप हो रहा है कोई भी गिरकर घायल हो सकता है।", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "hi", "incident_family": "gym_equipment_broken"},
    {"text": "डंबल रैक का स्टैंड टेढ़ा हो गया है और वजन फर्श पर गिर रहे हैं।", "category": "COMMON_AREA", "urgency": "LOW", "language": "hi", "incident_family": "gym_equipment_broken"},
    {"text": "Clubhouse gym ka cross trainer machine jam ho gaya hai noise kar raha hai service technician bhejo.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "hi", "incident_family": "gym_equipment_broken"},
    {"text": "सोसायटीच्या व्यायामशाळेतील ट्रेडमिलचा बेल्ट अचानक अडकतो आणि कसरत करताना तोल जातो.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "mr", "incident_family": "gym_equipment_broken"},
    {"text": "जिममधील डंबेलचे स्टँड तुटले असून वजने खाली पडत आहेत दुरुस्ती करणे आवश्यक आहे.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "gym_equipment_broken"},
    {"text": "Gym machine chi wire fray zali ahe servicing karavi lagel gym equipment repair required.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "gym_equipment_broken"},

    # Family 4: clubhouse_ac_leaking
    {"text": "Clubhouse party hall split AC is leaking continuous water stream over the wooden dance flooring.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "en", "incident_family": "clubhouse_ac_leaking"},
    {"text": "Clubhouse indoor badminton court AC is not cooling during booked tournament slots.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "clubhouse_ac_leaking"},
    {"text": "Society office air conditioner outdoor condenser unit making rattling fan vibration.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "clubhouse_ac_leaking"},
    {"text": "क्लबहाउस के एसी से बहुत पानी टपक रहा है और नीचे की लकड़ी का फर्श फूल कर खराब हो रहा है।", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "hi", "incident_family": "clubhouse_ac_leaking"},
    {"text": "कम्युनिटी हॉल का एसी कूलिंग नहीं कर रहा है सिर्फ हवा फेंक रहा है गैस चेक कराएं।", "category": "COMMON_AREA", "urgency": "LOW", "language": "hi", "incident_family": "clubhouse_ac_leaking"},
    {"text": "Clubhouse AC water drop kar raha hai wooden floor par slippery ho raha hai repair karwao.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "hi", "incident_family": "clubhouse_ac_leaking"},
    {"text": "क्लबहाऊसमधील वातानुकूलन यंत्रातून (एसी) सतत पाणी गळत असून लाकडी मजला खराब होत आहे.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "mr", "incident_family": "clubhouse_ac_leaking"},
    {"text": "सोसायटीच्या सभागृहातील एसी थंड हवा देत नसून गॅस संपला असावा सर्व्हिसिंग करावी.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "clubhouse_ac_leaking"},
    {"text": "Clubhouse hall AC leak hot ahe paani floor var saachle ahe AC repair technician pathva.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "clubhouse_ac_leaking"},

    # Family 5: badminton_court_net_torn
    {"text": "Indoor badminton court center net is torn from tension cable and sagging to the ground.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "badminton_court_net_torn"},
    {"text": "Tennis court perimeter fence net has huge gaping holes allowing balls onto internal road.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "badminton_court_net_torn"},
    {"text": "Table tennis table corner edge veneer chipped off during tournament play.", "category": "COMMON_AREA", "urgency": "LOW", "language": "en", "incident_family": "badminton_court_net_torn"},
    {"text": "बैडमिंटन कोर्ट की नेट बीच से फट गई है और जमीन पर लटक रही है नई नेट लगवाएं।", "category": "COMMON_AREA", "urgency": "LOW", "language": "hi", "incident_family": "badminton_court_net_torn"},
    {"text": "टेनिस कोर्ट की जाली फटी हुई है और गेंदें बार-बार सड़क पर जा रही हैं।", "category": "COMMON_AREA", "urgency": "LOW", "language": "hi", "incident_family": "badminton_court_net_torn"},
    {"text": "Badminton court ki net phati hui hai khelne me problem aa rahi hai replace it.", "category": "COMMON_AREA", "urgency": "LOW", "language": "hi", "incident_family": "badminton_court_net_torn"},
    {"text": "बॅडमिंटन कोर्टची जाळी मध्यभागी फाटली असून ती खाली लोंबकळत आहे नवीन जाळी बसवावी.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "badminton_court_net_torn"},
    {"text": "टेबल टेनिस टेबलचा कोपरा तुटला असून खेळताना चेंडू उसळत नाही दुरुस्त करा.", "category": "COMMON_AREA", "urgency": "LOW", "language": "mr", "incident_family": "badminton_court_net_torn"},
    {"text": "Sports arena net phatli ahe badminton play karta yet nahi navin net basva.", "category": "COMMON_AREA", "urgency": "MEDIUM", "language": "mr", "incident_family": "badminton_court_net_torn"},

    # =========================================================================
    # GENERAL (45 complaints across 5 incident families)
    # Target: 10 LOW, 11 MEDIUM, 12 HIGH, 12 CRITICAL
    # =========================================================================
    # Family 1: late_night_loud_music
    {"text": "Flat 1204 playing deafening bass amplified party music continuously at 2:30 AM on weekday despite guard visits!", "category": "GENERAL", "urgency": "CRITICAL", "language": "en", "incident_family": "late_night_loud_music"},
    {"text": "Brawl and screaming physical altercation in 9th floor corridor at 1:00 AM terrifying elderly neighbors!", "category": "GENERAL", "urgency": "CRITICAL", "language": "en", "incident_family": "late_night_loud_music"},
    {"text": "Violent banging on communal doors and unruly loud shouting late at night in Tower 8.", "category": "GENERAL", "urgency": "HIGH", "language": "en", "incident_family": "late_night_loud_music"},
    {"text": "फ्लैट 1204 में रात के 2:30 बजे बेहद तेज आवाज में डीजे म्यूजिक बज रहा है, मना करने पर झगड़ा कर रहे हैं तुरंत पुलिस या सुरक्षा भेजें!", "category": "GENERAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "late_night_loud_music"},
    {"text": "रात को लॉबी में कुछ लोग चिल्ला रहे हैं और दरवाजा पीट रहे हैं, सोसायटी की शांति भंग हो रही है।", "category": "GENERAL", "urgency": "HIGH", "language": "hi", "incident_family": "late_night_loud_music"},
    {"text": "Raat ko 2 baje flat 802 me high volume sound baj raha hai patients so nahi pa rahe action lo.", "category": "GENERAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "late_night_loud_music"},
    {"text": "शेजारच्या फ्लॅटमध्ये मध्यरात्री अडीच वाजता अतिशय मोठ्या आवाजात संगीत सुरू असून विचारणा केल्यावर शिवीगाळ करत आहेत तातडीने हस्तक्षेप करा!", "category": "GENERAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "late_night_loud_music"},
    {"text": "मध्यरात्री कॉरिडॉरमध्ये काही लोकांचे मोठे भांडण सुरू असून आरडाओरड होत आहे शांतता धोक्यात आली आहे.", "category": "GENERAL", "urgency": "HIGH", "language": "mr", "incident_family": "late_night_loud_music"},
    {"text": "Raatri 2 vajta loud DJ music chalu ahe flat 504 madhe complaint karun pan band karat nahit urgent guard pathva.", "category": "GENERAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "late_night_loud_music"},

    # Family 2: visitor_parking_encroachment
    {"text": "Unauthorized SUV illegally parked in my allocated covered parking bay B-104 refusing to move.", "category": "GENERAL", "urgency": "HIGH", "language": "en", "incident_family": "visitor_parking_encroachment"},
    {"text": "Commercial delivery truck completely blocking emergency fire tender driveway and ambulance access!", "category": "GENERAL", "urgency": "CRITICAL", "language": "en", "incident_family": "visitor_parking_encroachment"},
    {"text": "Visitor vehicle parked over two reserved resident slots without displaying guest pass.", "category": "GENERAL", "urgency": "MEDIUM", "language": "en", "incident_family": "visitor_parking_encroachment"},
    {"text": "मेरी अलॉटेड पार्किंग में किसी अज्ञात व्यक्ति ने अपनी गाड़ी लगा दी है और फोन नहीं उठा रहा तुरंत हटवाएं।", "category": "GENERAL", "urgency": "HIGH", "language": "hi", "incident_family": "visitor_parking_encroachment"},
    {"text": "फायर ब्रिगेड और एम्बुलेंस का मुख्य रास्ता अज्ञात भारी वाहन ने पूरी तरह ब्लॉक कर दिया है जानलेवा खतरा है!", "category": "GENERAL", "urgency": "CRITICAL", "language": "hi", "incident_family": "visitor_parking_encroachment"},
    {"text": "Mera parking slot B-45 kisi aur car ne block kar diya hai security guard ko bolkar car tow karwao.", "category": "GENERAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "visitor_parking_encroachment"},
    {"text": "माझ्या हक्काच्या पार्किंग जागेत अज्ञात व्यक्तीने गाडी उभी केली असून गाडी काढण्यास नकार देत आहे तातडीने सुरक्षा रक्षक पाठवा.", "category": "GENERAL", "urgency": "HIGH", "language": "mr", "incident_family": "visitor_parking_encroachment"},
    {"text": "अग्निशामक दलाचा आपत्कालीन मार्ग अज्ञात वाहनाने अडवला असून रुग्णवाहिका येण्यास मार्ग नाही त्वरित वाहन हटवा!", "category": "GENERAL", "urgency": "CRITICAL", "language": "mr", "incident_family": "visitor_parking_encroachment"},
    {"text": "Majhya parking bay madhe dusri gadi park keli ahe number plate track kara gadi kadhayla sanga.", "category": "GENERAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "visitor_parking_encroachment"},

    # Family 3: maintenance_receipt_delay
    {"text": "Paid monthly maintenance fee of Rs 7475 via UPI last Monday but payment receipt is not reflected in account portal.", "category": "GENERAL", "urgency": "MEDIUM", "language": "en", "incident_family": "maintenance_receipt_delay"},
    {"text": "Discrepancy in previous quarter ledger statement showing incorrect penalty charge of Rs 250.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "maintenance_receipt_delay"},
    {"text": "Annual audited maintenance statement requested two weeks ago has not been emailed by society office.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "maintenance_receipt_delay"},
    {"text": "मैंने पिछले हफ्ते मेंटेनेंस का 7475 रुपये यूपीआई से भुगतान किया था लेकिन पोर्टल पर अभी भी पेंडिंग दिख रहा है रसीद दें।", "category": "GENERAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "maintenance_receipt_delay"},
    {"text": "मेंटेनेंस बिल में 200 रुपये का गलत लेट फाइन लगा दिया गया है कृपया लेजर में सुधार करें।", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "maintenance_receipt_delay"},
    {"text": "Maintenance bill payment receipt portal par update nahi hui bank se paise cut ho gaye hai update ledger.", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "maintenance_receipt_delay"},
    {"text": "गेल्या आठवड्यात मेंटेनन्स बिलाचे ७४७५ रुपये भरले असून अद्याप पावती जनरेट झालेली नाही खात्यांची पडताळणी करावी.", "category": "GENERAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "maintenance_receipt_delay"},
    {"text": "सोसायटीच्या खात्यावर दंड म्हणून चुकीची रक्कम लावण्यात आली आहे लेजर दुरुस्त करून मिळावे.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "maintenance_receipt_delay"},
    {"text": "Maintenance receipt ajun bhetli nahi bank txn id share kela ahe accounts team la confirm karayla sanga.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "maintenance_receipt_delay"},

    # Family 4: pet_policy_violation
    {"text": "Large aggressive unleashed dog roaming corridor without muzzle lunging at passing school children.", "category": "GENERAL", "urgency": "HIGH", "language": "en", "incident_family": "pet_policy_violation"},
    {"text": "Resident allowing pet dog to bark incessantly on balcony for 6 hours straight during working hours.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "pet_policy_violation"},
    {"text": "Pet owner walking dog in designated children play sandbox violating society bylaws.", "category": "GENERAL", "urgency": "MEDIUM", "language": "en", "incident_family": "pet_policy_violation"},
    {"text": "पड़ोसी अपने बड़े कुत्ते को बिना पट्टे के लॉबी में खुला छोड़ देते हैं जिससे बच्चों में डर बैठ गया है।", "category": "GENERAL", "urgency": "HIGH", "language": "hi", "incident_family": "pet_policy_violation"},
    {"text": "बालकनी में कुत्ता पिछले 4 घंटे से लगातार भौंक रहा है वर्क फ्रॉम होम में भारी परेशानी हो रही है।", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "pet_policy_violation"},
    {"text": "Unleashed pet dog corridor me ghum raha hai bina lease ke bacho ko darr lag raha hai notice bhejo owner ko.", "category": "GENERAL", "urgency": "MEDIUM", "language": "hi", "incident_family": "pet_policy_violation"},
    {"text": "शेजारी आपल्या पाळीव कुत्र्याला पट्ट्याशिवाय कॉरिडॉरमध्ये मोकळे सोडत असल्याने लहान मुलांमध्ये घबराट पसरली आहे.", "category": "GENERAL", "urgency": "HIGH", "language": "mr", "incident_family": "pet_policy_violation"},
    {"text": "सकाळपासून बाल्कनीमध्ये कुत्रा भुंकत असल्यामुळे आजारी व्यक्तींना शांत झोप घेता येत नाही.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "pet_policy_violation"},
    {"text": "Pet dog leash shivay lobby madhe firavtat society rules follow karayla owner la warning dya.", "category": "GENERAL", "urgency": "MEDIUM", "language": "mr", "incident_family": "pet_policy_violation"},

    # Family 5: renovation_noc_request
    {"text": "Flat renovation NOC application submitted 10 days ago awaiting society manager approval stamp.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "renovation_noc_request"},
    {"text": "Interior carpenter work requested permission for drilling between 10 AM and 1 PM tomorrow.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "renovation_noc_request"},
    {"text": "Requesting security gate pass clearance for modular kitchen material delivery truck.", "category": "GENERAL", "urgency": "LOW", "language": "en", "incident_family": "renovation_noc_request"},
    {"text": "फ्लैट रिनोवेशन की एनओसी के लिए 10 दिन पहले आवेदन किया था, अभी तक अनुमति पत्र नहीं मिला।", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "renovation_noc_request"},
    {"text": "कल सुबह किचन के फर्नीचर काम के लिए बढ़ई का गेट पास स्वीकृत किया जाए।", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "renovation_noc_request"},
    {"text": "Renovation NOC request form submit kiya tha status update karke approval issue karo.", "category": "GENERAL", "urgency": "LOW", "language": "hi", "incident_family": "renovation_noc_request"},
    {"text": "फ्लॅटच्या नूतनीकरणासाठी ना-हरकत प्रमाणपत्राचा (NOC) अर्ज सादर केला असून अद्याप स्वाक्षरी मिळालेली नाही.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "renovation_noc_request"},
    {"text": "घरातील सुतारकामासाठी उद्या सकाळी साहित्याची गाडी आणण्यास सुरक्षारक्षकांकडे परवानगी द्यावी.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "renovation_noc_request"},
    {"text": "Flat renovation permission letter approve karun dya carpenter team ready ahe NOC pass dya.", "category": "GENERAL", "urgency": "LOW", "language": "mr", "incident_family": "renovation_noc_request"},
]

df = pd.DataFrame(complaints_data)
print(f"Total rows: {len(df)}")
print("\nCategories distribution:")
print(df["category"].value_counts())
print("\nUrgencies distribution:")
print(df["urgency"].value_counts())
print("\nLanguages distribution:")
print(df["language"].value_counts())
print(f"\nUnique incident families: {df['incident_family'].nunique()}")

# Ensure target directory exists
os.makedirs("backend/app/ml/data", exist_ok=True)
csv_path = "backend/app/ml/data/complaints_v1.csv"
df.to_csv(csv_path, index=False, encoding="utf-8")
print(f"\nSuccessfully wrote {csv_path}")
