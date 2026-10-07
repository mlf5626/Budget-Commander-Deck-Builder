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


if __name__ == "__main__":
    app.run(debug=True)