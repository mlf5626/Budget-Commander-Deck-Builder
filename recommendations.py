"""Explainable, budget-aware Scryfall recommendations (not machine learning)."""
import requests

HEADERS = {"User-Agent": "BudgetCommanderDeckBuilder/1.0", "Accept": "application/json"}
CATEGORIES = {
    "synergy": "Commander Synergy",
    "ramp": "Ramp",
    "draw": "Card Draw",
    "removal": "Removal",
    "protection": "Protection",
}
CATEGORY_QUERIES = {
    "ramp": '(o:"add {" OR o:"search your library for a basic land" OR o:"search your library for a land")',
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
    for term, label, query in THEMES:
        if term in text:
            return label, query
    return "Popular Commander staples", None

def fetch_recommendations(commander, deck, remaining_budget, category="synergy", sort="popular"):
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
    colors = "".join(commander.get("color_identity", []))
    query = f"legal:commander id<={colors} -t:land game:paper usd>0 usd<={max(0, remaining_budget):.2f} {filter_query}"
    if remaining_budget <= 0:
        return [], description, None
    params = {"q": query, "order": "usd" if sort == "price" else "edhrec", "dir": "asc"}
    try:
        response = requests.get("https://api.scryfall.com/cards/search",
                                params=params, headers=HEADERS, timeout=10)
        if response.status_code == 404:
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
            cards.append(card)
            if len(cards) >= 18:
                break
        return cards, description, None
    except (requests.RequestException, ValueError, TypeError):
        return [], description, "Scryfall is temporarily unavailable. Please try again."
