from flask import Flask, jsonify, request
import csv, os

# Location of the CSV file inside the container volume
DATA_FILE = os.environ.get("CATALOG_FILE", "/data/catalog_data.csv")

app = Flask(__name__)

# -------------------------------
# Utility Functions
# -------------------------------
def read_catalog():
    books = []
    if not os.path.exists(DATA_FILE):
        return books

    with open(DATA_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["id"] = int(row["id"])
            row["quantity"] = int(row["quantity"])
            row["price"] = float(row["price"])
            books.append(row)
    return books


def write_catalog(books):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "topic", "quantity", "price"])
        writer.writeheader()
        writer.writerows(books)


# -------------------------------
# API Endpoints
# -------------------------------

# RETURN ALL BOOKS
@app.route("/books", methods=["GET"])
def get_books():
    books = read_catalog()
    return jsonify(books)


# SEARCH BY TOPIC
@app.route("/search/<topic>", methods=["GET"])
def search(topic):
    books = read_catalog()
    results = [
        {"id": b["id"], "title": b["title"]}
        for b in books if topic.lower() in b["topic"].lower()
    ]
    return jsonify(results)


# BOOK INFO BY ID
@app.route("/info/<int:item_id>", methods=["GET"])
def info(item_id):
    books = read_catalog()
    for b in books:
        if b["id"] == item_id:
            return jsonify(b)
    return jsonify({"error": "item not found"}), 404


# UPDATE QUANTITY OR PRICE
@app.route("/update", methods=["PUT"])
def update():
    data = request.get_json() or {}

    item_id = data.get("id")
    qty_delta = data.get("qty_delta")
    price = data.get("price")

    if item_id is None:
        return jsonify({"error": "missing id"}), 400

    books = read_catalog()
    updated = False

    for b in books:
        if b["id"] == int(item_id):

            # Update quantity
            if qty_delta is not None:
                new_qty = b["quantity"] + int(qty_delta)
                if new_qty < 0:
                    return jsonify({"error": "not enough stock"}), 400
                b["quantity"] = new_qty

            # Update price
            if price is not None:
                b["price"] = float(price)

            updated = True
            break

    if not updated:
        return jsonify({"error": "item not found"}), 404

    write_catalog(books)

    return jsonify({
        "id": item_id,
        "quantity": b["quantity"],
        "price": b["price"]
    })


# -------------------------------
# Run the service
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
