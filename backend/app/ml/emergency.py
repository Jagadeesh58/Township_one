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
    matched_text: str | None
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
    r"\b(?:mock\s+drill|fire\s+drill|drill|practice\s+run|test\s+alarm|scheduled\s+drill)\b",
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
    Applies conservative negation: when ambiguous or uncertain, escalates to True.
    """
    if not text or not text.strip():
        return {
            "is_emergency": False,
            "trigger": None,
            "matched_text": None,
            "language": "en",
        }

    lang = detect_language(text)
    lowered = text.lower()

    matched_trigger = None
    matched_snippet = None

    # Iterate through triggers in priority sequence
    for trigger, patterns in EMERGENCY_PATTERNS.items():
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                matched_trigger = trigger
                matched_snippet = match.group(0)
                break
        if matched_trigger:
            break

    # If no life-safety pattern matched, return non-emergency
    if not matched_trigger:
        return {
            "is_emergency": False,
            "trigger": None,
            "matched_text": None,
            "language": lang,
        }

    # Life safety trigger matched: inspect for conservative negation / drills
    has_drill = any(bool(re.search(p, lowered, re.IGNORECASE)) for p in DRILL_PATTERNS)
    has_override = any(bool(re.search(p, lowered, re.IGNORECASE)) for p in OVERRIDE_PATTERNS)
    has_benign_negation = any(bool(re.search(p, lowered, re.IGNORECASE)) for p in BENIGN_NEGATIONS)

    # If an override or conflict is present (e.g., "no fire drill today, real fire"), always escalate
    if has_override:
        return {
            "is_emergency": True,
            "trigger": matched_trigger,
            "matched_text": matched_snippet,
            "language": lang,
        }

    # Routine drills without real emergency cues are suppressed
    if has_drill and not has_override:
        # Check if the text actually says "no fire drill" (drill was negated)
        if re.search(r"\bno\s+fire\s+drill\b|\bnot\s+a\s+drill\b", lowered):
            # The drill is negated, so the fire is real - escalate conservatively
            return {
                "is_emergency": True,
                "trigger": matched_trigger,
                "matched_text": matched_snippet,
                "language": lang,
            }
        return {
            "is_emergency": False,
            "trigger": None,
            "matched_text": None,
            "language": lang,
        }

    # Benign negation check (e.g. "routine check, no smoke")
    if has_benign_negation and not has_override:
        return {
            "is_emergency": False,
            "trigger": None,
            "matched_text": None,
            "language": lang,
        }

    # Conservative fail-safe: default to escalation for all matched hazards
    return {
        "is_emergency": True,
        "trigger": matched_trigger,
        "matched_text": matched_snippet,
        "language": lang,
    }
