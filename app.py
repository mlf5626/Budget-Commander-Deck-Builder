from flask import Flask, render_template, request, session, redirect, url_for
import requests

app = Flask(__name__)
app.secret_key = "budget-commander-deck-builder"

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    commander_name = request.form.get("commander")

    url = "https://api.scryfall.com/cards/named"
    params = {"fuzzy": commander_name}

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=10
    )

    print("Scryfall URL:", response.url)
    print("Scryfall Status:", response.status_code)
    print("Scryfall Response:", response.text)

    if response.status_code == 200:
        commander = response.json()

        return render_template(
            "commander.html",
            commander=commander
        )

    return "Commander not found."

@app.route("/build", methods=["POST"])
def build():
    commander_name = request.form.get("commander_name")
    budget = request.form.get("budget")
    
    session["commander_name"] = commander_name
    session["budget"] = budget
    session["deck"] = []

    # Look up the selected Commander again
    commander_url = "https://api.scryfall.com/cards/named"
    commander_params = {"exact": commander_name}

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    commander_response = requests.get(
        commander_url,
        params=commander_params,
        headers=headers,
        timeout=10
    )

    if commander_response.status_code != 200:
        return "Unable to retrieve Commander."

    commander = commander_response.json()

    # Convert color identity into a Scryfall search value
    color_identity = "".join(commander["color_identity"])

    # Search for Commander-legal cards within the Commander's colors
    search_url = "https://api.scryfall.com/cards/search"

    search_query = (
        f"legal:commander "
        f"id<={color_identity} "
        f"-t:land "
        f"game:paper"
    )

    card_response = requests.get(
        search_url,
        params={"q": search_query},
        headers=headers,
        timeout=10
    )

    if card_response.status_code != 200:
        return "Unable to retrieve legal cards."

    card_data = card_response.json()

    cards = card_data["data"][:20]

    return render_template(
    "builder.html",
    commander=commander,
    budget=budget,
    cards=cards,
    deck=session["deck"],
    deck_size=1,
    deck_cost=0.00
    )

@app.route("/add-card", methods=["POST"])
def add_card():
    card_name = request.form.get("card_name")
    card_price = request.form.get("card_price")

    deck = session.get("deck", [])

    # Prevent duplicate cards
    for existing_card in deck:
        if existing_card["name"] == card_name:
            return redirect(url_for("deck"))

    card = {
        "name": card_name,
        "price": float(card_price)
    }

    deck.append(card)

    session["deck"] = deck

    return redirect(url_for("deck"))

@app.route("/remove-card", methods=["POST"])
def remove_card():
    card_name = request.form.get("card_name")

    deck = session.get("deck", [])

    deck = [
        card for card in deck
        if card["name"] != card_name
    ]

    session["deck"] = deck

    return redirect(url_for("deck"))

@app.route("/deck")
def deck():
    deck = session.get("deck", [])
    commander_name = session.get("commander_name")
    budget = float(session.get("budget", 0))

    deck_cost = sum(card["price"] for card in deck)
    deck_size = len(deck) + 1

    return render_template(
        "deck.html",
        commander_name=commander_name,
        budget=budget,
        deck=deck,
        deck_cost=deck_cost,
        deck_size=deck_size
    )

@app.route("/continue-building")
def continue_building():
    commander_name = session.get("commander_name")
    budget = float(session.get("budget", 0))
    deck = session.get("deck", [])

    if not commander_name:
        return redirect(url_for("home"))

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    # Retrieve Commander information
    commander_response = requests.get(
        "https://api.scryfall.com/cards/named",
        params={"exact": commander_name},
        headers=headers,
        timeout=10
    )

    if commander_response.status_code != 200:
        return "Unable to retrieve Commander."

    commander = commander_response.json()

    color_identity = "".join(commander["color_identity"])

    search_query = (
        f"legal:commander "
        f"id<={color_identity} "
        f"-t:land "
        f"game:paper"
    )

    card_response = requests.get(
        "https://api.scryfall.com/cards/search",
        params={"q": search_query},
        headers=headers,
        timeout=10
    )

    if card_response.status_code != 200:
        return "Unable to retrieve legal cards."

    cards = card_response.json()["data"][:20]

    deck_cost = sum(card["price"] for card in deck)
    deck_size = len(deck) + 1

    return render_template(
        "builder.html",
        commander=commander,
        budget=budget,
        cards=cards,
        deck=deck,
        deck_cost=deck_cost,
        deck_size=deck_size
    )

