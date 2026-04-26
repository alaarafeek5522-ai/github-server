from flask import Flask, jsonify, request
import datetime, os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="utf-8">
<title>GitHub Server</title>
<style>
body{background:#0d1117;color:#e6edf3;font-family:sans-serif;text-align:center;padding:50px}
h1{color:#58a6ff;font-size:2.5em}
.badge{background:#238636;padding:8px 20px;border-radius:20px;display:inline-block;margin:10px}
.url{background:#161b22;border:1px solid #30363d;padding:15px;border-radius:8px;margin:20px auto;max-width:500px;word-break:break-all}
</style>
</head>
<body>
<h1>🚀 GitHub Actions Server</h1>
<div class="badge">✅ Running</div>
<div class="badge">♾️ Auto-Renewing</div>
<p>الوقت: ''' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + '''</p>
</body>
</html>
'''

@app.route('/api/ping')
def ping():
    return jsonify({
        "status": "ok",
        "time": str(datetime.datetime.now()),
        "server": "GitHub Actions"
    })

@app.route('/api/echo', methods=['POST'])
def echo():
    data = request.get_json(force=True)
    return jsonify({"echo": data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
