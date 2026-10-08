
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


BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}


def list_saved_decks():
    """Return saved decks newest first, including their card counts."""
    with sqlite3.connect(DATABASE) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
            SELECT d.id, d.commander_name, d.budget, d.created_at,
                   1 + COALESCE(SUM(c.quantity), 0) AS card_count
            FROM decks AS d
            LEFT JOIN deck_cards AS c ON c.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.id DESC
        """).fetchall()
        return [dict(row) for row in rows]


def load_saved_deck(deck_id):
    """Return a deck and its cards, or None if it does not exist."""
    with sqlite3.connect(DATABASE) as connection:
        connection.row_factory = sqlite3.Row
        record = connection.execute(
            "SELECT * FROM decks WHERE id = ?", (deck_id,)
        ).fetchone()
        if record is None:
            return None
        cards = connection.execute(
            "SELECT card_name, quantity, price FROM deck_cards WHERE deck_id = ? ORDER BY id",
            (deck_id,)
        ).fetchall()
    deck = []
    basic_lands = {}
    for card in cards:
        if card["card_name"] in BASIC_LAND_NAMES:
            basic_lands[card["card_name"]] = basic_lands.get(card["card_name"], 0) + card["quantity"]
        else:
            deck.extend({"name": card["card_name"], "price": card["price"]} for _ in range(card["quantity"]))
    return {**dict(record), "deck": deck, "basic_lands": basic_lands}


def update_saved_deck(deck_id, commander_name, commander_price, budget, deck, basic_lands):
    """Overwrite an existing saved deck atomically. Return False if missing."""
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        exists = connection.execute("SELECT 1 FROM decks WHERE id = ?", (deck_id,)).fetchone()
        if not exists:
            return False
        connection.execute("""
            UPDATE decks SET commander_name = ?, commander_price = ?, budget = ? WHERE id = ?
        """, (commander_name, commander_price, budget, deck_id))
        connection.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
        rows = [(deck_id, c["name"], 1, c["price"]) for c in deck]
        rows.extend((deck_id, name, qty, 0.0) for name, qty in basic_lands.items())
        connection.executemany("""
            INSERT INTO deck_cards (deck_id, card_name, quantity, price) VALUES (?, ?, ?, ?)
        """, rows)
    return True


def delete_saved_deck(deck_id):
    """Delete a saved deck and all its card rows."""
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
        result = connection.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        return result.rowcount > 0


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
