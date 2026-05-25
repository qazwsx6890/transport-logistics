from flask import Flask, request, jsonify
from orchestrator import TransportOrchestrator
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)  # разрешаем запросы с фронтенда

orchestrator = TransportOrchestrator()

@app.route('/api/start-order', methods=['POST'])
def start_order():
    data = request.json
    weight = data.get('cargo_weight_kg')
    pickup = data.get('pickup_address')
    delivery = data.get('delivery_address')
    
    result = orchestrator.create_transport_request(weight, pickup, delivery)
    return jsonify(result), 200 if result else 500

if __name__ == '__main__':
    app.run(port=5003, debug=True)