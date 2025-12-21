from flask import Flask, jsonify, request
import os
import requests
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CATALOG_HOST = os.environ.get("CATALOG_HOST", "catalog")
CATALOG_PORT = os.environ.get("CATALOG_PORT", "5001")
ORDER_HOST = os.environ.get("ORDER_HOST", "order")
ORDER_PORT = os.environ.get("ORDER_PORT", "5002")

CATALOG_URL = f"http://{CATALOG_HOST}:{CATALOG_PORT}"
ORDER_URL = f"http://{ORDER_HOST}:{ORDER_PORT}"

REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))

@app.route("/health", methods=["GET"])
def health():

    return jsonify({"status": "ok", "component": "front-end"}), 200

@app.route("/search/<path:topic>", methods=["GET"])
def search(topic):
  
    logging.info("Received search request for topic: %s", topic)
    try:
        r = requests.get(f"{CATALOG_URL}/search/{requests.utils.requote_uri(topic)}", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logging.error("Catalog unreachable for search: %s", e)
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502

    try:
        payload = r.json()
    except ValueError:
        logging.error("Catalog returned non-json for search")
        return jsonify({"error": "catalog returned invalid response"}), 502

    return jsonify(payload), r.status_code


@app.route("/info/<int:item_id>", methods=["GET"])
def info(item_id):

    logging.info("Received info request for id: %d", item_id)
    try:
        r = requests.get(f"{CATALOG_URL}/info/{item_id}", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logging.error("Catalog unreachable for info: %s", e)
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502

    if r.status_code == 200:
        try:
            return jsonify(r.json()), 200
        except ValueError:
            logging.error("Catalog returned non-json for info")
            return jsonify({"error": "catalog returned invalid response"}), 502
    elif r.status_code == 404:
        return jsonify({"error": "item not found"}), 404
    else:
        return jsonify({"error": "catalog error", "status_code": r.status_code}), 502


@app.route("/purchase/<int:item_id>", methods=["POST"])
def purchase(item_id):

    data = request.get_json(silent=True) or {}
    qty = data.get("qty", 1)

    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return jsonify({"error": "qty must be an integer"}), 400

    if qty <= 0:
        return jsonify({"error": "qty must be >= 1"}), 400

    logging.info("Purchase request: id=%d qty=%d", item_id, qty)

    order_payload = {"id": item_id, "qty": qty}

    try:
        r = requests.post(f"{ORDER_URL}/order", json=order_payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logging.error("Order service unreachable: %s", e)
        return jsonify({"error": "order service unreachable", "detail": str(e)}), 502

    try:
        resp_json = r.json()
    except ValueError:
        logging.error("Order service returned non-json")
        return jsonify({"error": "order service returned invalid response"}), 502

    if r.status_code == 200:
        logging.info("Order placed: %s", resp_json)
        return jsonify(resp_json), 200
    else:
        return jsonify({"error": "order failed", "detail": resp_json}), r.status_code


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "bazar front-end",
        "endpoints": {
            "GET /search/<topic>": "search books by topic (proxy to catalog)",
            "GET /info/<item_id>": "get info for item id (proxy to catalog)",
            "POST /purchase/<item_id>": "purchase item id, JSON body: {\"qty\":<int>} (defaults to 1)",
            "GET /health": "health check"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("FRONTEND_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
