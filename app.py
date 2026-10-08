from flask import Flask, render_template, request, session, redirect, url_for
import requests
from functools import lru_cache
import sqlite3
from legality import validate_deck
from database import (
    init_db, save_deck, list_saved_decks, load_saved_deck,
    update_saved_deck, delete_saved_deck,
)

app = Flask(__name__)
app.secret_key = "budget-commander-deck-builder"

# Initialize the SQLite database
init_db()


@lru_cache(maxsize=10)
def get_basic_land_price(land_name):
    """Retrieve an estimated USD price for a basic land."""

    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    response = requests.get(
        "https://api.scryfall.com/cards/search",
        params={
            "q": f'!"{land_name}" t:basic game:paper usd>0',
            "order": "usd",
            "dir": "asc"
        },
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        return None

    cards = response.json().get("data", [])

    for card in cards:
        price = card.get("prices", {}).get("usd")

        if price:
            return float(price)

    return None


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

        commander_price = commander["prices"].get("usd")

        if commander_price:
            commander_price = float(commander_price)
        else:
            commander_price = 0.00

        session["commander_price"] = commander_price

        return render_template(
            "commander.html",
            commander=commander
        )

    return "Commander not found."

@app.route("/build", methods=["POST"])
def build():
    commander_name = request.form.get("commander_name")
    budget = request.form.get("budget")
    commander_price = float(
        session.get("commander_price", 0)
    )
    try:
        budget_value = float(budget)
    except (TypeError, ValueError):
        return "Please enter a valid deck budget."

    if budget_value <= 0:
        return "Deck budget must be greater than $0."

    if commander_price > budget_value:
        return (
            f"Your Commander costs ${commander_price:.2f}, "
            f"which exceeds your ${budget_value:.2f} budget. "
            "Please go back and choose a higher budget."
        )
    
    session["commander_name"] = commander_name
    session["budget"] = budget
    session["deck"] = []
    session["basic_lands"] = {}
    session.pop("saved_deck_id", None)

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
    deck_cost=commander_price
    )

