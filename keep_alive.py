from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Hogwarts Bot está activo y funcionando! ⚡"

@app.route('/status')
def status():
    return {
        "bot_status": "active",
        "platform": "Render",
        "message": "Dumbledore's magic is working!"
    }

def run():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print(f"🌐 Keep-alive server started on port {os.environ.get('PORT', 5000)}")