"""Generate a "Most Used Languages" SVG card from ALL repos you own (public + private).

Uses the GitHub languages API, which respects each repo's .gitattributes
(linguist-vendored / linguist-generated), so third-party code is not counted.

Env: GH_TOKEN  token able to read your private repos (Metadata: read is enough)
     OUT       output path (default dist/top-langs.svg)
"""
import base64
import fnmatch
import json
import os
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

TOKEN = os.environ["GH_TOKEN"]
OUT = os.environ.get("OUT", "dist/top-langs.svg")
LANGS_COUNT = 6
EXCLUDE_LANGS = {"Hack"}  # misdetected PHP templates

COLORS = {
    "Kotlin": "#A97BFF", "Java": "#b07219", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Go": "#00ADD8", "Python": "#3572A5",
    "Shell": "#89e051", "CSS": "#663399", "HTML": "#e34c26", "PHP": "#4F5D95",
    "Dart": "#00B4AB", "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Lua": "#000080", "Luau": "#00A2FF", "Rust": "#dea584",
}


def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "top-langs-card",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


EXT_LANG = {
    ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript", ".css": "CSS",
    ".html": "HTML", ".java": "Java", ".kt": "Kotlin", ".py": "Python", ".go": "Go",
    ".php": "PHP", ".sh": "Shell",
}


def vendored_bytes(repo):
    """Bytes per language of files marked linguist-vendored/-generated in .gitattributes.

    GitHub can take hours to re-run linguist after .gitattributes changes, so we
    subtract these files ourselves (only while GitHub still counts them).
    """
    try:
        raw = api(repo["url"] + "/contents/.gitattributes")
    except urllib.error.HTTPError:
        return {}
    text = base64.b64decode(raw["content"]).decode("utf-8", "replace")
    patterns = [
        line.split()[0] for line in text.splitlines()
        if line.strip() and not line.startswith("#")
        and ("linguist-vendored" in line or "linguist-generated" in line)
        and "=false" not in line
    ]
    if not patterns:
        return {}
    tree = api(f'{repo["url"]}/git/trees/{repo["default_branch"]}?recursive=1')["tree"]
    out = {}
    for item in tree:
        if item["type"] != "blob":
            continue
        if any(fnmatch.fnmatch(item["path"], p.lstrip("/")) or fnmatch.fnmatch(item["path"], "*/" + p)
               for p in patterns):
            lang = EXT_LANG.get(os.path.splitext(item["path"])[1].lower())
            if lang:
                out[lang] = out.get(lang, 0) + item["size"]
    return out


def collect():
    totals, page = {}, 1
    while True:
        repos = api(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo["fork"]:
                continue
            langs = api(repo["languages_url"])
            for lang, size in vendored_bytes(repo).items():
                if langs.get(lang, 0) >= size:  # GitHub hasn't excluded it yet
                    langs[lang] -= size
            for lang, size in langs.items():
                if lang not in EXCLUDE_LANGS and size > 0:
                    totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals


def render(totals):
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LANGS_COUNT]
    total = sum(v for _, v in top) or 1
    width, bar_w = 320, 270

    bar, x = [], 0.0
    for lang, size in top:
        w = bar_w * size / total
        bar.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{COLORS.get(lang, "#858585")}"/>')
        x += w

    items = []
    for i, (lang, size) in enumerate(top):
        col, row = i % 2, i // 2
        tx, ty = col * 140, row * 25
        items.append(
            f'<g transform="translate({tx},{ty})">'
            f'<circle cx="5" cy="6" r="5" fill="{COLORS.get(lang, "#858585")}"/>'
            f'<text x="15" y="10" class="lang">{escape(lang)} {100 * size / total:.2f}%</text></g>'
        )

    rows = (len(top) + 1) // 2
    height = 90 + rows * 25
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t">
<title id="t">Most Used Languages</title>
<style>
.title {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #ff6e96; }}
.lang {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #f8f8f2; }}
</style>
<rect x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}" fill="#282a36" stroke="#e4e2e2"/>
<text x="25" y="35" class="title">Most Used Languages</text>
<mask id="m"><rect x="0" y="0" width="{bar_w}" height="8" rx="5" fill="white"/></mask>
<g transform="translate(25,55)"><g mask="url(#m)">{"".join(bar)}</g></g>
<g transform="translate(25,80)">{"".join(items)}</g>
</svg>
'''


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    totals = collect()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(totals))
    print(json.dumps(dict(sorted(totals.items(), key=lambda kv: -kv[1])), indent=1))
