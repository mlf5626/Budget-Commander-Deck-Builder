"""Explainable, budget-aware Scryfall recommendations (not machine learning)."""
import requests
import re

HEADERS = {"User-Agent": "BudgetCommanderDeckBuilder/1.0", "Accept": "application/json"}
CATEGORIES = {
    "synergy": "Commander Synergy",
    "ramp": "Ramp",
    "draw": "Card Draw",
    "removal": "Removal",
    "protection": "Protection",
}
CATEGORY_QUERIES = {
    "ramp": '(o:"add {" OR o:"onto the battlefield" OR o:"additional land")',
    "draw": '(o:"draw a card" OR o:"draw two cards" OR o:"draw three cards")',
    "removal": '(o:"destroy target" OR o:"exile target")',
    "protection": '(o:"hexproof" OR o:"indestructible" OR o:"protection from")',
}
THEMES = [
    ("proliferate", "Proliferate", 'o:proliferate'),
    ("+1/+1 counter", "+1/+1 counters", 'o:"+1/+1 counter"'),
    ("landfall", "Landfall", 'o:landfall'),
    ("graveyard", "Graveyard", '(o:graveyard OR o:mill)'),
    ("artifact", "Artifacts", '(o:artifact OR t:artifact)'),
    ("enchantment", "Enchantments", '(o:enchantment OR t:enchantment)'),
    ("token", "Tokens", 'o:token'),
    ("lifegain", "Lifegain", '(o:"gain life" OR o:lifelink)'),
    ("surveil", "Surveil", 'o:surveil'),
    ("sacrifice", "Sacrifice", 'o:sacrifice'),
    ("instant", "Spellslinger", '(t:instant OR t:sorcery)'),
]
def detect_theme(commander):
    text = commander.get("oracle_text", "").lower()

    for face in commander.get("card_faces", []):
        text += " " + face.get("oracle_text", "").lower()

    matched_themes = []

    for term, label, query in THEMES:
        if term in text:
            matched_themes.append((label, query))

    if matched_themes:
        labels = [theme[0] for theme in matched_themes]
        queries = [theme[1] for theme in matched_themes]

        theme_label = ", ".join(labels)
        theme_query = "(" + " OR ".join(queries) + ")"

        return theme_label, theme_query

    return "Popular Commander staples", None

def ramp_evidence(card):
    """Distinguish actual acceleration from finding a land for your hand.

    Conservative heuristic: false negatives are possible. Does not certify card
    quality or account for every unusual mana ability.
    """
    text = (card.get("oracle_text") or "")
    for face in card.get("card_faces", []):
        text += " " + (face.get("oracle_text") or "")
    text = text.lower()
    typ = (card.get("type_line") or "").lower()

    # Putting lands directly into play is acceleration; putting them in hand isn't.
    if re.search(r"(?:search your library|put|return).*?land(?:s| cards?)?.*?onto the battlefield", text, re.S):
        return "Puts lands directly onto the battlefield to accelerate mana development."
    if re.search(r"(?:play|put) (?:an? )?additional land", text) or "you may play an additional land" in text:
        return "Allows additional land plays, potentially accelerating mana development."
    # Nonland permanents with explicit mana abilities (rocks, mana creatures).
    if "land" not in typ and re.search(r"(?:\{t\}|tap an untapped|remove .*? counter).*?add \{[wubrgc0-9]", text, re.S):
        return "Provides a mana ability that can accelerate your available mana."
    if "land" not in typ and re.search(r"add \{[wubrgc0-9]\}", text):
        return "Can generate additional mana."
    if re.search(r"create (?:a|one|two|three|[0-9]+).*?treasure token", text, re.S):
        return "Creates Treasure tokens that can be used for mana."
    return None


def explain_recommendation(card, category="synergy"):
    """Explain why a card matches a recommendation category."""
    text = card.get("oracle_text", "").lower()

    for face in card.get("card_faces", []):
        text += " " + face.get("oracle_text", "").lower()

    if category == "ramp":
        return ramp_evidence(card) or "Matches the ramp search; mana acceleration is not verified."

    if category == "synergy":
        matches = [
            label
            for term, label, query in THEMES
            if term in text
        ]

        if matches:
            return (
                "Supports these strategy themes: "
                + ", ".join(matches)
                + "."
            )

        return "Matches the selected Commander strategy search."

    explanations = {
        "ramp": "Helps generate mana or develop your mana resources.",
        "draw": "Provides opportunities to draw additional cards.",
        "removal": "Provides ways to remove opposing permanents.",
        "protection": "Helps protect your creatures or other permanents.",
    }

    return explanations.get(category, "Matches your selected category.")

def fetch_recommendations(commander, deck, remaining_budget, category="synergy", sort="popular", strategy_focus=False):
    """Return (cards, description, error). Filter owned/unpriced/over-budget cards."""
    theme_label, theme_query = detect_theme(commander)
    category = category if category in CATEGORIES else "synergy"
    sort = sort if sort in ("popular", "price") else "popular"
    if category == "synergy":
        if theme_query:
            filter_query = theme_query
            description = f"Cards matching {theme_label.lower()} themes found in your commander's rules text."
        else:
            filter_query = "t:artifact"
            description = "Affordable, popular artifacts; no specific strategy keyword was detected."
    else:
        filter_query = CATEGORY_QUERIES[category]
        description = f"Budget-aware {CATEGORIES[category].lower()} suggestions."
    # Optional focused search: the card must match BOTH the selected role and
    # the commander's detected theme. Keep the original searches as defaults.
    focused = bool(strategy_focus and category != "synergy" and theme_query)
    if focused:
        filter_query = f"({filter_query}) {theme_query}"
        description = (f"Strategy-aware {CATEGORIES[category].lower()} suggestions "
                       f"matching {theme_label.lower()} (when available).")
    elif strategy_focus and category != "synergy" and not theme_query:
        description += " No Commander theme was detected; showing standard suggestions."
    colors = "".join(commander.get("color_identity", []))
    query = f"legal:commander id<={colors} -t:land game:paper usd>0 usd<={max(0, remaining_budget):.2f} {filter_query}"
    if remaining_budget <= 0:
        return [], description, None
    params = {"q": query, "order": "usd" if sort == "price" else "edhrec", "dir": "asc"}
    try:
        response = requests.get("https://api.scryfall.com/cards/search",
                                params=params, headers=HEADERS, timeout=10)
        if response.status_code == 404:
            if focused:
                return [], (description + " No matching cards were found within your remaining "
                            "budget. Try the standard category recommendations instead."), None
            return [], description, None
        response.raise_for_status()
        payload = response.json()
        owned = {c["name"].casefold() for c in deck}
        owned.add(commander.get("name", "").casefold())
        cards = []
        for card in payload.get("data", []):
            price = card.get("prices", {}).get("usd")
            try:
                amount = float(price)
            except (TypeError, ValueError):
                continue
            if card.get("name", "").casefold() in owned or amount > remaining_budget:
                continue
            if category == "ramp" and not ramp_evidence(card):
                continue
            card["recommendation_reason"] = explain_recommendation(card, category)
            cards.append(card)
            if len(cards) >= 18:
                break
        if focused and not cards:
            description += " No verified mana-acceleration matches were found. Try standard suggestions."
        elif focused:
            for card in cards:
                card["recommendation_reason"] = (
                    explain_recommendation(card, category) +
                    f" Also matches the detected Commander theme: {theme_label}."
                )
        return cards, description, None
    except (requests.RequestException, ValueError, TypeError):
        return [], description, "Scryfall is temporarily unavailable. Please try again."
