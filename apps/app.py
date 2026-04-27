from flask import Flask, jsonify, request
import requests
import datetime

app = Flask(__name__)

API_NAME = "API Developer Alaa"
VERSION = "1.0.0"

@app.route('/')
def home():
    return jsonify({
        "api": API_NAME,
        "version": VERSION,
        "status": "ok",
        "time": str(datetime.datetime.now()),
        "endpoints": [
            "GET /api/drug/search?name=اسم_الدواء",
            "GET /api/status"
        ]
    })

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "api": API_NAME})

@app.route('/api/drug/search')
def drug_search():
    name = request.args.get('name', '')
    if not name:
        return jsonify({"code": 400, "error": True, "message": "اكتب اسم الدواء"}), 400
    try:
        res = requests.get(
            "http://moelshafey.top/API/MD/search.php",
            params={'name': name},
            headers={'User-Agent': 'Dart/3.7 (dart:io)', 'Accept-Encoding': 'gzip'},
            timeout=10
        )
        data = res.json()
        if data.get("code") == 200 and not data.get("error"):
            return jsonify({
                "code": 200,
                "error": False,
                "api": API_NAME,
                "count": len(data.get("products", [])),
                "products": data.get("products", [])
            })
        return jsonify({"code": 500, "error": True, "message": "خطأ في المصدر"})
    except Exception as e:
        return jsonify({"code": 500, "error": True, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
