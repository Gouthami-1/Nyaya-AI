# Nyaya AI — Phase 1 starter

A Flask-based Indian legal information assistant foundation with Gemini integration, local SQLite retrieval, browser speech input/output, and privacy-conscious defaults. This is a working starter, **not a complete legal database or a substitute for a lawyer**.

## Architecture

- Flask backend in `app.py`
- Gemini integration in `services/gemini_service.py` using the official `google-genai` SDK
- SQLite schema and chat persistence in `database/database.py`
- Retrieval of only locally imported, source-linked provisions in `services/legal_search.py`
- Browser speech recognition and speech synthesis in `static/js/voice.js`
- Chat UI and answer controls in `static/js/chat.js`

## Windows PowerShell setup

```powershell
cd path	o
yaya-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` to a key you obtain from Google AI Studio. Keep `.env` private and never commit it. Set a long random `FLASK_SECRET_KEY`. For local development, `STORE_HISTORY=false` is the default. With history disabled, the app does not persist chat messages, though the current request is sent to Gemini when you submit it.

Run the app:

```powershell
python app.py
```

Open http://127.0.0.1:5000. Microphone permission generally requires localhost or HTTPS. Browser speech recognition is not uniformly supported; text chat remains available.

## Legal database

The database initializes automatically on first run. The provisions table starts empty by design. Review `legal_data/README.md`. Use official sources such as [India Code](https://www.indiacode.nic.in/indiacode/home.jsp) and the [Legislative Department](https://www.legislative.gov.in/) to verify each provision before importing it. Do not use unverified scraped content. Create a CSV with the exact columns listed in `legal_data/README.md`, then run:

```powershell
python scripts\import_legal_csv.py path	oerified_provisions.csv
```

The app searches imported rows only. It does not claim exhaustive coverage or live legal research. A source URL is displayed for each retrieved provision. Always check amendments, commencement, state rules, and facts with a qualified lawyer.

## Tests

```powershell
python -m pytest -q
```

Tests use a temporary database and do not need a paid Gemini call. `test_legal_search.py` may require the Flask app context in some configurations; if it fails due to missing context, initialize a Flask test app before calling retrieval.

## Voice controls

- Click **Speak** to start a one-shot recording. Review the transcript in the input before submitting.
- Select English, Hindi, or Telugu before recording.
- Use Play, Pause, Resume, or Stop on an answer.
- Voice support depends on browser, installed voices, network, operating system, and selected language. The UI provides text alternatives.

## Security and privacy notes

- API key stays on the server.
- Chat persistence is disabled by default.
- The app has CSRF protection, input length limits, parameterized SQL, and safe DOM text rendering.
- For production, configure HTTPS, a strong secret, secure cookie flags, rate limiting, a production WSGI server, dependency updates, monitoring without logging legal content, and a privacy notice. Do not deploy Flask's development server publicly.
- Questions sent to Gemini may be processed by Google's service under its applicable terms. Do not submit unnecessary identifiers or sensitive documents. This is not lawyer-client privileged communication.
- Urgent danger requires contacting local emergency services. For free legal-aid information, see [NALSA](https://nalsa.gov.in/promoting-inclusive-legal-system/) (helpline 15100).

## Known phase-1 limitations

- No accounts; history is session-scoped and optional.
- The legal database is empty until you import verified records.
- Retrieval uses simple keyword matching, not semantic embeddings.
- Speech recognition support varies and voice conversation is user-initiated, not always-on.
- Further hardening and broader automated tests are planned for subsequent phases.
