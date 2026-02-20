"""Serper.dev web search — plain function replacement for SerperDevTool."""

from __future__ import annotations

import json
import os

import requests


def serper_search(query: str, num_results: int = 10) -> str:
    """Search the web using Serper.dev API.

    Args:
        query: The search query string.
        num_results: Number of results to return (default 10).

    Returns:
        Formatted search results as a string.
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return "Error: SERPER_API_KEY not set"

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": num_results},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"Search error: {e}"

    # Format results
    results = []

    # Knowledge graph
    if "knowledgeGraph" in data:
        kg = data["knowledgeGraph"]
        results.append(f"Knowledge Graph: {kg.get('title', '')} — {kg.get('description', '')}")

    # Organic results
    for i, item in enumerate(data.get("organic", [])[:num_results], 1):
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        results.append(f"{i}. [{title}]({link})\n   {snippet}")

    # People Also Ask
    paa = data.get("peopleAlsoAsk", [])
    if paa:
        results.append("\nPeople Also Ask:")
        for q in paa[:5]:
            results.append(f"  - {q.get('question', '')}")

    # Related searches
    related = data.get("relatedSearches", [])
    if related:
        results.append("\nRelated Searches:")
        for r in related[:5]:
            results.append(f"  - {r.get('query', '')}")

    return "\n".join(results) if results else "No results found."
