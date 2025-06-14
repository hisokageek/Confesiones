
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "¡Bot de ConfesionesUCLV está activo! 🤖"

@app.route('/status')
def status():
    return {"status": "active", "message": "Bot funcionando correctamente"}

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
