# Budget Commander Deck Builder

**IST 440W Capstone Project — Final Implementation**

A local web application that helps Magic: The Gathering players assemble a Commander deck while tracking a custom budget. It uses the Scryfall API for card information and estimated USD prices, Flask for the web application, and SQLite for saved decks.

## Current features

- Search for a Commander and choose a deck budget.
- Browse and search cards using Commander color identity and category filters.
- Add or remove cards, including quantities of basic lands, with a 100-card limit and estimated budget tracking.
- Review a basic Commander legality report. Special Commander rules and exceptions may not be fully covered.
- See budget-aware card recommendations, including Commander synergy and category-based suggestions.
- Use **Analyze My Deck** to review deck composition, strengths, gaps, and strategy themes.
- Save, load, update, and delete decks in a local SQLite database.
- Export the current deck or a saved deck as a plain-text card list.
- Review a shopping list and follow TCGplayer search links for individual cards.

## Requirements

- Python 3.10 or newer (recommended)
- Internet access to retrieve card data from Scryfall and open TCGplayer searches
- A modern web browser
- Git (optional; needed for the clone command)

No Scryfall API key is required for the current implementation.

## Installation on Windows (PowerShell)

These steps work for a **fresh GitHub download**, including when you are installing the project in a separate folder from your original development copy. Python must already be installed.

1. Check Python in PowerShell:

   ```powershell
   python --version
   ```

   The project has been installed using Python 3.13.14. If `python` is not recognized, install Python and reopen PowerShell. Some computers use `py --version` instead.

2. Download the project from [GitHub](https://github.com/mlf5626/Budget-Commander-Deck-Builder): select **Code → Download ZIP**. Find the ZIP in Downloads, choose **Extract All**, and extract it into a folder of your choice (for example, `Documents\IST440W-Fresh-Installation`). Open the extracted `Budget-Commander-Deck-Builder-main` folder. It should contain `app.py`, `requirements.txt`, and `README.md`.

   **Open PowerShell in that project folder:** In File Explorer, click the address bar, type `powershell`, and press Enter. Make sure the PowerShell prompt ends with the extracted project folder name, not just the parent folder.

   **Alternative using Git** (if installed):

   ```powershell
   git clone https://github.com/mlf5626/Budget-Commander-Deck-Builder.git
   cd Budget-Commander-Deck-Builder
   ```

3. Create a fresh virtual environment in the project folder:

   ```powershell
   python -m venv .venv
   ```

   If `python` does not work but the Python launcher does, use `py -m venv .venv` instead.

4. Install the required packages into that environment. You do **not** need to activate the environment first:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   Wait until PowerShell reports `Successfully installed ...`. A notice that a newer version of pip is available is not an installation failure.

5. Start the Flask application:

   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```

   When Flask reports `Running on http://127.0.0.1:5000`, leave PowerShell open.

6. Open **http://127.0.0.1:5000** in a web browser. The application should show the Budget Commander Deck Builder homepage.

7. When finished, return to PowerShell and press **Ctrl+C** to stop the application.

**Important:** The SQLite database is created automatically when the application starts. A fresh download begins with no saved decks, and changes made in this copy do not update the original development copy. Do not copy the old `.venv` folder into a new installation.

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
4. Open **Your Commander Deck** to review card count, budget, estimated cost, and legality feedback. Use **Analyze My Deck** to review suggested improvements, strategy themes, and card-role gaps.
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

- **`py` is not recognized:** Use `python --version` and `python -m venv .venv` instead. The `py` launcher is not required if `python` works.
- **`python` is not recognized:** Install Python from python.org, ensure it is available in PowerShell, then reopen PowerShell.
- **`.\.venv\Scripts\python.exe` is not recognized:** Create the virtual environment first with `python -m venv .venv`, and make sure PowerShell is open in the correct project folder.
- **`No module named flask`:** Install dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, then start the app using that same virtual environment.
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
