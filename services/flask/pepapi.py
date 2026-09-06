# mock_service.py
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.post("/v1/optimizer/optimization")
def optimize():
    payload = request.get_json()
    print("Received:", payload)

    return jsonify({
        "optimizationResponse": {
            "requestId": "mock-request-001",
            "sessionId": "mock-session-001",
            "status": {"code": "SUCCESS", "desc": "Mock optimization completed"},
            "tradeSummary": {
                "turnover": 0.0,
                "tradesValue": 0.0,
                "nBuys": 0,
                "nSells": 0,
                "amtBuys": 0.0,
                "amtSells": 0.0,
                "buyTransCost": 0.0,
                "sellTransCost": 0.0,
            },
            "trades": [],
        }
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)