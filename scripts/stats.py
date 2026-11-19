"""Generate a GitHub stats SVG card counting ALL repos you own (public + private).

Env: GH_TOKEN  token able to read your private repos (Metadata + Contents: read)
     OUT       output path (default dist/stats.svg)
"""
import json
import os
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

TOKEN = os.environ["GH_TOKEN"]
OUT = os.environ.get("OUT", "dist/stats.svg")


def api(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "stats-card",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def owned_repos():
    repos, page = [], 1
    while True:
        batch = api(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}")
        if not batch:
            return repos
        repos += [r for r in batch if not r["fork"]]
        page += 1


def count_commits(repo, login):
    total, page = 0, 1
    while True:
        try:
            batch = api(f'{repo["url"]}/commits?author={login}&per_page=100&page={page}')
        except urllib.error.HTTPError as e:
            if e.code == 409:  # empty repository
                return 0
            raise
        total += len(batch)
        if len(batch) < 100:
            return total
        page += 1


def collect():
    q = """query { viewer { login name
      pullRequests { totalCount } issues { totalCount }
      repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY], first:1) { totalCount } } }"""
    v = api("https://api.github.com/graphql", json.dumps({"query": q}).encode())["data"]["viewer"]
    repos = owned_repos()
    return {
        "name": v["name"] or v["login"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "commits": sum(count_commits(r, v["login"]) for r in repos),
        "prs": v["pullRequests"]["totalCount"],
        "issues": v["issues"]["totalCount"],
        "repos": len(repos),
    }


# Octicons (16px)
ICONS = {
    "stars": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "commits": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "prs": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issues": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repos": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}
LABELS = [
    ("stars", "Total Stars Earned"),
    ("commits", "Total Commits"),
    ("prs", "Total PRs"),
    ("issues", "Total Issues"),
    ("repos", "Repositories"),
]


def render(s):
    width, height = 400, 195
    rows = "".join(
        f'<g transform="translate(25,{55 + i * 25})">'
        f'<svg viewBox="0 0 16 16" width="16" height="16"><path fill="#79ff97" d="{ICONS[k]}"/></svg>'
        f'<text x="25" y="12.5" class="stat">{label}:</text>'
        f'<text x="230" y="12.5" class="stat bold">{s[k]}</text></g>'
        for i, (k, label) in enumerate(LABELS)
    )
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t">
<title id="t">{escape(s["name"])}'s GitHub Stats</title>
<style>
.title {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #ff6e96; }}
.stat {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #f8f8f2; }}
.bold {{ font-weight: 700; }}
</style>
<rect x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}" fill="#282a36" stroke="#e4e2e2"/>
<text x="25" y="35" class="title">{escape(s["name"])}'s GitHub Stats</text>
{rows}
</svg>
'''


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    stats = collect()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(json.dumps(stats))
