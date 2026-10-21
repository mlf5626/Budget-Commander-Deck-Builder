"""Commander deck validation using Scryfall card data."""
from collections import Counter
from functools import lru_cache
import requests
import re

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
            "mana_cost": card.get("mana_cost") or " // ".join(face.get("mana_cost", "") for face in card.get("card_faces", []) if face.get("mana_cost")),
            "oracle_text": card.get("oracle_text", ""),
            "keywords": card.get("keywords", []),
            "layout": card.get("layout", ""),
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


# Heuristic roles: useful guidance, not definitive card classification.
ROLE_KEYS = (
    "Ramp / Mana Acceleration", "Card Draw / Advantage", "Targeted Removal",
    "Board Wipes", "Protection", "Win Conditions / Finishers",
)


def classify_card_roles(card):
    """Estimate functional roles from Scryfall Oracle text; roles may overlap."""
    if not card:
        return set()
    text = card.get("oracle_text", "").lower()
    typ = card.get("type_line", "").lower()
    keywords = {str(k).lower() for k in card.get("keywords", [])}
    roles = set()

    # Mana production on nonlands, mana acceleration, and putting lands onto the battlefield.
    mana_ability = bool(re.search(r"(?:\{t\}|tap an untapped|remove a .*counter).*?add \{[wubrgc]\}", text, re.S))
    mana_rock = "land" not in typ and mana_ability
    extra_mana = bool(re.search(r"add (?:an additional|\{[0-9wubrgc]\}\{[0-9wubrgc]\})", text))
    land_ramp = bool(re.search(r"(?:search your library for|put) .*?land card.*?(?:onto the battlefield|onto the battlefield tapped)", text, re.S))
    if mana_rock or extra_mana or land_ramp or "treasure token" in text and "create" in text:
        roles.add("Ramp / Mana Acceleration")

    if (re.search(r"draw (?:a|one|two|three|four|[0-9]+|x) cards?", text)
            or "draw cards equal to" in text or "whenever you draw" in text
            or "look at the top" in text and "put" in text and "hand" in text):
        roles.add("Card Draw / Advantage")

    wipe = bool(re.search(r"(?:destroy|exile|return) (?:all|each) (?:creatures?|artifacts?|enchantments?|nonland permanents?|permanents?)", text))
    if wipe or "each creature gets -" in text or "all creatures get -" in text:
        roles.add("Board Wipes")
    elif re.search(r"(?:destroy|exile|return) target (?:creature|artifact|enchantment|permanent|nonland permanent|planeswalker)", text) or "counter target spell" in text:
        roles.add("Targeted Removal")

    if ("hexproof" in text or "indestructible" in text or "phase out" in text
            or "protection from" in text or "ward" in keywords
            or "can't be the target" in text):
        roles.add("Protection")

    if ("you win the game" in text or "target player loses the game" in text
            or "each opponent loses the game" in text):
        roles.add("Win Conditions / Finishers")
    return roles

def validate_deck(commander_name, deck, basic_lands):
    """Return a conservative legality assessment; never claim legal if verification fails."""
    count = 1 + len(deck) + sum(basic_lands.values())
    role_counts = {key: 0 for key in ROLE_KEYS}
    unverified_role_cards = 0
    issues = []
    warnings = []
    composition = {key: 0 for key in (
        "Creatures", "Artifacts", "Enchantments", "Instants",
        "Sorceries", "Lands", "Planeswalkers", "Other", "Unverified"
    )}

    def count_card_type(card_data, quantity=1):
        """Assign one primary type per card so totals equal the deck size."""
        if card_data is None:
            composition["Unverified"] += quantity
            return
        type_line = card_data.get("type_line", "").split(" // ")[0]
        for word, category in (
            ("Creature", "Creatures"), ("Land", "Lands"),
            ("Planeswalker", "Planeswalkers"), ("Instant", "Instants"),
            ("Sorcery", "Sorceries"), ("Artifact", "Artifacts"),
            ("Enchantment", "Enchantments"),
        ):
            if word in type_line.split():
                composition[category] += quantity
                return
        composition["Other"] += quantity

    commander = lookup_card(commander_name) if commander_name else None
    count_card_type(commander)
    if commander:
        for role in classify_card_roles(commander):
            role_counts[role] += 1
    else:
        unverified_role_cards += 1
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
        count_card_type(card, frequencies[name.casefold()])
        if card is None:
            unverified_role_cards += frequencies[name.casefold()]
            warnings.append(f"Could not verify card: {name}.")
            continue
        for role in classify_card_roles(card):
            role_counts[role] += frequencies[name.casefold()]
        if not card["legal"]:
            issues.append(f"{name} is not legal in Commander.")
        if colors is not None and not set(card["color_identity"]).issubset(colors):
            issues.append(f"{name} is outside your commander's color identity.")
        # Some cards override singleton via their Oracle text. We do not certify those exceptions here.
        if "a deck can have any number of cards named" in card["oracle_text"].lower():
            warnings.append(f"{name} has a special deck-construction rule; check its permitted quantity.")

    composition["Lands"] += sum(basic_lands.values())

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
            "count": count, "composition": composition,
            "role_counts": role_counts, "unverified_role_cards": unverified_role_cards}
