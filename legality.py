"""Commander deck validation using Scryfall card data."""
from collections import Counter
from functools import lru_cache
import requests

HEADERS = {"User-Agent": "BudgetCommanderDeckBuilder/1.0", "Accept": "application/json"}
BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}

@lru_cache(maxsize=2048)
def lookup_card(name):
    """Fetch one exact card. None means validation could not be completed."""
    try:
        response = requests.get(
            "https://api.scryfall.com/cards/named",
            params={"exact": name}, headers=HEADERS, timeout=10
        )
        if response.status_code != 200:
            return None
        card = response.json()
        return {
            "name": card.get("name", name),
            "color_identity": card.get("color_identity", []),
            "legal": card.get("legalities", {}).get("commander") == "legal",
            "type_line": card.get("type_line", ""),
            "oracle_text": card.get("oracle_text", ""),
            "keywords": card.get("keywords", []),
            "layout": card.get("layout", ""),
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None

def validate_deck(commander_name, deck, basic_lands):
    """Return a conservative legality assessment; never claim legal if verification fails."""
    count = 1 + len(deck) + sum(basic_lands.values())
    issues = []
    warnings = []
    commander = lookup_card(commander_name) if commander_name else None
    if not commander:
        warnings.append("Commander information could not be verified with Scryfall.")
    else:
        if not commander["legal"]:
            issues.append(f"{commander_name} is not legal in Commander.")
        typ = commander["type_line"].lower()
        text = commander["oracle_text"].lower()
        if "legendary" not in typ or "creature" not in typ:
            if "can be your commander" not in text:
                issues.append(f"{commander_name} is not verified as an eligible commander.")
        if any(term in text for term in ("choose a background", "partner", "friends forever", "doctor's companion")):
            warnings.append("Partner/Background and other multi-commander rules are not supported by this single-commander checker.")

    if count != 100:
        warnings.append(f"Deck needs {100 - count} more cards." if count < 100 else f"Deck exceeds 100 cards by {count - 100}.")
    names = [c["name"] for c in deck]
    frequencies = Counter(n.casefold() for n in names)
    for name in names:
        if name.casefold() == commander_name.casefold():
            issues.append(f"{name} is already your commander and cannot also be in the deck.")
            break
    for name, frequency in frequencies.items():
        if frequency > 1:
            issues.append(f"Duplicate nonbasic card: {name} ({frequency} copies).")

    colors = set(commander["color_identity"]) if commander else None
    for name in sorted(set(names), key=str.casefold):
        card = lookup_card(name)
        if card is None:
            warnings.append(f"Could not verify card: {name}.")
            continue
        if not card["legal"]:
            issues.append(f"{name} is not legal in Commander.")
        if colors is not None and not set(card["color_identity"]).issubset(colors):
            issues.append(f"{name} is outside your commander's color identity.")
        # Some cards override singleton via their Oracle text. We do not certify those exceptions here.
        if "a deck can have any number of cards named" in card["oracle_text"].lower():
            warnings.append(f"{name} has a special deck-construction rule; check its permitted quantity.")

    land_colors = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
    for name, qty in basic_lands.items():
        if name not in BASIC_LANDS or not isinstance(qty, int) or qty < 1:
            issues.append(f"Invalid basic land entry: {name}.")
        elif colors is not None and name in land_colors and land_colors[name] not in colors:
            issues.append(f"{name} is outside your commander's color identity.")

    if issues:
        status = "Illegal"
    elif warnings:
        status = "Incomplete" if count != 100 and not any("could not" in w.lower() or "not supported" in w.lower() or "special" in w.lower() for w in warnings) else "Needs review"
    else:
        status = "Legal"
    return {"status": status, "issues": list(dict.fromkeys(issues)),
            "warnings": list(dict.fromkeys(warnings)), "remaining": max(0, 100 - count),
            "count": count}
