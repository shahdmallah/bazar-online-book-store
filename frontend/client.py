import requests
import json

FRONTEND_HOST = "localhost"
FRONTEND_PORT = 5000
BASE_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"


def pretty_print(obj):
    print(json.dumps(obj, indent=4))


def do_search():
    topic = input("Enter topic: ").strip()
    try:
        r = requests.get(f"{BASE_URL}/search/{topic}")
        if r.status_code == 200:
            print("\n--- Search Results ---")
            pretty_print(r.json())
        else:
            print("Error:", r.json())
    except Exception as e:
        print("Connection error:", e)


def do_info():
    try:
        item_id = int(input("Enter item id: ").strip())
    except:
        print("Invalid number")
        return

    try:
        r = requests.get(f"{BASE_URL}/info/{item_id}")
        if r.status_code == 200:
            print("\n--- Book Info ---")
            pretty_print(r.json())
        else:
            print("Error:", r.json())
    except Exception as e:
        print("Connection error:", e)


def do_purchase():
    try:
        item_id = int(input("Enter item id to buy: ").strip())
    except:
        print("Invalid number")
        return

    qty_input = input("Enter quantity (default 1): ").strip()
    qty = int(qty_input) if qty_input else 1

    try:
        r = requests.post(
            f"{BASE_URL}/purchase/{item_id}",
            json={"qty": qty}
        )

        data = r.json()

        if r.status_code == 200:
            print(f"\nBought book: {data.get('title')}")
            print("--- Order Details ---")
            pretty_print(data)
        else:
            print("Purchase failed:")
            pretty_print(data)

    except Exception as e:
        print("Connection error:", e)


def main():
    print("\n=== Bazar.com Client ===")
    print(f"Connected to front-end at {BASE_URL}\n")

    while True:
        print("1. Search by topic")
        print("2. Get book info")
        print("3. Purchase a book")
        print("4. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            do_search()
        elif choice == "2":
            do_info()
        elif choice == "3":
            do_purchase()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.\n")

        print("\n-----------------------------\n")


if __name__ == "__main__":
    main()
