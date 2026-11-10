"""
Township One - Emergency Safety Trigger Detection Service.

Provides deterministic, trilingual regex/keyword identification for life-safety hazards:
- Fire / flames
- Smoke
- Gas leaks
- Lift entrapments
- Electrical shock / active sparking

Supports English, Hindi (Devanagari and romanized transliteration), and Marathi
(Devanagari and romanized transliteration) with conservative negation handling.
"""

import re
from typing import TypedDict


class EmergencyResult(TypedDict):
    is_emergency: bool
    trigger: str | None
    hazard_type: str | None
    matched_text: str | None
    match_snippet: str | None
    language: str


# Canonical emergency triggers and regex patterns
EMERGENCY_PATTERNS = {
    "FIRE": [
        # English
        r"\b(?:fire|flames?|blaze|inferno|burning|on\s+fire|building\s+on\s+fire)\b",
        # Hindi Devanagari & romanized
        r"(?:आग\b|भीषण\s*आग|आग\s*लग[ीेा]|आग\s+की\s+लपटें?|आग\s+लगी\s+है)",
        r"\b(?:aag\s+lagi|aag\s+lag\s+gayi|aag\s+lagi\s+hai|bhadak\s+gayi|laptein|\baag\b)\b",
        # Marathi Devanagari & romanized
        r"(?:मोठी\s*आग|आग\s*लागली|आगीचा\s*भडका|आग\s+आहे|आगीत)",
        r"\b(?:aag\s+laagli|aag\s+lagli|aag\s+ahe|bhadka\s+udala)\b",
    ],
    "SMOKE": [
        # English
        r"\b(?:smoke|thick\s+smoke|dense\s+smoke|black\s+smoke|heavy\s+smoke|suffocating\s+smoke|smoke\s+rising|smoke\s+coming)\b",
        # Hindi Devanagari & romanized
        r"(?:धुआं|धुंआ|काला\s*धुआं|काले\s*धुं?आं|तेज\s*धुआं|धुआं\s*निकल\s*रहा|धुएं\s*का\s*गुबार)",
        r"\b(?:dhua|dhuan|kaala\s+dhuan?|bhari\s+dhuan?|dhua\s+aa\s+raha|dhuan\s+nikal\s+raha)\b",
        # Marathi Devanagari & romanized
        r"(?:धूर\b|काळा\s*धूर|विषारी\s*धूर|धूर\s*येत\s*आहे|धुराचे\s*लोट|धूर\s*पसरला)",
        r"\b(?:dhur\b|kala\s+dhur|mottha\s+dhur|dhur\s+yet\s+ahe|dhur\s+pasarla)\b",
    ],
    "GAS_LEAK": [
        # English
        r"\b(?:gas\s+leak(?:age)?|cylinder\s+leak(?:age)?|lpg\s+leak(?:age)?|pungent\s+gas\s+smell|gas\s+cylinder\s+hissing|smell\s+of\s+gas)\b",
        # Hindi Devanagari & romanized
        r"(?:गैस\s*लीक|गैस\s*का\s*रिसाव|सिलेंडर\s*लीक|गैस\s*की\s*बदबू)",
        r"\b(?:gas\s+leak|cylinder\s+leak|gas\s+ka\s+risav|gas\s+smell)\b",
        # Marathi Devanagari & romanized
        r"(?:गॅस\s*गळती|गॅस\s*लीक|सिलिंडर\s*गळती|गॅसचा\s*वास)",
        r"\b(?:gas\s+galati|gas\s+galtee|gas\s+leak\s+hot\s+ahe|gascha\s+vaas)\b",
    ],
    "LIFT_TRAPPED": [
        # English
        r"\b(?:lift\s+stuck|elevator\s+stuck|trapped\s+in(?:side)?\s+(?:the\s+)?lift|trapped\s+in(?:side)?\s+(?:the\s+)?elevator|people\s+trapped\s+in\s+lift|lift\s+stopped\s+with\s+passengers)\b",
        r"\b(?:lift|elevator)\b.*?\b(?:stuck|trapped|stopped\s+with\s+passengers)\b",
        # Hindi Devanagari & romanized
        r"(?:लिफ्ट\s*में\s*फंसे|लिफ्ट\s*अटक\s*गई|लिफ्ट\s*अटकी|लिफ्ट\s*बंद\s*लोग\s*अंदर|लिफ्ट\s*में\s*लोग\s*बंद)",
        r"(?:लिफ्ट).*?(?:फंसे|अटक|अटकी)",
        r"\b(?:lift|elevator)\b.*?\b(?:atki|phasi|fasi|phansi|fas\s+gaye|band\s+hai\s+andar)\b",
        # Marathi Devanagari & romanized
        r"(?:लिफ्टमध्ये\s*अडकले|लिफ्ट\s*अडकली|लिफ्ट\s*बंद\s*पडून\s*प्रवासी\s*आत|लिफ्ट\s*आत\s*अडकले)",
        r"(?:लिफ्ट).*?(?:अडकली|अडकले)",
        r"\b(?:lift|elevator)\b.*?\b(?:adakli|adakle|band\s+ahe\s+lok\s+aat|adkun\s+padli)\b",
    ],
    "ELECTRIC_SHOCK_SPARKING": [
        # English
        r"\b(?:electric\s+shock|electrocution|active\s+sparking|heavy\s+sparks?|live\s+wire|switchboard\s+spark(?:ing)?|short\s+circuit\s+fire|sparking)\b",
        # Hindi Devanagari & romanized
        r"(?:बिजली\s*का\s*झटका|करंट\s*लग\s*रहा|करंट\s*लगा|तेज\s*चिंगारी|नंगी\s*तार|स्पार्किंग\s*हो\s*रही|करंट)",
        r"\b(?:current\s+lag\s+raha|current\s+laga|current\s+lag\s+gaya|bijli\s+ka\s+jhatka|chingari\s+nikal\s+rahi|sparking|live\s+wire)\b",
        # Marathi Devanagari & romanized
        r"(?:विजेचा\s*धक्का|करंट\s*बसला|मोठ्या\s*ठिणग्या|उघडी\s*विद्युत\s*तार|शॉर्ट\s*सर्किट|ठिणगी)",
        r"\b(?:vijecha\s+dhakka|current\s+basla|thingi\s+udali|thingi|sparking\s+hot\s+ahe|short\s+circuit)\b",
    ],
}

