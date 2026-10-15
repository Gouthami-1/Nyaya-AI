# Legal data import

This project intentionally starts with an empty legal-provisions table. It does not seed guessed section numbers or pretend that a small sample is a complete legal database.

Import only provisions you have checked against an official source such as India Code (https://www.indiacode.nic.in/indiacode/home.jsp) or the Legislative Department (https://www.legislative.gov.in/). Each record should include an official source URL and a last-verified date. The app's search currently searches rows already in SQLite; it does not crawl the internet.

Columns in `legal_provisions`: `act_name` (required), `year`, `section` (required), `heading`, `legal_text`, `explanation`, `source_url` (required), `jurisdiction`, `applicability_notes`, `last_verified` (ISO date recommended), `keywords`.

Example import from a locally prepared CSV (after reviewing each row):

```powershell
python scripts\import_legal_csv.py path	oerified_provisions.csv
```
