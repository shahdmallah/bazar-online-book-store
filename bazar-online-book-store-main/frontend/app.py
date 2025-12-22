from flask import Flask, jsonify, request
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CATALOG_REPLICAS = [
    f"http://{os.environ.get('CATALOG1_HOST', 'catalog1')}:{os.environ.get('CATALOG1_PORT', '5001')}",
    f"http://{os.environ.get('CATALOG2_HOST', 'catalog2')}:{os.environ.get('CATALOG2_PORT', '5001')}",
]

ORDER_REPLICAS = [
    f"http://{os.environ.get('ORDER1_HOST', 'order1')}:{os.environ.get('ORDER1_PORT', '5002')}",
    f"http://{os.environ.get('ORDER2_HOST', 'order2')}:{os.environ.get('ORDER2_PORT', '5002')}",
]

REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))
CACHE_MAX_ITEMS = int(os.environ.get("CACHE_MAX_ITEMS", "200"))
USE_CACHE = os.environ.get("USE_CACHE", "1") == "1"

_rr_catalog = 0
_rr_order = 0

CACHE = {}

def pick_catalog():
    global _rr_catalog
    url = CATALOG_REPLICAS[_rr_catalog % len(CATALOG_REPLICAS)]
    _rr_catalog += 1
    return url

def pick_order():
    global _rr_order
    url = ORDER_REPLICAS[_rr_order % len(ORDER_REPLICAS)]
    _rr_order += 1
    return url

def cache_put(key, value):
    if len(CACHE) >= CACHE_MAX_ITEMS:
        CACHE.pop(next(iter(CACHE)))
    CACHE[key] = value

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "component": "front-end"}), 200

@app.route("/invalidate", methods=["POST"])
def invalidate():
    data = request.get_json(silent=True) or {}
    item_id = data.get("id")
    if item_id is None:
        return jsonify({"error": "missing id"}), 400
    k = f"info:{item_id}"
    deleted = 1 if k in CACHE else 0
    CACHE.pop(k, None)
    return jsonify({"status": "ok", "deleted": deleted}), 200

@app.route("/search/<path:topic>", methods=["GET"])
def search(topic):
    catalog_url = pick_catalog()
    try:
        r = requests.get(
            f"{catalog_url}/search/{requests.utils.requote_uri(topic)}",
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502
    try:
        payload = r.json()
    except ValueError:
        return jsonify({"error": "catalog returned invalid response"}), 502
    return jsonify(payload), r.status_code

@app.route("/info/<int:item_id>", methods=["GET"])
def info(item_id):
    cache_key = f"info:{item_id}"
    if USE_CACHE and cache_key in CACHE:
        logging.info("CACHE HIT %s", cache_key)
        return jsonify(CACHE[cache_key]), 200
    logging.info("CACHE MISS %s", cache_key)
    catalog_url = pick_catalog()
    try:
        r = requests.get(f"{catalog_url}/info/{item_id}", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        return jsonify({"error": "catalog unreachable", "detail": str(e)}), 502
    if r.status_code == 200:
        try:
            payload = r.json()
        except ValueError:
            return jsonify({"error": "catalog returned invalid response"}), 502
        if USE_CACHE:
            cache_put(cache_key, payload)
        return jsonify(payload), 200
    if r.status_code == 404:
        return jsonify({"error": "item not found"}), 404
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
    order_url = pick_order()
    try:
        r = requests.post(
            f"{order_url}/order",
            json={"id": item_id, "qty": qty},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        return jsonify({"error": "order service unreachable", "detail": str(e)}), 502
    try:
        payload = r.json()
    except ValueError:
        return jsonify({"error": "order returned invalid response"}), 502
    return jsonify(payload), r.status_code

@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "service": "bazar front-end",
            "endpoints": {
                "GET /search/<topic>": "proxy to catalog replicas",
                "GET /info/<id>": "cached, proxy to catalog replicas",
                "POST /purchase/<id>": "proxy to order replicas, body {qty}",
                "POST /invalidate": "used by replicas before writes, body {id}",
                "GET /health": "health",
            },
        }
    )

if __name__ == "__main__":
    port = int(os.environ.get("FRONTEND_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, threaded=True)
