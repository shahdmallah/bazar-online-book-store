import csv, os

DATA_FILE = os.environ.get("CATALOG_FILE", "/data/catalog_data.csv")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

if os.path.exists(DATA_FILE):
    print(f"ℹ️ Catalog already exists at {DATA_FILE}, skipping init")
    raise SystemExit(0)

books = [
    # Lab 1
    {"id": 1, "title": "How to get a good grade in DOS in 40 minutes a day", "topic": "distributed systems", "quantity": 5, "price": 40.0},
    {"id": 2, "title": "RPCs for Noobs", "topic": "distributed systems", "quantity": 5, "price": 50.0},
    {"id": 3, "title": "Xen and the Art of Surviving Undergraduate School", "topic": "undergraduate school", "quantity": 5, "price": 30.0},
    {"id": 4, "title": "Cooking for the Impatient Undergrad", "topic": "undergraduate school", "quantity": 5, "price": 25.0},

    #Lab 2
    {"id": 5, "title": "How to finish Project 3 on time", "topic": "distributed systems", "quantity": 5, "price": 45.0},
    {"id": 6, "title": "Why theory classes are so hard", "topic": "undergraduate school", "quantity": 5, "price": 35.0},
    {"id": 7, "title": "Spring in the Pioneer Valley", "topic": "general interest", "quantity": 5, "price": 20.0},
]

with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "title", "topic", "quantity", "price"])
    writer.writeheader()
    writer.writerows(books)

print(f"✅ Catalog CSV initialized at {DATA_FILE}")
