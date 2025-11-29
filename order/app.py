from flask import Flask, jsonify, request
import csv, os, requests
from datetime import datetime

# Catalog service connection
CATALOG_HOST = os.environ.get("CATALOG_HOST", "catalog")
CATALOG_PORT = os.environ.get("CATALOG_PORT", "5001")
CATALOG_URL = f"http://{CATALOG_HOST}:{CATALOG_PORT}"

# Orders storage file
ORDERS_FILE = os.environ.get("ORDERS_FILE", "/data/orders_log.csv")

app = Flask(__name__)



def read_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def append_order(order):
    os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
    file_exists = os.path.exists(ORDERS_FILE)
    with open(ORDERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_id", "item_id", "title", "qty", "total_price", "timestamp"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(order)

@app.route("/order", methods=["POST"])
def place_order():
    data = request.get_json() or {}

    item_id = data.get("id")
    qty = data.get("qty")

    if item_id is None or qty is None:
        return jsonify({"error": "id and qty required"}), 400

    qty = int(qty)

    # Step 1: Fetch book info from catalog
    try:
        r = requests.get(f"{CATALOG_URL}/info/{item_id}", timeout=5)
    except Exception as e:
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502

    if r.status_code != 200:
        return jsonify({"error": "item not found"}), 404

    book = r.json()

    if book["quantity"] < qty:
        return jsonify({"error": "not enough stock"}), 400

    # Step 2: Update stock in catalog
    update_payload = {
        "id": item_id,
        "qty_delta": -qty
    }
    r2 = requests.put(f"{CATALOG_URL}/update", json=update_payload)

    if r2.status_code != 200:
        return jsonify({"error": "catalog update failed"}), 400

    # Step 3: Save the order in CSV
    orders = read_orders()
    order_id = len(orders) + 1

    total_price = float(book["price"]) * qty

    order_record = {
        "order_id": order_id,
        "item_id": item_id,
        "title": book["title"],
        "qty": qty,
        "total_price": total_price,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    append_order(order_record)

    return jsonify({
        "status": "success",
        "order_id": order_id,
        "item_id": item_id,
        "title": book["title"],
        "qty": qty,
        "total_price": total_price
    }), 200



@app.route("/orders", methods=["GET"])
def list_orders():
    return jsonify(read_orders())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
