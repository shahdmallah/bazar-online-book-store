from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Frontend is working!"

if __name__ == "__main__":
    # Listen on all interfaces so Docker can access it
    app.run(host="0.0.0.0", port=5000)
