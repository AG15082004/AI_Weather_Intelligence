"""Tamil Nadu district entity extraction with canonical normalization and alias support.

Covers all 38 official districts of Tamil Nadu.
Ensures unambiguous, exact word-boundary matching and eliminates accidental substring conflicts.
"""

import re
from typing import List, Optional, Set, Tuple

# All 38 canonical Tamil Nadu districts
ALL_TN_DISTRICTS: List[str] = [
    "Ariyalur",
    "Chengalpattu",
    "Chennai",
    "Coimbatore",
    "Cuddalore",
    "Dharmapuri",
    "Dindigul",
    "Erode",
    "Kallakurichi",
    "Kanchipuram",
    "Kanyakumari",
    "Karur",
    "Krishnagiri",
    "Madurai",
    "Mayiladuthurai",
    "Nagapattinam",
    "Namakkal",
    "Nilgiris",
    "Perambalur",
    "Pudukkottai",
    "Ramanathapuram",
    "Ranipet",
    "Salem",
    "Sivaganga",
    "Tenkasi",
    "Thanjavur",
    "Theni",
    "Thoothukudi",
    "Tiruchirappalli",
    "Tirunelveli",
    "Tirupathur",
    "Tiruppur",
    "Tiruvallur",
    "Tiruvannamalai",
    "Tiruvarur",
    "Vellore",
    "Viluppuram",
    "Virudhunagar",
]

# Canonical normalization map: maps lowercased alias/variation to official district name
DISTRICT_ALIAS_MAP = {
    # Direct lowercase mappings
    **{d.lower(): d for d in ALL_TN_DISTRICTS},
    
    # Common variations and historic names
    "madras": "Chennai",
    "chengalpet": "Chengalpattu",
    "chengalpettu": "Chengalpattu",
    "kovai": "Coimbatore",
    "kancheepuram": "Kanchipuram",
    "conjeevaram": "Kanchipuram",
    "kanniyakumari": "Kanyakumari",
    "cape comorin": "Kanyakumari",
    "comorin": "Kanyakumari",
    "mayuram": "Mayiladuthurai",
    "mayavaram": "Mayiladuthurai",
    "nagai": "Nagapattinam",
    "the nilgiris": "Nilgiris",
    "ooty": "Nilgiris",
    "udhagamandalam": "Nilgiris",
    "ramnad": "Ramanathapuram",
    "sivagangai": "Sivaganga",
    "tanjore": "Thanjavur",
    "tuticorin": "Thoothukudi",
    "thoothukudi port": "Thoothukudi",
    "trichy": "Tiruchirappalli",
    "tiruchi": "Tiruchirappalli",
    "nellai": "Tirunelveli",
    "tirunelvely": "Tirunelveli",
    "tirupattur": "Tirupathur",
    "tiruppattur": "Tirupathur",
    "tirupur": "Tiruppur",
    "thiruvallur": "Tiruvallur",
    "thiruvannamalai": "Tiruvannamalai",
    "thiruvarur": "Tiruvarur",
    "villupuram": "Viluppuram",
    "virudhunagar town": "Virudhunagar",
}


def extract_districts(text: str) -> List[str]:
    """Extract all mentioned Tamil Nadu districts in the text in order of appearance.
    
    Uses word boundaries to prevent partial word matches (e.g. 'then' matching 'Theni').
    """
    if not text:
        return []

    text_lower = text.lower()
    found: List[Tuple[int, str]] = []
    already_matched_canonical: Set[str] = set()

    # Sort aliases by length descending so multi-word aliases (e.g. 'cape comorin') match before single words
    sorted_aliases = sorted(DISTRICT_ALIAS_MAP.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        canonical = DISTRICT_ALIAS_MAP[alias]
        if canonical in already_matched_canonical:
            continue

        # Regex with word boundary check
        pattern = r"\b" + re.escape(alias) + r"\b"
        match = re.search(pattern, text_lower)
        if match:
            found.append((match.start(), canonical))
            already_matched_canonical.add(canonical)

    # Sort by position in the user sentence
    found.sort(key=lambda x: x[0])
    return [canonical for _, canonical in found]


def extract_single_district(text: str) -> Optional[str]:
    """Extract a single primary district from text, or None if none found."""
    districts = extract_districts(text)
    return districts[0] if districts else None

