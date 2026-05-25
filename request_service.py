from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)
db = {}

@app.route('/requests', methods=['POST'])
def create():
    data = request.json
    rid = str(uuid.uuid4())[:8]
    db[rid] = {'id': rid, 'weight': data.get('weight'), 'status': 'pending'}
    return jsonify(db[rid]), 201

@app.route('/requests', methods=['GET'])
def list_all():
    return jsonify(list(db.values()))

if __name__ == '__main__':
    app.run(port=5001)