from flask import Flask, render_template, request, jsonify, Response
from filler_service import fill_google_form
import asyncio
import queue
import json

log_queue = queue.Queue()

def log_to_queue(msg_type, content):
    log_queue.put({"type": msg_type, "content": content})

app = Flask(__name__)

@app.route('/api/stream')
def stream():
    def event_stream():
        while True:
            msg = log_queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fill-form", methods=["POST"])
def fill_form():
    data = request.json
    url = data.get("url")
    email = data.get("email", "")
    
    if not url:
        return jsonify({"success": False, "message": "URL is required"}), 400
        
    if not url.startswith("http"):
        url = "https://" + url

    if "docs.google.com/forms" not in url and "forms.gle" not in url:
        return jsonify({"success": False, "message": "Invalid Google Form URL"}), 400
        
    try:
        # Run async function in synchronous wrapper
        user_keys = data.get("user_keys", {})
        result = asyncio.run(fill_google_form(url, email, data.get("manual_answers", {}), log_to_queue, user_keys=user_keys))
        log_to_queue("done", result)
        return jsonify(result)
    except Exception as e:
        log_to_queue("error", str(e))
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/parse-form", methods=["POST"])
def parse_form():
    data = request.json
    url = data.get("url")
    
    if not url:
        return jsonify({"success": False, "message": "URL is required"}), 400
        
    if not url.startswith("http"):
        url = "https://" + url

    if "docs.google.com/forms" not in url and "forms.gle" not in url:
        return jsonify({"success": False, "message": "Invalid Google Form URL"}), 400
        
    try:
        from filler_service import parse_google_form
        user_keys = data.get("user_keys", {})
        result = asyncio.run(parse_google_form(url, user_keys=user_keys))
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
