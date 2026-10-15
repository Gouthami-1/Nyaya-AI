
from flask import Flask, render_template, request, jsonify, session
from flask_wtf.csrf import CSRFProtect
from config import Config
from database.database import (
    init_db,
    search_provisions,
    save_message,
    get_history,
    delete_history,
)
from services.gemini_service import (
    answer_legal_question,
    GeminiServiceError,
)
from services.legal_search import retrieve_legal_sources
import secrets

app = Flask(__name__)
app.config.from_object(Config)
CSRFProtect(app)

with app.app_context():
    init_db()


@app.before_request
def ensure_session_id():
    session.setdefault(
        "conversation_id",
        secrets.token_urlsafe(18)
    )


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/history")
def history():
    if not app.config["STORE_HISTORY"]:
        return jsonify({"messages": []})

    return jsonify({
        "messages": get_history(session["conversation_id"])
    })


@app.delete("/api/history")
def clear_history():
    delete_history(session["conversation_id"])
    return jsonify({"ok": True})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}

    question = str(data.get("message", "")).strip()
    language = str(data.get("language", "English"))

    if not question:
        return jsonify({
            "error": "Please enter or dictate your legal question."
        }), 400

    if len(question) > app.config["MAX_QUESTION_LENGTH"]:
        return jsonify({
            "error": "Your question is too long. Please shorten it."
        }), 413

    if language not in {"English", "Hindi", "Telugu"}:
        language = "English"

    # Retrieve provisions from the existing legal search service.
    try:
        provisions = retrieve_legal_sources(question, limit=6)
    except Exception:
        app.logger.exception("Legal source retrieval failed")
        provisions = []

    history_messages = (
        get_history(session["conversation_id"])
        if app.config["STORE_HISTORY"]
        else []
    )

    try:
        answer = answer_legal_question(
            question,
            language,
            provisions,
            history_messages,
        )
    except GeminiServiceError as exc:
        app.logger.warning("Gemini request failed: %s", exc)
        return jsonify({
            "error": str(exc),
            "sources": provisions,
        }), 503

    if app.config["STORE_HISTORY"]:
        save_message(
            session["conversation_id"], "user", question
        )
        save_message(
            session["conversation_id"], "assistant", answer
        )

    return jsonify({
        "answer": answer,
        "sources": provisions,
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(
        debug=app.config["DEBUG"],
        host="127.0.0.1",
        port=5000,
    )
