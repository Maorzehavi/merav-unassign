from flask import Flask, request, jsonify
import requests, json, os

API_TOKEN = os.getenv("API_TOKEN", "")
MONDAY_API_URL = "https://api.monday.com/v2"

app = Flask(__name__)

def header():
    if not API_TOKEN:
        raise RuntimeError("API_TOKEN is missing. Set env var API_TOKEN.")
    return {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

def run_query(query, variables=None):
    r = requests.post(MONDAY_API_URL, headers=header(),
                      json={"query": query, "variables": variables or {}})
    r.raise_for_status()
    return r.json()

def is_empty(val):
    if val is None: return True
    if isinstance(val, str): return val.strip() == ""
    if isinstance(val, dict):
        txt = val.get("label", {}).get("text")
        if isinstance(txt, str): return txt.strip() == ""
        return len(val) == 0
    if isinstance(val, (list, tuple, set)): return len(val) == 0
    return False

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route('/unassign', methods=['POST'])
def webhook():
    data = request.get_json(force=True) or {}
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    # assign column can come via query (?assign_column=col_x) or body {"assign_column":"col_x"}
    assign_column_id = request.args.get("assign_column") or data.get("assign_column")
    if not assign_column_id:
        return jsonify({"error": "Missing assign_column"}), 400

    event = data.get("event", {})
    user_id  = event.get("userId")
    item_id  = event.get("pulseId")
    board_id = event.get("boardId")
    value    = event.get("value")

    # Monday may send 'value' as a JSON string; try to parse if so
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            pass

    if not (user_id and item_id and board_id):
        return jsonify({"status": "ignored", "reason": "missing ids"})

    # Assign if value present, unassign if empty
    column_value = {"personsAndTeams": []} if is_empty(value) else {
        "personsAndTeams": [{"id": user_id, "kind": "person"}]
    }

    mutation = """
      mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
        change_column_value(board_id:$boardId, item_id:$itemId, column_id:$columnId, value:$value){ id }
      }
    """
    vars_ = {
        "boardId": str(board_id),
        "itemId":  str(item_id),
        "columnId": assign_column_id,
        "value":   json.dumps(column_value)
    }

    try:
        res = run_query(mutation, vars_)
        return jsonify({"status": "ok", "result": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # 0.0.0.0 for Docker; publish with -p 5000:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
