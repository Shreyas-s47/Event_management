import json
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "docs/contracts/member4.openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Exported {destination.name}")
