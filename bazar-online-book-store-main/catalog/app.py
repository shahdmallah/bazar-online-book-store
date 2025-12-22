from flask import Flask, jsonify, request
import csv, os, requests

app = Flask(__name__)

DATA_FILE = os.environ.get("CATALOG_FILE", "/data/catalog_data.csv")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend:5000")
CATALOG_REPLICA_NAME = os.environ.get("CATALOG_REPLICA_NAME", "catalog1")
CATALOG_PEER_URL = os.environ.get("CATALOG_PEER_URL")  
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))


def read_catalog():
    books = []
    if not os.path.exists(DATA_FILE):
        return books
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
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


def invalidate_cache(item_id: int):
    try:
        requests.post(
            f"{FRONTEND_URL}/invalidate",
            json={"id": item_id},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception:
        pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "component": "catalog", "replica": CATALOG_REPLICA_NAME}), 200


@app.route("/replicate_update", methods=["POST"])
def replicate_update():
    data = request.get_json(silent=True) or {}
    item_id = data.get("id")
    qty_delta = data.get("qty_delta")
    price = data.get("price")

    if item_id is None:
        return jsonify({"error": "missing id"}), 400

    books = read_catalog()
    updated = False

    for b in books:
        if b["id"] == int(item_id):
            if qty_delta is not None:
                new_qty = b["quantity"] + int(qty_delta)
                if new_qty < 0:
                    return jsonify({"error": "not enough stock"}), 400
                b["quantity"] = new_qty
            if price is not None:
                b["price"] = float(price)
            updated = True
            break

    if not updated:
        return jsonify({"error": "item not found"}), 404

    write_catalog(books)
    return jsonify({"status": "ok"}), 200


@app.route("/search/<topic>", methods=["GET"])
def search(topic):
    books = read_catalog()
    results = [{"id": b["id"], "title": b["title"]} for b in books if topic.lower() in b["topic"].lower()]
    return jsonify(results), 200


@app.route("/info/<int:item_id>", methods=["GET"])
def info(item_id):
    books = read_catalog()
    for b in books:
        if b["id"] == item_id:
            return jsonify(b), 200
    return jsonify({"error": "item not found"}), 404


@app.route("/update", methods=["PUT"])
def update():
    data = request.get_json(silent=True) or {}
    item_id = data.get("id")
    qty_delta = data.get("qty_delta")
    price = data.get("price")

    if item_id is None:
        return jsonify({"error": "missing id"}), 400
    item_id = int(item_id)


    invalidate_cache(item_id)

  
    books = read_catalog()
    updated = False
    result_row = None

    for b in books:
        if b["id"] == item_id:
            if qty_delta is not None:
                new_qty = b["quantity"] + int(qty_delta)
                if new_qty < 0:
                    return jsonify({"error": "not enough stock"}), 400
                b["quantity"] = new_qty
            if price is not None:
                b["price"] = float(price)
            updated = True
            result_row = b
            break

    if not updated:
        return jsonify({"error": "item not found"}), 404

    write_catalog(books)

  
    replicated = False
    if CATALOG_PEER_URL:
        try:
            pr = requests.post(
                f"{CATALOG_PEER_URL}/replicate_update",
                json={"id": item_id, "qty_delta": qty_delta, "price": price},
                timeout=REQUEST_TIMEOUT,
            )
            replicated = pr.status_code == 200
        except Exception:
            replicated = False

    return jsonify(
        {
            "id": item_id,
            "quantity": result_row["quantity"],
            "price": result_row["price"],
            "replicated_to_peer": replicated,
        }
    ), 200


if __name__ == "__main__":
    port = int(os.environ.get("CATALOG_PORT", "5001"))
    app.run(host="0.0.0.0", port=port, threaded=True)
