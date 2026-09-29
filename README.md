# Jolley Search

A lightweight general-purpose web search interface built with Flask and designed for Render.

## Features
- Clean responsive search UI
- Web search results and snippets
- Pagination
- JSON `/api/search?q=` endpoint
- `/health` endpoint
- Render-ready deployment

## Search provider
Set `BRAVE_SEARCH_API_KEY` in your Render environment variables. The application uses the Brave Search API with standard content filtering.

## Local run
```bash
pip install -r requirements.txt
export BRAVE_SEARCH_API_KEY=your_key
python app.py
```

## Production
```bash
gunicorn app:app
```