# Drill / routine indicators
DRILL_PATTERNS = [
    r"\b(?:mock\s+drill|fire\s+drill|drill|practice\s+run|test\s+alarm|scheduled\s+drill|fire\s+safety(?:\s+practice)?|safety\s+drill|evacuation\s+drill)\b",
    r"(?:मॉक\s*ड्रिल|फायर\s*ड्रिल|अभ्यास\s*दौरा)",
    r"\b(?:routine\s+drill|routine\s+check\s+no\s+smoke|no\s+fire\s+drill)\b",
]

# Explicit override indicators that cancel drill negation (escalate immediately)
OVERRIDE_PATTERNS = [
    r"\b(?:real\s+fire|actual\s+fire|not\s+a\s+drill|real\s+emergency|actual\s+emergency|genuine\s+fire)\b",
    r"\b(?:no\s+fire\s+drill\s+today[,\s]+real|not\s+drill|asli\s+aag|khari\s+aag|sachmuch\s+aag)\b",
    r"(?:खरी\s*आग|सत्य\s*आग|असली\s*आग|मॉक\s*नाही\s*खरी\s*आग)",
    r"\b(?:help|bachao|madat|urgent|trapped|victim|injured|hospital)\b",
]

# Non-emergency routine negation phrases
BENIGN_NEGATIONS = [
    r"\b(?:routine\s+drill[,\s]+no\s+smoke)\b",
    r"\b(?:no\s+smoke\b|no\s+fire\b|no\s+flames\b|no\s+leak\b)",
    r"(?:धूर\s*नाही|आग\s*नाही|धुआं\s*नहीं)",
]


def detect_language(text: str) -> str:
    """Identify language: en, hi, or mr based on script and vocabulary."""
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    lowered = text.lower()

    if has_devanagari:
        # Distinguish Marathi from Hindi in Devanagari
        marathi_markers = [
            "आहे",
            "नाही",
            "झाली",
            "झाला",
            "पडत",
            "अडकले",
            "अडकली",
            "गळती",
            "विजेचा",
            "धूर",
            "ठिणगी",
            "मध्ये",
            "होते",
            "करावे",
            "तपासा",
        ]
        if any(marker in text for marker in marathi_markers):
            return "mr"
        return "hi"

    # Latin romanized script detection
    marathi_roman = [
        "ahe",
        "ahet",
        "zala",
        "zali",
        "jhali",
        "adakle",
        "adakli",
        "dhur",
        "galati",
        "vijecha",
        "madhe",
        "majha",
        "majhya",
        "kela",
        "keli",
        "lavkar",
        "pathva",
        "basla",
    ]
    if any(re.search(rf"\b{word}\b", lowered) for word in marathi_roman):
        return "mr"

    hindi_roman = [
        "hai",
        "hain",
        "nahi",
        "gaya",
        "gayi",
        "phasi",
        "fase",
        "dhua",
        "dhuan",
        "karo",
        "bhejo",
        "jaldi",
        "bachao",
        "raha",
        "rahi",
        "hua",
        "hui",
        "laga",
        "chingari",
    ]
    if any(re.search(rf"\b{word}\b", lowered) for word in hindi_roman):
        return "hi"

    return "en"


