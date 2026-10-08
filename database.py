
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "commander_decks.db"


def init_db():
    """Create the database tables if they do not exist."""

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Store Commander decks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commander_name TEXT NOT NULL,
            commander_price REAL NOT NULL,
            budget REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Store cards belonging to each deck
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deck_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            card_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (deck_id) REFERENCES decks(id)
        )
    """)

    connection.commit()
    connection.close()


def save_deck(commander_name, commander_price, budget, deck, basic_lands):
    """Save a Commander deck and its cards to SQLite."""

    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    try:
        # Create a new deck record
        cursor.execute("""
            INSERT INTO decks (commander_name, commander_price, budget)
            VALUES (?, ?, ?)
        """, (commander_name, commander_price, budget))

        deck_id = cursor.lastrowid

        # Save individually selected cards
        for card in deck:
            cursor.execute("""
                INSERT INTO deck_cards
                    (deck_id, card_name, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (
                deck_id,
                card["name"],
                1,
                card["price"]
            ))

        # Save basic lands and their quantities
        for land_name, quantity in basic_lands.items():
            cursor.execute("""
                INSERT INTO deck_cards
                    (deck_id, card_name, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (
                deck_id,
                land_name,
                quantity,
                0.0
            ))

        connection.commit()
        return deck_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
