#!/usr/bin/env python3
"""Generate a 'live GitHub activity' SVG card (dark + light) in the same
visual language as the profile hero banner, using only SMIL animations.

Pulls the last few PUBLIC events for GITHUB_USERNAME from the GitHub REST
API (no auth needed for public data — the Actions runner's default
GITHUB_TOKEN is used automatically if present, just to raise the rate
limit). Falls back to a small static list if the API is unreachable so the
workflow never breaks.

Run manually:  python scripts/generate_activity_card.py
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
MAX_EVENTS = 5
LOCAL_UTC_OFFSET = 3  # Europe/Istanbul, no DST since 2016

# Accent palette shifts with the time of day (Türkiye local time) so the
# card's glow/border/text-gradient colors read like the sky outside —
# indigo at night, sunrise oranges in the morning, bright sky blues at
# midday, sunset pinks in the evening. Base background/panel/text stay the
# same as the hero card; only the 3 accent hues + a header label change.
TIME_PALETTES = [
    # (start_hour, end_hour, key, label, emoji, c1, c2, c3)
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

FALLBACK_EVENTS = [
    ("push", "React Native + Django ile filo yönetim platformu üzerinde çalışıyor", ""),
    ("focus", "Şu anki odak: Fleet Management & B2B2C", ""),
    ("build", "vdnp/vdnp profilini güncel tutuyor", ""),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def relative_time(iso_str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return ""
    delta = datetime.now(timezone.utc) - dt
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{max(seconds // 60, 1)}dk önce"
    if seconds < 86400:
        return f"{seconds // 3600}sa önce"
    if seconds < 86400 * 30:
        return f"{seconds // 86400}g önce"
    return dt.strftime("%d.%m.%Y")


def describe(event):
    kind = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload", {})
    ts = relative_time(event.get("created_at", ""))

    if kind == "PushEvent":
        n = len(payload.get("commits", []) or [])
        n = n or 1
        return "push", f"{n} commit push edildi → {repo}", ts
    if kind == "PullRequestEvent":
        action = payload.get("action", "opened")
        pr = payload.get("pull_request", {})
        title = (pr.get("title") or "")[:42]
        verb = {"opened": "PR açıldı", "closed": "PR kapatıldı", "reopened": "PR yeniden açıldı"}.get(action, f"PR {action}")
        return "pr", f"{verb}: {title} → {repo}", ts
    if kind == "WatchEvent":
        return "star", f"yıldızlandı → {repo}", ts
    if kind == "CreateEvent":
        ref_type = payload.get("ref_type", "repo")
        return "create", f"yeni {ref_type} oluşturuldu → {repo}", ts
    if kind == "IssuesEvent":
        action = payload.get("action", "opened")
        title = (payload.get("issue", {}).get("title") or "")[:42]
        return "issue", f"issue {action}: {title} → {repo}", ts
    if kind == "ForkEvent":
        return "fork", f"fork edildi → {repo}", ts
    if kind == "ReleaseEvent":
        tag = payload.get("release", {}).get("tag_name", "")
        return "release", f"{tag} yayınlandı → {repo}", ts
    return None


def fetch_events():
    try:
        req = urllib.request.Request(
            f"https://api.github.com/users/{GITHUB_USERNAME}/events/public?per_page=30",
            headers={
                "User-Agent": "vdnp-readme-bot",
                "Accept": "application/vnd.github+json",
                **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            events = json.loads(r.read().decode("utf-8"))
        out = []
        for e in events:
            desc = describe(e)
            if desc:
                out.append(desc)
            if len(out) >= MAX_EVENTS:
                break
        if out:
            return out
    except Exception:
        pass
    return FALLBACK_EVENTS


DOT_COLOR = {
    "push": "c2", "pr": "c1", "star": "c3", "create": "c1",
    "issue": "c2", "fork": "c3", "release": "c1",
    "focus": "c2", "build": "c3",
}

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


def build_svg(theme_name, events, bucket):
    t = dict(THEMES[theme_name])
    t["c1"], t["c2"], t["c3"] = bucket["c1"], bucket["c2"], bucket["c3"]
    w = 1180
    row_h = 32
    h = 96 + len(events) * row_h + 20

    rows = []
    for i, (kind, text, ts) in enumerate(events):
        y = 88 + i * row_h
        begin = 0.25 + i * 0.22
        color = t[DOT_COLOR.get(kind, "c2")]
        rows.append(
            f'  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>\n'
            f'    <circle cx="44" cy="{y - 5}" r="4" fill="{color}"/>\n'
            f'    <text x="60" y="{y}" font-size="14" fill="{t["text"]}">{esc(text)}</text>\n'
            + (f'    <text x="{w - 44}" y="{y}" text-anchor="end" font-size="12" fill="{t["muted"]}">{esc(ts)}</text>\n' if ts else '')
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
  <circle cx="44" cy="38" r="5" fill="{t['c3']}">
    <animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite"/>
  </circle>
  <text x="60" y="43" font-size="11" letter-spacing="2" fill="{t['muted']}">LIVE ACTIVITY · github.com/{GITHUB_USERNAME}</text>
  <text x="{w - 44}" y="43" text-anchor="end" font-size="12" fill="{t['muted']}">{bucket['emoji']} {bucket['label']}</text>
{chr(10).join(rows)}
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    events = fetch_events()
    bucket = get_time_bucket()
    for theme in ("dark", "light"):
        svg = build_svg(theme, events, bucket)
        out_path = OUT_DIR / f"activity-{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} ({len(events)} events, {bucket['emoji']} {bucket['label']})")


if __name__ == "__main__":
    main()
