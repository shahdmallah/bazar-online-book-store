# order/app.py
from flask import Flask, jsonify, request
import csv, os, requests
from datetime import datetime

CATALOG_HOST = os.environ.get("CATALOG_HOST", "catalog")
CATALOG_PORT = os.environ.get("CATALOG_PORT", "5001")
CATALOG_URL = f"http://{CATALOG_HOST}:{CATALOG_PORT}"

ORDERS_FILE = os.environ.get("ORDERS_FILE", "/data/orders_log.csv")

app = Flask(__name__)

def read_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def append_order(order):
    os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
    file_exists = os.path.exists(ORDERS_FILE)
    with open(ORDERS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['order_id','item_id','title','price','status','timestamp'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(order)

@app.route("/purchase/<int:item_id>", methods=["POST"])
def purchase(item_id):
    # Step 1: get book info
    try:
        r = requests.get(f"{CATALOG_URL}/info/{item_id}", timeout=5)
    except Exception as e:
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502

    if r.status_code != 200:
        return jsonify({"error": "book not found"}), 404

    info = r.json()
    if info.get("quantity", 0) <= 0:
        return jsonify({"status": "failed", "reason": "out of stock"}), 400

    # Step 2: request catalog to decrement stock
    update_payload = {"id": item_id, "qty_delta": -1}
    upd = requests.put(f"{CATALOG_URL}/update", json=update_payload)
    if upd.status_code != 200:
        return jsonify({"status": "failed", "reason": "update failed"}), 400

    # Step 3: log order
    orders = read_orders()
    order_id = len(orders) + 1
    order = {
        "order_id": order_id,
        "item_id": item_id,
        "title": info["title"],
        "price": info["price"],
        "status": "completed",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    append_order(order)
    return jsonify({"status": "success", "item": info["title"], "order_id": order_id})

@app.route("/orders", methods=["GET"])
def list_orders():
    return jsonify(read_orders())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
