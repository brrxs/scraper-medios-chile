import re
import unicodedata
from datetime import date, datetime
from typing import Optional

MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def parse_date(text: str) -> Optional[date]:
    """
    Parses a date string into a date object. Handles:
      - ISO 8601: "2025-05-15" or "2025-05-15T12:30:00Z"
      - Spanish: "15 de enero de 2025" or "enero 15, 2025"
      - Numeric: "15/01/2025" or "15-01-2025"
    Returns None if unparseable.
    """
    if not text:
        return None
    text = text.strip()

    # ISO 8601 (with optional time)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    lower = text.lower()

    # "15 de enero de 2025"
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", lower)
    if m and m.group(2) in MONTHS_ES:
        try:
            return date(int(m.group(3)), MONTHS_ES[m.group(2)], int(m.group(1)))
        except ValueError:
            pass

    # "20 mayo de 2026" or "Miércoles 20 mayo de 2026 | 15:03" (biobio style)
    # Strip leading weekday word and trailing time
    stripped = re.sub(r"^\w+\s+", "", lower)
    stripped = stripped.split("|")[0].strip()
    m = re.search(r"(\d{1,2})\s+(\w+)\s+de\s+(\d{4})", stripped)
    if m and m.group(2) in MONTHS_ES:
        try:
            return date(int(m.group(3)), MONTHS_ES[m.group(2)], int(m.group(1)))
        except ValueError:
            pass

    # "enero 15, 2025" or "enero 15 2025"
    m = re.search(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", lower)
    if m and m.group(1) in MONTHS_ES:
        try:
            return date(int(m.group(3)), MONTHS_ES[m.group(1)], int(m.group(2)))
        except ValueError:
            pass

    # "15/01/2025" or "15-01-2025"
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    return None


def normalize(text: str) -> str:
    """Lowercase + strip accents for accent-insensitive matching."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def phrase_matches(text: str, phrase: str) -> bool:
    """True if every word of phrase appears in text (accent-insensitive, AND logic)."""
    haystack = normalize(text)
    return all(normalize(w) in haystack for w in phrase.split())


def any_phrase_matches(text: str, phrases: list[str]) -> bool:
    """True if at least one phrase matches text. Empty phrases list returns True (no filter)."""
    if not phrases:
        return True
    return any(phrase_matches(text, p) for p in phrases)


def clean_text(text: str) -> str:
    """Strip excess whitespace, newlines, and common junk prefixes."""
    text = re.sub(r"dfp:", " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()
