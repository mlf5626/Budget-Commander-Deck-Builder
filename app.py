from flask import Flask, render_template, request
import requests

app = Flask(__name__)


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
        cards=cards
    )
if __name__ == "__main__":
    app.run(debug=True)