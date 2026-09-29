import logging
import os
from urllib.parse import quote_plus

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jolley-search")

SERPER_ENDPOINT = "https://google.serper.dev/search"


def web_search(query: str, page: int = 1):
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        logger.error("Serper search failed: SERPER_API_KEY is missing")
        return [], "Search provider is not configured yet."

    payload = {"q": query, "page": page, "num": 10}
    try:
        response = requests.post(
            SERPER_ENDPOINT,
            headers={
                "X-API-KEY": key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=12,
        )
        if not response.ok:
            body = (response.text or "").replace("\n", " ")[:1000]
            logger.error("Serper API HTTP %s response=%s", response.status_code, body)
            return [], f"Search provider returned HTTP {response.status_code}."
        data = response.json()
    except requests.Timeout:
        logger.exception("Serper API request timed out")
        return [], "The search provider timed out."
    except requests.RequestException as exc:
        logger.error("Serper API network error type=%s message=%s", type(exc).__name__, str(exc)[:500])
        return [], "The search provider is temporarily unavailable."
    except ValueError as exc:
        logger.error("Serper API returned invalid JSON: %s", str(exc)[:500])
        return [], "The search provider returned an invalid response."

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title") or item.get("link", "Result"),
            "url": item.get("link", ""),
            "description": item.get("snippet", ""),
            "profile": {},
        })
    logger.info("Serper search succeeded result_count=%s page=%s", len(results), page)
    return results, None


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/search")
def search():
    q = request.args.get("q", "").strip()[:300]
    try:
        page = max(1, min(int(request.args.get("page", "1")), 20))
    except ValueError:
        page = 1
    if not q:
        return render_template("index.html")
    results, error = web_search(q, page)
    return render_template("results.html", q=q, results=results, error=error, page=page, encoded_q=quote_plus(q))


@app.get("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:300]
    if not q:
        return jsonify({"ok": False, "error": "q is required", "results": []}), 400
    try:
        page = max(1, min(int(request.args.get("page", "1")), 20))
    except ValueError:
        page = 1
    results, error = web_search(q, page)
    return jsonify({"ok": error is None, "provider": "serper", "query": q, "page": page, "results": results, "error": error})


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "Jolley Search", "provider": "serper"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
