# Budget Commander Deck Builder

**IST 440W Capstone Project — Basic Implementation**

A local web application that helps Magic: The Gathering players assemble a Commander deck while tracking a custom budget. It uses the Scryfall API for card information and estimated USD prices, Flask for the web application, and SQLite for saved decks.

## Current features

- Search for a Commander and choose a deck budget.
- Browse and search cards using Commander color identity and category filters.
- Add or remove cards, including quantities of basic lands, with a 100-card limit and estimated budget tracking.
- Review a basic Commander legality report. Special Commander rules and exceptions may not be fully covered.
- See budget-aware card recommendations.
- Save, load, update, and delete decks in a local SQLite database.
- Export the current deck or a saved deck as a plain-text card list.
- Review a shopping list and follow TCGplayer search links for individual cards.

## Requirements

- Python 3.10 or newer (recommended)
- Internet access to retrieve card data from Scryfall and open TCGplayer searches
- A modern web browser
- Git (optional; needed for the clone command)

No Scryfall API key is required for the current implementation.

## Installation on Windows

1. Open **PowerShell** or a terminal in a folder where you want the project.
2. Download the repository using Git:

   ```powershell
   git clone https://github.com/mlf5626/Budget-Commander-Deck-Builder.git
   cd Budget-Commander-Deck-Builder
   ```

   Alternatively, select **Code → Download ZIP** on GitHub, extract the ZIP, and open a terminal in the extracted project folder.

3. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

4. Install the dependencies directly into the virtual environment (this works without activating it):

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Start the application:

   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```

6. Open **http://127.0.0.1:5000** in a browser.

7. Stop the application by pressing **Ctrl+C** in the terminal.

The SQLite database is initialized automatically on first launch. The database file is intentionally excluded from Git; a fresh installation begins without saved decks.

## Installation on macOS or Linux

```bash
git clone https://github.com/mlf5626/Budget-Commander-Deck-Builder.git
cd Budget-Commander-Deck-Builder
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:5000**.

## How to use

1. Enter a Commander name on the homepage and select the matching Commander.
2. Enter a custom budget to start a new deck.
3. Search or browse cards and add them to the deck. Add basic lands as needed.
4. Open **Your Commander Deck** to review card count, budget, estimated cost, and basic legality feedback.
5. Select **Save Deck** to store your progress. Use **My Saved Decks** on the homepage to load or manage decks later.
6. Select **Export Deck (.txt)** to download a text deck list, or **Buy Cards** to view individual TCGplayer search links.

## Project structure

```text
Budget-Commander-Deck-Builder/
├── app.py                 # Flask routes and deck-building workflow
├── database.py            # SQLite saved-deck operations
├── legality.py            # Basic Commander legality validation
├── recommendations.py     # Budget-aware card recommendations
├── templates/             # HTML/Jinja pages, including deck and shopping pages
├── requirements.txt       # Python dependencies
├── test_legality.py       # Legality-check tests
└── README.md              # Setup and project documentation
```

## Data and limitations

- Card details and prices are retrieved from **Scryfall**; network access is necessary for normal operation.
- Prices are estimates, not live TCGplayer checkout prices. Shipping, tax, condition, printing, and availability can change the total.
- TCGplayer links open search results; the application does not process orders or payments.
- Saved decks are stored in a **local SQLite database** on the computer running the application. They are not synchronized across computers.
- The legality checker supports common single-Commander rules but does not guarantee comprehensive rules enforcement.
- This is a **local development prototype**, not a production-hosted multiuser service. Run it locally; do not expose the Flask debug server to the public internet.

## Troubleshooting

- **`py` is not recognized:** Install Python from python.org, then retry; on some systems use `python` instead of `py`.
- **`git` is not recognized:** Install Git or use GitHub's **Download ZIP** option.
- **`ModuleNotFoundError`:** Re-run the virtual-environment dependency installation command above.
- **Scryfall search fails:** Check your internet connection and try again.
- **Port 5000 is already in use:** Stop the other Flask process and restart this application.
- **No saved decks appear:** A new installation creates its own empty local database; saved decks from another computer are not included.

## AI assistance and course documentation

AI assistance was used during planning, code development, and documentation. The IST 440W submission separately includes the relevant AI prompt history, implementation screenshots, functional decomposition, technical and operational flowcharts, self-reflection, and updated schedule charts.

## Source links

- [Scryfall API](https://scryfall.com/docs/api)
- [TCGplayer](https://www.tcgplayer.com/)
- [Flask](https://flask.palletsprojects.com/)
