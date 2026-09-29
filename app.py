import os
from urllib.parse import quote_plus

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def brave_search(query: str, page: int = 1):
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
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
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return [], "The search provider is temporarily unavailable."

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title") or item.get("url", "Result"),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "profile": item.get("profile", {}),
        })
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
