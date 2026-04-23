import requests

def query_web_search(message: str) -> str:
    """Uses DuckDuckGo instant answer API — no key needed."""
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": message,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            },
            timeout=5
        )
        data = response.json()

        results = []

        if data.get("AbstractText"):
            results.append(data["AbstractText"])

        for topic in data.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        if not results:
            return "No web results found."

        return "\n\n".join(results)

    except Exception as e:
        return f"Web search failed: {str(e)}"