@app.route("/add-card", methods=["POST"])
def add_card():
    card_name = request.form.get("card_name")
    card_price = request.form.get("card_price")

    deck = session.get("deck", [])
    budget = float(session.get("budget", 0))

    try:
        price = float(card_price)
    except (TypeError, ValueError):
        return redirect(url_for("deck"))

    # Prevent duplicate cards
    for existing_card in deck:
        if existing_card["name"] == card_name:
            return redirect(url_for("deck"))

    # Count Commander, individual cards, and basic lands
    basic_lands = session.get("basic_lands", {})
    basic_land_count = sum(basic_lands.values())

    current_deck_size = 1 + len(deck) + basic_land_count

    # Prevent deck from exceeding 100 cards
    if current_deck_size >= 100:
        session["message"] = "Your deck already contains 100 cards."
        return redirect(url_for("deck"))

    # Calculate current deck cost
    commander_price = float(
        session.get("commander_price", 0)
    )

    current_deck_cost = commander_price + sum(
        card["price"] for card in deck
    )

    
    # Include existing basic lands in the deck cost
    basic_lands = session.get("basic_lands", {})

    for land_name, quantity in basic_lands.items():
        land_price = get_basic_land_price(land_name)

        if land_price is None:
            session["message"] = "Unable to verify basic land prices."
            return redirect(url_for("deck"))

        current_deck_cost += land_price * quantity


    # Prevent the new card from exceeding the budget
    if current_deck_cost + price > budget:
        session["message"] = (
            f"{card_name} would put your deck over budget."
        )
        return redirect(url_for("deck"))

    card = {
        "name": card_name,
        "price": price
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
    message = session.pop("message", None)
    commander_name = session.get("commander_name")
    budget = float(session.get("budget", 0))

    commander_price = float(
        session.get("commander_price", 0)
    )

    

    # Get basic lands and calculate deck size
    basic_lands = session.get("basic_lands", {})
    basic_land_count = sum(basic_lands.values())
    deck_size = 1 + len(deck) + basic_land_count

    # Calculate the cost of basic lands
    basic_land_cost = 0.0
    unpriced_lands = []
    basic_land_prices = {}

    for land_name, quantity in basic_lands.items():
        land_price = get_basic_land_price(land_name)

        if land_price is None:
            unpriced_lands.append(land_name)
        else:
            basic_land_prices[land_name] = land_price
            basic_land_cost += land_price * quantity

    # Include basic lands in the estimated deck cost
    deck_cost = (
        commander_price
        + sum(card["price"] for card in deck)
        + basic_land_cost
    )


    legality = validate_deck(commander_name, deck, basic_lands)

    return render_template(
        "deck.html",
        commander_name=commander_name,
        commander_price=commander_price,
        budget=budget,
        deck=deck,
        deck_cost=deck_cost,
        deck_size=deck_size,
        basic_lands=basic_lands,
        basic_land_count=basic_land_count,
        basic_land_prices=basic_land_prices,
        message=message,
        saved_deck_id=session.get("saved_deck_id"),
        legality=legality
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

    commander_price = float(
        session.get("commander_price", 0)
    )

     # Get basic lands from the session
    basic_lands = session.get("basic_lands", {})

    # Calculate the cost of basic lands
    basic_land_cost = 0.0

    for land_name, quantity in basic_lands.items():
        land_price = get_basic_land_price(land_name)

        if land_price is not None:
            basic_land_cost += land_price * quantity

    # Calculate total estimated deck cost
    deck_cost = (
        commander_price
        + sum(card["price"] for card in deck)
        + basic_land_cost
    )

    basic_lands = session.get("basic_lands", {})
    basic_land_count = sum(basic_lands.values())

    deck_size = 1 + len(deck) + basic_land_count

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

    commander_price = float(
        session.get("commander_price", 0)
    )

    # Get basic lands from the session
    basic_lands = session.get("basic_lands", {})

    # Calculate the cost of basic lands
    basic_land_cost = 0.0

    for land_name, quantity in basic_lands.items():
        land_price = get_basic_land_price(land_name)

        if land_price is not None:
            basic_land_cost += land_price * quantity

    # Include basic lands in the estimated deck cost
    deck_cost = (
        commander_price
        + sum(card["price"] for card in deck)
        + basic_land_cost
    )

    # Include basic lands in the deck size
    basic_lands = session.get("basic_lands", {})
    basic_land_count = sum(basic_lands.values())

    deck_size = 1 + len(deck) + basic_land_count

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

    commander_price = float(
        session.get("commander_price", 0)
    )

    # Get basic lands from the session
    basic_lands = session.get("basic_lands", {})

    # Calculate the cost of basic lands
    basic_land_cost = 0.0

    for land_name, quantity in basic_lands.items():
        land_price = get_basic_land_price(land_name)

        if land_price is not None:
            basic_land_cost += land_price * quantity

    # Include basic lands in the estimated deck cost
    deck_cost = (
        commander_price
        + sum(card["price"] for card in deck)
        + basic_land_cost
    )

    # Include basic lands in the deck size
    basic_lands = session.get("basic_lands", {})
    basic_land_count = sum(basic_lands.values())

    deck_size = 1 + len(deck) + basic_land_count

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


@app.route("/add-basic-land", methods=["POST"])
def add_basic_land():
    land_name = request.form.get("land_name")
    quantity_text = request.form.get("quantity", "1")

    land_colors = {
        "Plains": "W",
        "Island": "U",
        "Swamp": "B",
        "Mountain": "R",
        "Forest": "G"
    }

    # Check that the land is a recognized basic land
    if land_name not in land_colors:
        session["message"] = "Invalid basic land."
        return redirect(url_for("deck"))

    # Validate the requested quantity
    try:
        quantity = int(quantity_text)
    except (TypeError, ValueError):
        session["message"] = "Please enter a valid land quantity."
        return redirect(url_for("deck"))

    if quantity <= 0:
        session["message"] = "Land quantity must be greater than zero."
        return redirect(url_for("deck"))

    # Check that a deck has been started
    commander_name = session.get("commander_name")

    if not commander_name:
        return redirect(url_for("home"))

    # Retrieve the Commander's color identity
    headers = {
        "User-Agent": "BudgetCommanderDeckBuilder/1.0",
        "Accept": "application/json"
    }

    response = requests.get(
        "https://api.scryfall.com/cards/named",
        params={"exact": commander_name},
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        session["message"] = "Unable to verify Commander colors."
        return redirect(url_for("deck"))

    commander = response.json()
    color_identity = commander.get("color_identity", [])

    # Only allow lands that match the Commander's colors
    if land_colors[land_name] not in color_identity:
        session["message"] = (
            f"{land_name} is outside your Commander's color identity."
        )
        return redirect(url_for("deck"))

    deck = session.get("deck", [])
    basic_lands = session.get("basic_lands", {})

    current_land_count = sum(basic_lands.values())
    current_deck_size = 1 + len(deck) + current_land_count

    # Do not exceed 100 cards
    if current_deck_size + quantity > 100:
        session["message"] = "Adding these lands would exceed 100 cards."
        return redirect(url_for("deck"))

    
    # Get the selected land's estimated price
    land_price = get_basic_land_price(land_name)

    if land_price is None:
        session["message"] = "Unable to retrieve the basic land price. Please try again."
        return redirect(url_for("deck"))

    # Calculate the current cost of the deck
    budget = float(session.get("budget", 0))
    commander_price = float(session.get("commander_price", 0))
    current_deck_cost = commander_price + sum(
        card["price"] for card in deck
    )

    # Include basic lands already in the deck
    for existing_land, existing_quantity in basic_lands.items():
        existing_price = get_basic_land_price(existing_land)

        if existing_price is None:
            session["message"] = "Unable to verify existing basic land prices."
            return redirect(url_for("deck"))

        current_deck_cost += existing_price * existing_quantity

    # Check whether the new lands would exceed the budget
    new_land_cost = land_price * quantity

    if current_deck_cost + new_land_cost > budget + 0.000001:
        session["message"] = "Adding these basic lands would exceed your deck budget."
        return redirect(url_for("deck"))


    # Save the land quantities
    basic_lands[land_name] = (
        basic_lands.get(land_name, 0) + quantity
    )

    session["basic_lands"] = basic_lands

    return redirect(url_for("deck"))


@app.route("/remove-basic-land", methods=["POST"])
def remove_basic_land():

    land_name = request.form.get("land_name")
    quantity_text = request.form.get("quantity", "1")

    basic_lands = session.get("basic_lands", {})

    # Check that the land exists in the deck
    if land_name not in basic_lands:
        session["message"] = "That basic land is not in your deck."
        return redirect(url_for("deck"))

    # Validate the quantity
    try:
        quantity = int(quantity_text)
    except (TypeError, ValueError):
        session["message"] = "Please enter a valid quantity."
        return redirect(url_for("deck"))

    if quantity <= 0:
        session["message"] = "Quantity must be greater than zero."
        return redirect(url_for("deck"))

    current_quantity = basic_lands[land_name]

    # Prevent removing more copies than are available
    if quantity > current_quantity:
        session["message"] = (
            f"You only have {current_quantity} copies of {land_name}."
        )
        return redirect(url_for("deck"))

    # Subtract the requested quantity
    new_quantity = current_quantity - quantity

    if new_quantity == 0:
        del basic_lands[land_name]
    else:
        basic_lands[land_name] = new_quantity

    session["basic_lands"] = basic_lands

    return redirect(url_for("deck"))



@app.route("/save-deck", methods=["POST"])
def save_current_deck():
    commander_name = session.get("commander_name")
    if not commander_name:
        return redirect(url_for("home"))
    deck = session.get("deck", [])
    basic_lands = session.get("basic_lands", {})
    commander_price = float(session.get("commander_price", 0))
    budget = float(session.get("budget", 0))
    saved_id = session.get("saved_deck_id")
    if saved_id is not None:
        updated = update_saved_deck(
            int(saved_id), commander_name, commander_price, budget, deck, basic_lands
        )
        if not updated:
            session.pop("saved_deck_id", None)
            session["message"] = "Saved deck not found. Please save again."
            return redirect(url_for("deck"))
        session["message"] = "Changes saved successfully."
    else:
        saved_id = save_deck(commander_name, commander_price, budget, deck, basic_lands)
        session["saved_deck_id"] = saved_id
        session["message"] = "Deck saved successfully."
    return redirect(url_for("deck"))


@app.route("/saved-decks")
def saved_decks():
    return render_template("saved_decks.html", decks=list_saved_decks())


@app.route("/load-deck/<int:deck_id>", methods=["POST"])
def load_deck(deck_id):
    saved = load_saved_deck(deck_id)
    if saved is None:
        return "Saved deck not found.", 404
    session["commander_name"] = saved["commander_name"]
    session["commander_price"] = saved["commander_price"]
    session["budget"] = saved["budget"]
    session["deck"] = saved["deck"]
    session["basic_lands"] = saved["basic_lands"]
    session["saved_deck_id"] = saved["id"]
    session["message"] = "Saved deck loaded. You can continue editing it."
    return redirect(url_for("deck"))


@app.route("/delete-deck/<int:deck_id>", methods=["POST"])
def delete_deck(deck_id):
    if not delete_saved_deck(deck_id):
        return "Saved deck not found.", 404
    if session.get("saved_deck_id") == deck_id:
        session.pop("saved_deck_id", None)
    return redirect(url_for("saved_decks"))


if __name__ == "__main__":
    app.run(debug=True)