#!/usr/bin/env python3
"""Generate a 'GitHub stats' SVG card (dark + light) built entirely from
GitHub's own REST + Search APIs — no dependency on third-party community
services (which go down/rate-limit often). Same visual language as the
hero banner.

Run manually:  python scripts/generate_stats_card.py
Run by CI:     see .github/workflows/dynamic-readme.yml
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GITHUB_USERNAME = "vdnp"
OUT_DIR = Path(__file__).resolve().parent.parent
LOCAL_UTC_OFFSET = 3  # Europe/Istanbul, no DST since 2016

# Shared across every card so the whole profile shifts hue together.
TIME_PALETTES = [
    (0, 6, "night", "GECE", "🌙", "#312E81", "#6366F1", "#7C3AED"),
    (6, 11, "morning", "SABAH", "🌅", "#F97316", "#FBBF24", "#EC4899"),
    (11, 17, "day", "GÜNDÜZ", "☀️", "#0EA5E9", "#22D3EE", "#10B981"),
    (17, 22, "evening", "AKŞAM", "🌆", "#F97316", "#EC4899", "#8B5CF6"),
    (22, 24, "night", "GECE", "🌙", "#312E81", "#6366F1", "#7C3AED"),
]


def get_time_bucket():
    local_hour = (datetime.now(timezone.utc).hour + LOCAL_UTC_OFFSET) % 24
    for start, end, key, label, emoji, c1, c2, c3 in TIME_PALETTES:
        if start <= local_hour < end:
            return dict(key=key, label=label, emoji=emoji, c1=c1, c2=c2, c3=c3)
    return dict(key="day", label="GÜNDÜZ", emoji="☀️", c1="#0EA5E9", c2="#22D3EE", c3="#10B981")


def api_headers(token=None):
    h = {"User-Agent": "vdnp-readme-bot", "Accept": "application/vnd.github+json"}
    tok = token or os.environ.get("GITHUB_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def get_json(url, token=None):
    req = urllib.request.Request(url, headers=api_headers(token))
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def search_count(query):
    try:
        data = get_json(f"https://api.github.com/search/issues?q={query}&per_page=1")
        return data.get("total_count", 0)
    except Exception:
        return None


def fetch_stats():
    # Optional personal token (repo scope, own account only) — if set, we
    # can count private repos too. Never used for the activity feed, so no
    # private push timing ever leaks; just aggregate counts here.
    pat = os.environ.get("GH_PAT")
    try:
        if pat:
            profile = get_json("https://api.github.com/user", token=pat)
            repos = get_json(
                "https://api.github.com/user/repos?affiliation=owner&per_page=100&visibility=all",
                token=pat,
            )
            include_private = True
        else:
            profile = get_json(f"https://api.github.com/users/{GITHUB_USERNAME}")
            repos = get_json(
                f"https://api.github.com/users/{GITHUB_USERNAME}/repos?type=owner&per_page=100"
            )
            include_private = False

        own_repos = [r for r in repos if not r.get("fork")]
        stars = sum(r.get("stargazers_count", 0) for r in own_repos)
        forks = sum(r.get("forks_count", 0) for r in own_repos)
        private_count = sum(1 for r in own_repos if r.get("private"))

        prs = search_count(f"author:{GITHUB_USERNAME}+type:pr")
        issues = search_count(f"author:{GITHUB_USERNAME}+type:issue")

        repos_count = len(own_repos) if include_private else profile.get("public_repos", len(own_repos))

        return dict(
            repos=repos_count,
            followers=profile.get("followers", 0),
            stars=stars,
            forks=forks,
            prs=prs,
            issues=issues,
            include_private=include_private,
            private_count=private_count if include_private else None,
        )
    except Exception:
        return None


FALLBACK_STATS = dict(repos=None, followers=None, stars=None, forks=None, prs=None, issues=None,
                       include_private=False, private_count=None)

THEMES = {
    "dark": dict(bg="#030712", panel="#0F172A", panel_op="0.55", text="#F8FAFC", muted="#94A3B8",
                 c1="#7C3AED", c2="#22D3EE", c3="#10B981",
                 outer_stroke="#FFFFFF", outer_op="0.06", panel_stroke="#FFFFFF", panel_stroke_op="0.08"),
    "light": dict(bg="#FFFFFF", panel="#F8FAFC", panel_op="0.8", text="#0F172A", muted="#475569",
                  c1="#2563EB", c2="#06B6D4", c3="#10B981",
                  outer_stroke="#0F172A", outer_op="0.06", panel_stroke="#0F172A", panel_stroke_op="0.08"),
}

def build_svg(theme_name, stats, bucket):
    t = dict(THEMES[theme_name])
    t["c1"], t["c2"], t["c3"] = bucket["c1"], bucket["c2"], bucket["c3"]
    w = 1180
    h = 190
    cols = 6
    tile_w = (w - 84) / cols
    tile_x0 = 42
    tile_y = 70

    repo_label = "Toplam Repo" if stats.get("include_private") else "Public Repos"
    tiles_def = [
        ("repos", "📦", repo_label),
        ("stars", "⭐", "Toplam Yıldız"),
        ("followers", "👥", "Takipçi"),
        ("prs", "🔀", "Pull Request"),
        ("issues", "🐛", "Issue"),
        ("forks", "🍴", "Fork Alınan"),
    ]

    tiles = []
    for i, (key, emoji, label) in enumerate(tiles_def):
        val = stats.get(key)
        display = f"{val:,}".replace(",", ".") if isinstance(val, int) else "—"
        cx = tile_x0 + tile_w * i + tile_w / 2
        begin = 0.2 + i * 0.12
        tiles.append(
            f'  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="{begin:.2f}s" fill="freeze"/>\n'
            f'    <text x="{cx:.1f}" y="{tile_y}" text-anchor="middle" font-size="20">{emoji}</text>\n'
            f'    <text x="{cx:.1f}" y="{tile_y + 42}" text-anchor="middle" font-size="30" font-weight="800" fill="url(#accentGrad)">{display}</text>\n'
            f'    <text x="{cx:.1f}" y="{tile_y + 66}" text-anchor="middle" font-size="12" fill="{t["muted"]}">{label}</text>\n'
            "  </g>"
        )
        if i > 0:
            lx = tile_x0 + tile_w * i
            tiles.append(f'  <line x1="{lx:.1f}" y1="{tile_y - 14}" x2="{lx:.1f}" y2="{tile_y + 70}" stroke="{t["muted"]}" stroke-opacity="0.12"/>')

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
  <clipPath id="cardClip"><rect x="0" y="0" width="{w}" height="{h}" rx="24"/></clipPath>
  <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{t['c1']}"><animate attributeName="stop-color" values="{t['c1']};{t['c2']};{t['c3']};{t['c1']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="50%" stop-color="{t['c2']}"><animate attributeName="stop-color" values="{t['c2']};{t['c3']};{t['c1']};{t['c2']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="100%" stop-color="{t['c3']}"><animate attributeName="stop-color" values="{t['c3']};{t['c1']};{t['c2']};{t['c3']}" dur="8s" repeatCount="indefinite"/></stop>
  </linearGradient>
  <radialGradient id="glow1" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0.28"/><stop offset="100%" stop-color="{t['c1']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="borderShimmer" gradientUnits="userSpaceOnUse" x1="-300" y1="0" x2="100" y2="0">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{t['c2']}" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="{t['c3']}" stop-opacity="0"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;1480 0;0 0" dur="7s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="24" fill="{t['bg']}"/>
<g clip-path="url(#cardClip)">
  <circle cx="{w/2}" cy="0" r="220" fill="url(#glow1)"/>
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="{t['panel']}" fill-opacity="{t['panel_op']}" stroke="{t['panel_stroke']}" stroke-opacity="{t['panel_stroke_op']}" stroke-width="1"/>
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="none" stroke="url(#borderShimmer)" stroke-width="1.4"/>
  <text x="42" y="38" font-size="11" letter-spacing="2" fill="{t['muted']}">GITHUB İSTATİSTİKLERİM · github.com/{GITHUB_USERNAME}</text>
  <text x="{w - 42}" y="38" text-anchor="end" font-size="12" fill="{t['muted']}">{bucket['emoji']} {bucket['label']}</text>
{chr(10).join(tiles)}
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    stats = fetch_stats() or FALLBACK_STATS
    bucket = get_time_bucket()
    for theme in ("dark", "light"):
        svg = build_svg(theme, stats, bucket)
        out_path = OUT_DIR / f"stats-{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} :: {stats}")


if __name__ == "__main__":
    main()
