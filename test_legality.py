
from unittest.mock import patch
from legality import validate_deck


def mock_card(name):
    return {
        "name": name,
        "color_identity": (
            ["R"] if name == "Lightning Bolt"
            else ["W", "U", "B", "G"]
        ),
        "legal": True,
        "type_line": (
            "Legendary Creature"
            if name == "Atraxa, Praetors' Voice"
            else "Instant"
        ),
        "oracle_text": "",
        "keywords": [],
        "layout": "normal"
    }


with patch("legality.lookup_card", side_effect=mock_card):
    result = validate_deck(
        "Atraxa, Praetors' Voice",
        [{"name": "Lightning Bolt", "price": 0.50}],
        {"Plains": 98}
    )

print("Legality Status:", result["status"])
print("Issues:", result["issues"])
