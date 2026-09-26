"""Rewrite the "Actividad reciente" block of README.md from the public GitHub events feed.

Lists the latest pushes, pull requests, issues and releases of the profile owner,
grouped so that consecutive pushes to the same repo collapse into one line.
Runs inside GitHub Actions with the default GITHUB_TOKEN; no third-party service.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "ZyroEolu-sk")
MAX_LINES = 5
START, END = "<!--START_SECTION:activity-->", "<!--END_SECTION:activity-->"


def fetch_events():
    req = urllib.request.Request(
        f"https://api.github.com/users/{USER}/events/public?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "User-Agent": "profile-activity",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fmt_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%d %b %Y")


def describe(ev):
    repo = ev["repo"]["name"]
    url = f"https://github.com/{repo}"
    p = ev["payload"]
    t = ev["type"]
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return ("push", repo, f"📤 {n} commit{'s' if n != 1 else ''} en [{repo}]({url})")
    if t == "PullRequestEvent":
        pr = p["pull_request"]
        return ("pr", repo, f"🔀 PR {p['action']}: [{pr['title']}]({pr['html_url']}) en {repo}")
    if t == "IssuesEvent":
        it = p["issue"]
        return ("issue", repo, f"❗ Issue {p['action']}: [{it['title']}]({it['html_url']}) en {repo}")
    if t == "ReleaseEvent":
        r = p["release"]
        return ("release", repo, f"🏷️ Release [{r.get('name') or r['tag_name']}]({r['html_url']}) en {repo}")
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return ("create", repo, f"🆕 Nuevo repositorio [{repo}]({url})")
    return None


def build_lines(events):
    lines, last_push_repo = [], None
    for ev in events:
        d = describe(ev)
        if not d:
            continue
        kind, repo, text = d
        if kind == "push" and repo == last_push_repo:
            continue  # collapse consecutive pushes to the same repo
        last_push_repo = repo if kind == "push" else None
        lines.append(f"- {text} · {fmt_date(ev['created_at'])}")
        if len(lines) >= MAX_LINES:
            break
    return lines or ["- Sin actividad pública reciente."]


def main():
    readme = open("README.md", encoding="utf-8").read()
    if START not in readme or END not in readme:
        raise SystemExit("README.md lacks the activity markers")
    block = "\n".join([START, *build_lines(fetch_events()), END])
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, readme, flags=re.S)
    if new != readme:
        open("README.md", "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
