from flask import Flask, jsonify, request
import csv, os, requests
from datetime import datetime

app = Flask(__name__)

CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog1:5001")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend:5000")

ORDER_REPLICA_NAME = os.environ.get("ORDER_REPLICA_NAME", "order1")
ORDER_PEER_URL = os.environ.get("ORDER_PEER_URL")  

ORDERS_FILE = os.environ.get("ORDERS_FILE", "/data/orders_log.csv")
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))


def read_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_order(order):
    os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
    file_exists = os.path.exists(ORDERS_FILE)
    with open(ORDERS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_id", "item_id", "title", "qty", "total_price", "timestamp"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(order)


def next_order_id():
    return len(read_orders()) + 1


def invalidate_cache(item_id: int):
    try:
        requests.post(f"{FRONTEND_URL}/invalidate", json={"id": item_id}, timeout=REQUEST_TIMEOUT)
    except Exception:
        pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "component": "order", "replica": ORDER_REPLICA_NAME}), 200


@app.route("/replicate_order", methods=["POST"])
def replicate_order():
    data = request.get_json(silent=True) or {}
    required = ["order_id", "item_id", "title", "qty", "total_price", "timestamp"]
    if any(k not in data for k in required):
        return jsonify({"error": "missing fields", "required": required}), 400

    append_order(
        {
            "order_id": data["order_id"],
            "item_id": data["item_id"],
            "title": data["title"],
            "qty": data["qty"],
            "total_price": data["total_price"],
            "timestamp": data["timestamp"],
        }
    )
    return jsonify({"status": "ok"}), 200


@app.route("/order", methods=["POST"])
def place_order():
    data = request.get_json(silent=True) or {}
    item_id = data.get("id")
    qty = data.get("qty")

    if item_id is None or qty is None:
        return jsonify({"error": "id and qty required"}), 400

    try:
        item_id = int(item_id)
        qty = int(qty)
    except (TypeError, ValueError):
        return jsonify({"error": "id and qty must be integers"}), 400
    if qty <= 0:
        return jsonify({"error": "qty must be >= 1"}), 400

   
    try:
        r = requests.get(f"{CATALOG_URL}/info/{item_id}", timeout=REQUEST_TIMEOUT)
    except Exception as e:
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502

    if r.status_code != 200:
        return jsonify({"error": "item not found"}), 404

    book = r.json()
    if int(book.get("quantity", 0)) < qty:
        return jsonify({"error": "not enough stock"}), 400

    invalidate_cache(item_id)

    try:
        r2 = requests.put(
            f"{CATALOG_URL}/update",
            json={"id": item_id, "qty_delta": -qty},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        return jsonify({"error": "catalog update unreachable", "detail": str(e)}), 502

    if r2.status_code != 200:
        return jsonify({"error": "catalog update failed", "detail": r2.text}), 400


    order_id = next_order_id()
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

    replicated = False
    if ORDER_PEER_URL:
        try:
            pr = requests.post(
                f"{ORDER_PEER_URL}/replicate_order",
                json=order_record,
                timeout=REQUEST_TIMEOUT,
            )
            replicated = pr.status_code == 200
        except Exception:
            replicated = False

    return jsonify({"status": "success", **order_record, "replicated_to_peer": replicated}), 200


@app.route("/orders", methods=["GET"])
def list_orders():
    return jsonify(read_orders()), 200


if __name__ == "__main__":
    port = int(os.environ.get("ORDER_PORT", "5002"))
    app.run(host="0.0.0.0", port=port, threaded=True)
