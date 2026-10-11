#!/usr/bin/env python3
"""
Builds modules/book_catalog.json: every book with lessons and every downloadable program, in one small file, for
"Explore books with {AI app}" in Pulse (the AI app reads it from the request's catalogUrl).

Re-run after changing modules/index.json, a collection, a book's info file, or modules/programs_index.json:
    python3 scripts/build_book_catalog.py
"""
import json
import os
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def clip(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def main():
    books = {}
    authors = {}

    programs = []
    for p in load("programs_index.json"):
        data = load(p["file"])
        steps = []
        for m in data.get(str(p["id"]), []):
            for b in m.get("books", []):
                if b.get("author"):
                    authors[b["id"]] = b["author"]
            steps.append({"title": m["title"], "goal": clip(m.get("goal"), 200), "books": [b["id"] for b in m.get("books", [])]})
        programs.append({"id": p["id"], "name": p["name"], "description": clip(p.get("description"), 300), "steps": steps})

    for c in load("index.json"):
        base = os.path.dirname(c["file"])
        for b in load(c["file"]).get("books", []):
            plan = b.get("studyPlan") or {}
            if not (plan.get("module_path") and plan.get("lesson_path")):
                continue
            if b["id"] in books:
                books[b["id"]]["collections"].append(c["name"])
                continue
            info = {}
            if b.get("info"):
                try:
                    info = load(os.path.join(base, b["info"]))
                except (OSError, ValueError):
                    info = {}
            entry = {
                "id": b["id"],
                "title": b.get("title") or info.get("title"),
                "about": clip(info.get("description"), 400),
                "skills": [s["title"] for s in info.get("keyStrategies", [])][:8],
                "collections": [c["name"]],
            }
            if authors.get(b["id"]):
                entry["author"] = authors[b["id"]]
            books[b["id"]] = entry

    # Books a program uses that no collection lists: they come with the app (lessons included), so describe them from
    # the program's own entry
    for p in programs:
        data = load(next(x["file"] for x in load("programs_index.json") if x["id"] == p["id"]))
        for m in data.get(str(p["id"]), []):
            for b in m.get("books", []):
                if b["id"] not in books:
                    books[b["id"]] = {
                        "id": b["id"],
                        "title": b.get("title"),
                        "about": clip(b.get("summary"), 400),
                        "skills": [],
                        "collections": [],
                        **({"author": b["author"]} if b.get("author") else {}),
                    }

    catalog = {
        "format": "pulse.bookCatalog",
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Books Pulse has lessons for, and programs (curated paths through books) it can download. Use the ids as they are.",
        "books": sorted(books.values(), key=lambda b: b["id"]),
        "programs": programs,
    }
    out = os.path.join(ROOT, "book_catalog.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{len(catalog['books'])} books, {len(programs)} programs → modules/book_catalog.json ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