def detect_emergency(text: str) -> EmergencyResult:
    """
    Deterministic safety trigger detector.

    Returns structured verdict with trigger name, matched snippet, and detected language.
    Applies clause-aware and context-sensitive negation: when ambiguous or uncertain, escalates to True.
    """
    if not text or not text.strip():
        return {
            "is_emergency": False,
            "trigger": None,
            "hazard_type": None,
            "matched_text": None,
            "match_snippet": None,
            "language": "en",
        }

    lang = detect_language(text)
    lowered = text.lower()

    # Check for explicit emergency overrides that defeat any drill suppression
    has_override = any(bool(re.search(p, lowered, re.IGNORECASE)) for p in OVERRIDE_PATTERNS)

    # Locate drill spans that are not themselves negated
    drill_spans: list[tuple[int, int]] = []
    if not has_override:
        for p in DRILL_PATTERNS:
            for m in re.finditer(p, text, re.IGNORECASE):
                span_text = text[max(0, m.start() - 15) : m.end()]
                if not re.search(r"\b(?:not|no|never)\s+(?:a\s+)?(?:fire\s+)?drill\b", span_text, re.IGNORECASE):
                    drill_spans.append((m.start(), m.end()))

    active_hazards: list[tuple[str, str]] = []

    # Iterate through triggers in priority sequence
    for trigger, patterns in EMERGENCY_PATTERNS.items():
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                m_start, m_end = m.start(), m.end()

                # 1. Skip if the hazard word is purely internal to an active drill phrase
                in_drill = any(d_start <= m_start and m_end <= d_end for d_start, d_end in drill_spans)
                if in_drill and not has_override:
                    continue

                # 2. Check localized prefix negation (e.g. 'no smoke', 'no fire', 'without leak')
                prefix_start = max(0, m_start - 35)
                punct_indices = [text.rfind(c, prefix_start, m_start) for c in (".", "?", "!", ";", "\n")]
                last_punct = max(punct_indices)
                if last_punct != -1:
                    prefix_start = last_punct + 1
                prefix = text[prefix_start:m_start]

                is_negated = bool(
                    re.search(r"\b(?:no|not|without|neither|nor)\s+(?:\w+\s+){0,3}$", prefix, re.IGNORECASE)
                )
                if not is_negated:
                    is_negated = bool(
                        re.search(r"(?:^|\s)(?:नाही|नाहीत|नाहीये|नहीं|न|काही\s*नाही)\s+(?:[^\s,;.?!]+\s+){0,2}$", prefix)
                    )

                # 3. Check localized suffix negation (e.g. Hindi/Marathi 'dhuan nahi', 'aag nahi')
                if not is_negated:
                    suffix_end = min(len(text), m_end + 30)
                    next_puncts = [
                        text.find(c, m_end, suffix_end)
                        for c in (".", "?", "!", ";", "\n")
                        if text.find(c, m_end, suffix_end) != -1
                    ]
                    next_punct = min(next_puncts, default=-1)
                    if next_punct != -1:
                        suffix_end = next_punct
                    suffix = text[m_end:suffix_end]
                    is_negated = bool(
                        re.search(
                            r"^\s*(?:hot\s+|ahe\s+|hai\s+|aahe\s+|hote\s+)?(?:नाही|नाहीत|नाहीये|नहीं|न|nahi|nahin|naahi)(?:\s|[.,;!?]|$)",
                            suffix,
                            re.IGNORECASE,
                        )
                    )

                if not is_negated or has_override:
                    active_hazards.append((trigger, m.group(0)))
                    break
        if active_hazards:
            break

    if active_hazards:
        trig, snip = active_hazards[0]
        return {
            "is_emergency": True,
            "trigger": trig,
            "hazard_type": trig,
            "matched_text": snip,
            "match_snippet": snip,
            "language": lang,
        }

    return {
        "is_emergency": False,
        "trigger": None,
        "hazard_type": None,
        "matched_text": None,
        "match_snippet": None,
        "language": lang,
    }
