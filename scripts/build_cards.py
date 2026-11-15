"""Draw the profile cards in assets/ and refresh the PR list in README.md.

Run from the repo root: python3 scripts/build_cards.py
Static cards come from profile.json; the Open Source card comes from the GitHub API.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import escape

P = json.load(open("profile.json"))
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
# shortcut: colours follow the viewer's OS theme, not their GitHub theme setting;
# switch to <picture> with light/dark files if that mismatch ever matters.
STYLE = f"""<style>
text{{font-family:{FONT}}}
.bg{{fill:#fff;stroke:#d0d7de}} .t{{fill:#1f2328}} .m{{fill:#59636e}}
@media(prefers-color-scheme:dark){{.bg{{fill:#0d1117;stroke:#30363d}} .t{{fill:#e6edf3}} .m{{fill:#9198a1}}}}
</style>"""


def cut(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def card(title, accent, rows, note=""):
    """rows: up to 4 of (heading, sub, tag)."""
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="410" height="270" viewBox="0 0 410 270" role="img" aria-label="{escape(title)}">',
        STYLE,
        '<rect class="bg" x=".5" y=".5" width="409" height="269" rx="10"/>',
        f'<rect x="24" y="26" width="4" height="20" rx="2" fill="{accent}"/>',
        f'<text class="t" x="38" y="42" font-size="17" font-weight="700">{escape(title)}</text>',
        f'<text class="m" x="386" y="42" font-size="12" text-anchor="end">{escape(note)}</text>',
    ]
    for i, (head, sub, tag) in enumerate(rows[:4]):
        y = 84 + i * 48
        out.append(f'<text class="t" x="24" y="{y}" font-size="14" font-weight="600">{escape(cut(head, 36))}</text>')
        out.append(f'<text class="m" x="24" y="{y + 18}" font-size="12">{escape(cut(sub, 58))}</text>')
        if tag:
            out.append(f'<text x="386" y="{y}" font-size="11" font-weight="700" text-anchor="end" fill="{accent}">{escape(tag.upper())}</text>')
    return "\n".join(out + ["</svg>"])


def hero():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="830" height="190" viewBox="0 0 830 190" role="img" aria-label="{escape(P['name'])}">
{STYLE}
<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#8250df"/><stop offset=".5" stop-color="#0969da"/><stop offset="1" stop-color="#1a7f37"/></linearGradient></defs>
<rect class="bg" x=".5" y=".5" width="829" height="189" rx="10"/>
<rect x="40" y="150" width="750" height="4" rx="2" fill="url(#g)" opacity=".25"/>
<rect x="40" y="150" width="120" height="4" rx="2" fill="url(#g)"><animate attributeName="x" values="40;670;40" dur="8s" repeatCount="indefinite"/></rect>
<text class="t" x="40" y="72" font-size="40" font-weight="800">{escape(P['name'])}</text>
<text class="t" x="40" y="104" font-size="18">{escape(P['tagline'])}</text>
<text class="m" x="40" y="130" font-size="15">{escape(P['subline'])}</text>
</svg>"""


def external_prs():
    """Merged and open PRs to repos the user does not own, merged first, newest first."""
    url = f"https://api.github.com/search/issues?q=author:{P['user']}+type:pr+-user:{P['user']}&per_page=100"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-cards"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    prs = []
    for it in json.load(urllib.request.urlopen(req))["items"]:
        merged = it["pull_request"].get("merged_at")
        if not merged and it["state"] != "open":
            continue  # closed without merging
        prs.append({"repo": it["repository_url"].split("/repos/")[1], "title": it["title"].strip(),
                    "url": it["html_url"], "merged": bool(merged), "date": merged or it["created_at"]})
    return sorted(prs, key=lambda p: (p["merged"], p["date"]), reverse=True)


def main():
    prs = external_prs()
    n_merged = sum(p["merged"] for p in prs)
    note = f"{n_merged} merged · {len(prs) - n_merged} in review"
    rows = [(p["repo"], p["title"], "Merged" if p["merged"] else "In review") for p in prs]
    svgs = {"hero": hero(), "opensource": card("Open Source", "#8250df", rows, note)}
    for c in P["cards"]:
        svgs[c["file"]] = card(c["title"], c["accent"], c["rows"])

    os.makedirs("assets", exist_ok=True)
    for name, svg in svgs.items():
        ET.fromstring(svg)  # self-check: every card must be well-formed XML
        open(f"assets/{name}.svg", "w").write(svg + "\n")

    links = "\n".join(f"- [{p['repo']}]({p['url']}): {p['title']} ({'merged' if p['merged'] else 'in review'})" for p in prs)
    readme = open("README.md").read()
    new, n = re.subn(r"(<!-- OSS:START -->).*?(<!-- OSS:END -->)", lambda m: f"{m[1]}\n{links}\n{m[2]}", readme, flags=re.S)
    assert n == 1, "README.md must contain one OSS:START / OSS:END block"
    open("README.md", "w").write(new)
    print(f"{len(svgs)} cards written, {len(prs)} PRs listed")


if __name__ == "__main__":
    assert cut("abcdef", 4) == "abc…" and cut("abc", 4) == "abc"
    main()