@app.route("/search-cards", methods=["POST"])
def search_cards():
    card_search = request.form.get("card_search", "").strip()

    commander_name = session.get("commander_name")
    budget = float(session.get("budget", 0))
    deck = session.get("deck", [])

    if not commander_name:
        return redirect(url_for("home"))

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    # Retrieve the selected Commander
    commander_response = requests.get(
        "https://api.scryfall.com/cards/named",
        params={"exact": commander_name},
        headers=headers,
        timeout=10
    )

    if commander_response.status_code != 200:
        return "Unable to retrieve Commander."

    commander = commander_response.json()

    color_identity = "".join(commander["color_identity"])

    # Search only for cards legal with this Commander
    search_query = (
        f"legal:commander "
        f"id<={color_identity} "
        f"-t:land "
        f"game:paper "
        f"{card_search}"
    )

    card_response = requests.get(
        "https://api.scryfall.com/cards/search",
        params={"q": search_query},
        headers=headers,
        timeout=10
    )

    if card_response.status_code != 200:
        cards = []
    else:
        cards = card_response.json()["data"][:20]

    deck_cost = sum(card["price"] for card in deck)
    deck_size = len(deck) + 1

    return render_template(
        "builder.html",
        commander=commander,
        budget=budget,
        cards=cards,
        deck=deck,
        deck_cost=deck_cost,
        deck_size=deck_size,
        card_search=card_search
    )

@app.route("/category", methods=["POST"])
def category():
    selected_category = request.form.get("category")
    max_price = request.form.get("max_price", "5.00")

    try:
        max_price_value = float(max_price)
    except ValueError:
        max_price_value = 5.00

    commander_name = session.get("commander_name")
    budget = float(session.get("budget", 0))
    deck = session.get("deck", [])

    if not commander_name:
        return redirect(url_for("home"))

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    # Retrieve Commander information
    commander_response = requests.get(
        "https://api.scryfall.com/cards/named",
        params={"exact": commander_name},
        headers=headers,
        timeout=10
    )

    if commander_response.status_code != 200:
        return "Unable to retrieve Commander."

    commander = commander_response.json()

    color_identity = "".join(commander["color_identity"])

    # Define searches for deck-building categories
    category_queries = {
    "ramp": (
        '(o:"add {" OR o:"search your library for a basic land" '
        'OR o:"search your library for a land")'
    ),

    "draw": (
        '(o:"draw a card" OR o:"draw two cards" '
        'OR o:"draw three cards")'
    ),

    "removal": (
        '(o:"destroy target" OR o:"exile target")'
    ),

    "board_wipe": (
        '(o:"destroy all" OR o:"exile all")'
    ),

    "protection": (
        '(o:"hexproof" OR o:"indestructible" '
        'OR o:"protection from")'
    )
}

    category_query = category_queries.get(selected_category, "")

    search_query = (
    f"legal:commander "
    f"id<={color_identity} "
    f"-t:land "
    f"game:paper "
    f"usd<={max_price_value} "
    f"{category_query}"
)
    card_response = requests.get(
        "https://api.scryfall.com/cards/search",
        params={
            "q": search_query,
            "order": "edhrec"
        },
        headers=headers,
        timeout=10
    )

    if card_response.status_code != 200:
        cards = []
    else:
        cards = card_response.json()["data"][:20]

    deck_cost = sum(card["price"] for card in deck)
    deck_size = len(deck) + 1

    return render_template(
        "builder.html",
        commander=commander,
        budget=budget,
        cards=cards,
        deck=deck,
        deck_cost=deck_cost,
        deck_size=deck_size,
        selected_category=selected_category,
        max_price=max_price
    )

if __name__ == "__main__":
    app.run(debug=True)