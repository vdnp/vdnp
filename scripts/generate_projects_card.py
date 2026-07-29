#!/usr/bin/env python3
"""Generate a 'currently working on' SVG card (dark + light) built from the
user's *real* most-recently-pushed public repos (not hand-written text),
in the same visual language as the hero banner.

Run manually:  python scripts/generate_projects_card.py
Run by CI:     see .github/workflows/dynamic-readme.yml
"""
import html
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GITHUB_USERNAME = "vdnp"
OUT_DIR = Path(__file__).resolve().parent.parent
MAX_REPOS = 3
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

# Used only if the GitHub API can't be reached (e.g. no network in this
# sandbox). Kept intentionally close to the original static bullets so we
# never invent facts — the real card overwrites this once the workflow runs
# on GitHub's infrastructure.
FALLBACK_REPOS = [
    dict(name="FiloYonetimSistemiGelistirme", desc="React Native & Django ile B2B2C mobil filo yönetim çözümü", lang="TypeScript", ts=""),
    dict(name="tablekit", desc="Akademik projeler için sağlam web sistemleri", lang="TypeScript", ts=""),
    dict(name="image-turbo", desc="İlişkisel veritabanı yapıları ve sorgu performansı üzerine çalışma", lang="TypeScript", ts=""),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def relative_time(iso_str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return ""
    seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
    if seconds < 3600:
        return f"{max(seconds // 60, 1)}dk önce"
    if seconds < 86400:
        return f"{seconds // 3600}sa önce"
    if seconds < 86400 * 30:
        return f"{seconds // 86400}g önce"
    return dt.strftime("%d.%m.%Y")


def api_headers():
    h = {"User-Agent": "vdnp-readme-bot", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


def fetch_repos():
    try:
        req = urllib.request.Request(
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos?type=owner&sort=pushed&direction=desc&per_page=30",
            headers=api_headers(),
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            repos = json.loads(r.read().decode("utf-8"))
        out = []
        for repo in repos:
            if repo.get("fork") or repo.get("archived"):
                continue
            out.append(dict(
                name=repo["name"],
                desc=(repo.get("description") or "Açıklama eklenmemiş").strip(),
                lang=repo.get("language") or "—",
                ts=relative_time(repo.get("pushed_at", "")),
                stars=repo.get("stargazers_count", 0),
            ))
            if len(out) >= MAX_REPOS:
                break
        if out:
            return out
    except Exception:
        pass
    return FALLBACK_REPOS


THEMES = {
    "dark": dict(
        bg="#030712", panel="#0F172A", panel_op="0.55", text="#F8FAFC", muted="#94A3B8",
        c1="#7C3AED", c2="#22D3EE", c3="#10B981",
        outer_stroke="#FFFFFF", outer_op="0.06",
        panel_stroke="#FFFFFF", panel_stroke_op="0.08",
    ),
    "light": dict(
        bg="#FFFFFF", panel="#F8FAFC", panel_op="0.8", text="#0F172A", muted="#475569",
        c1="#2563EB", c2="#06B6D4", c3="#10B981",
        outer_stroke="#0F172A", outer_op="0.06",
        panel_stroke="#0F172A", panel_stroke_op="0.08",
    ),
}


def build_svg(theme_name, repos, bucket):
    t = dict(THEMES[theme_name])
    t["c1"], t["c2"], t["c3"] = bucket["c1"], bucket["c2"], bucket["c3"]
    w = 1180
    row_h = 54
    h = 70 + len(repos) * row_h + 20

    rows = []
    for i, r in enumerate(repos):
        y = 88 + i * row_h
        begin = 0.25 + i * 0.25
        desc = r["desc"]
        if len(desc) > 78:
            desc = desc[:77].rstrip() + "…"
        meta_bits = [r["lang"]]
        if r.get("stars"):
            meta_bits.append(f"★ {r['stars']}")
        if r.get("ts"):
            meta_bits.append(r["ts"])
        meta = "  ·  ".join(meta_bits)
        rows.append(
            f'  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.45s" begin="{begin:.2f}s" fill="freeze"/>\n'
            f'    <circle cx="44" cy="{y - 6}" r="4" fill="url(#accentGrad)"/>\n'
            f'    <text x="60" y="{y}" font-size="16" font-weight="700" fill="{t["text"]}">{esc(r["name"])}</text>\n'
            f'    <text x="60" y="{y + 20}" font-size="13" fill="{t["muted"]}">{esc(desc)}</text>\n'
            f'    <text x="{w - 44}" y="{y}" text-anchor="end" font-size="12" font-family="\'Courier New\',monospace" fill="{t["muted"]}">{esc(meta)}</text>\n'
            + '  </g>'
        )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
  <clipPath id="cardClip"><rect x="0" y="0" width="{w}" height="{h}" rx="24"/></clipPath>
  <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{t['c1']}"><animate attributeName="stop-color" values="{t['c1']};{t['c2']};{t['c3']};{t['c1']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="50%" stop-color="{t['c2']}"><animate attributeName="stop-color" values="{t['c2']};{t['c3']};{t['c1']};{t['c2']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="100%" stop-color="{t['c3']}"><animate attributeName="stop-color" values="{t['c3']};{t['c1']};{t['c2']};{t['c3']}" dur="8s" repeatCount="indefinite"/></stop>
  </linearGradient>
  <radialGradient id="glow1" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0.3"/><stop offset="100%" stop-color="{t['c1']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow2" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c2']}" stop-opacity="0.28"/><stop offset="100%" stop-color="{t['c2']}" stop-opacity="0"/>
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
  <circle cx="110" cy="20" r="140" fill="url(#glow1)">
    <animateTransform attributeName="transform" type="translate" values="0,0; 20,10; -8,15; 0,0" dur="14s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{w - 120}" cy="{h - 20}" r="160" fill="url(#glow2)">
    <animateTransform attributeName="transform" type="translate" values="0,0; -15,-10; 10,8; 0,0" dur="16s" repeatCount="indefinite"/>
  </circle>
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="{t['panel']}" fill-opacity="{t['panel_op']}" stroke="{t['panel_stroke']}" stroke-opacity="{t['panel_stroke_op']}" stroke-width="1"/>
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="none" stroke="url(#borderShimmer)" stroke-width="1.4"/>
  <text x="42" y="38" font-size="11" letter-spacing="2" fill="{t['muted']}">ŞU AN ÜZERİNDE ÇALIŞTIKLARIM · en son push edilenler</text>
  <text x="{w - 42}" y="38" text-anchor="end" font-size="12" fill="{t['muted']}">{bucket['emoji']} {bucket['label']}</text>
{chr(10).join(rows)}
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    repos = fetch_repos()
    bucket = get_time_bucket()
    for theme in ("dark", "light"):
        svg = build_svg(theme, repos, bucket)
        out_path = OUT_DIR / f"working-on-{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} ({len(repos)} repos)")


if __name__ == "__main__":
    main()
