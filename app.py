import logging
import os
from urllib.parse import quote_plus

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jolley-search")

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def brave_search(query: str, page: int = 1):
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        logger.error("Brave search failed: BRAVE_SEARCH_API_KEY is missing")
        return [], "Search provider is not configured yet. Add BRAVE_SEARCH_API_KEY on Render."

    count = 10
    offset = max(0, page - 1) * count
    try:
        response = requests.get(
            BRAVE_ENDPOINT,
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            params={
                "q": query,
                "count": count,
                "offset": offset,
                "safesearch": "moderate",
                "text_decorations": False,
                "spellcheck": True,
            },
            timeout=12,
        )
        if not response.ok:
            # Deliberately never log request headers or the API key.
            body = (response.text or "").replace("\n", " ")[:1000]
            logger.error("Brave API HTTP %s response=%s", response.status_code, body)
            return [], f"Search provider returned HTTP {response.status_code}."
        data = response.json()
    except requests.Timeout:
        logger.exception("Brave API request timed out")
        return [], "The search provider timed out."
    except requests.RequestException as exc:
        logger.error("Brave API network error type=%s message=%s", type(exc).__name__, str(exc)[:500])
        return [], "The search provider is temporarily unavailable."
    except ValueError as exc:
        logger.error("Brave API returned invalid JSON: %s", str(exc)[:500])
        return [], "The search provider returned an invalid response."

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title") or item.get("url", "Result"),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "profile": item.get("profile", {}),
        })
    logger.info("Brave search succeeded result_count=%s page=%s", len(results), page)
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
    results, error = brave_search(q, page)
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
    results, error = brave_search(q, page)
    return jsonify({"ok": error is None, "query": q, "page": page, "results": results, "error": error})


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "Jolley Search"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
