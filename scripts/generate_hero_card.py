#!/usr/bin/env python3
"""Generate the profile hero card (dark.svg / light.svg): greeting, typing
role rotation, quick info, skill pills — plus a live 'Şu An Dinliyorum'
Spotify block under the SKILLS column, with the track's cover art (via the
user's own Spotify Web API app, not any third-party proxy, since those tend
to shut down).

If Spotify secrets aren't configured (or the API call fails), the block
falls back to a neutral "not connected" placeholder instead of breaking the card.

Run manually:  python scripts/generate_hero_card.py
Run by CI:     see .github/workflows/dynamic-readme.yml
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent
LOCAL_UTC_OFFSET = 3  # Europe/Istanbul, no DST since 2016

# Shared across every card (hero, stats, activity, working-on, langs) so the
# whole profile shifts hue together — indigo at night, sunrise oranges in
# the morning, sky blues at midday, sunset pinks in the evening.
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


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- Spotify --

MAX_COVER_BYTES = 300_000  # guard against an unexpectedly huge response bloating the SVG


def fetch_cover(item):
    """Download the smallest available album cover and base64-encode it, so
    the SVG stays fully self-contained (no external image fetch needed when
    someone actually views the README)."""
    try:
        images = (item.get("album") or {}).get("images") or []
        if not images:
            return None, None
        img_url = images[-1]["url"]  # last = smallest (usually ~64x64)
        if not img_url.startswith("https://"):
            return None, None
        img_req = urllib.request.Request(img_url, headers={"User-Agent": "vdnp-readme-bot"})
        with urllib.request.urlopen(img_req, timeout=8) as r:
            mime = r.headers.get_content_type() or "image/jpeg"
            raw = r.read(MAX_COVER_BYTES + 1)
            if len(raw) > MAX_COVER_BYTES:
                return None, None
            data = base64.b64encode(raw).decode()
            return data, mime
    except Exception:
        return None, None


def fetch_spotify():
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        return None

    try:
        basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        token_req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode(),
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(token_req, timeout=8) as r:
            access_token = json.loads(r.read().decode())["access_token"]
        auth = {"Authorization": f"Bearer {access_token}"}

        try:
            req = urllib.request.Request("https://api.spotify.com/v1/me/player/currently-playing", headers=auth)
            with urllib.request.urlopen(req, timeout=8) as r:
                body = r.read().decode().strip()
                if body:
                    data = json.loads(body)
                    if data and data.get("is_playing") and data.get("item"):
                        item = data["item"]
                        cover_b64, cover_mime = fetch_cover(item)
                        return dict(playing=True, track=item["name"],
                                    artist=", ".join(a["name"] for a in item["artists"]),
                                    cover_b64=cover_b64, cover_mime=cover_mime)
        except urllib.error.HTTPError:
            pass

        req2 = urllib.request.Request("https://api.spotify.com/v1/me/player/recently-played?limit=1", headers=auth)
        with urllib.request.urlopen(req2, timeout=8) as r:
            data = json.loads(r.read().decode())
            items = data.get("items", [])
            if items:
                item = items[0]["track"]
                cover_b64, cover_mime = fetch_cover(item)
                return dict(playing=False, track=item["name"],
                            artist=", ".join(a["name"] for a in item["artists"]),
                            cover_b64=cover_b64, cover_mime=cover_mime)
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ Theme --

THEMES = {
    "dark": dict(
        bg="#030712", panel="#0F172A", header="#111827", text="#F8FAFC", muted="#94A3B8",
        c1="#7C3AED", c2="#22D3EE", c3="#10B981",
        outer_stroke="#FFFFFF", outer_op="0.06", panel_stroke="#FFFFFF", panel_stroke_op="0.08",
        particle="#22D3EE", noise="1 1 1",
    ),
    "light": dict(
        bg="#FFFFFF", panel="#F8FAFC", header="#EEF2F7", text="#0F172A", muted="#475569",
        c1="#2563EB", c2="#06B6D4", c3="#10B981",
        outer_stroke="#0F172A", outer_op="0.06", panel_stroke="#0F172A", panel_stroke_op="0.08",
        particle="#06B6D4", noise="0 0 0",
    ),
}

SKILLS_ROW1 = [("React", 63), ("Expo", 56), ("JavaScript", 98), ("HTML", 56), ("CSS", 49)]
SKILLS_ROW2 = [("Python", 70), ("Django", 70), ("ASP.NET", 77), ("C#", 42), ("PostgreSQL", 98)]
SKILLS_ROW3 = [("SQLite", 70), ("Git", 49), ("Figma", 63), ("Postman", 76)]

PILL_STROKE_CYCLE = ["c2", "c1", "c3", "c2", "c1", "c3", "c2", "c1", "c3", "c2", "c1", "c3", "c2", "c1"]
PILL_PULSE_DUR = [3, 3.4, 2.8, 3.2, 3.6, 3.1, 2.9, 3.3, 3.5, 3, 3.2, 2.7, 3.4, 3]


def build_pill_row(t, row, x0, y, begin0):
    out = []
    x = x0
    i_offset = len(begin0["seen"])
    for name, width in row:
        i = i_offset
        begin0["seen"].append(1)
        stroke = t[PILL_STROKE_CYCLE[i % len(PILL_STROKE_CYCLE)]]
        pulse = PILL_PULSE_DUR[i % len(PILL_PULSE_DUR)]
        begin = 2.35 + i * 0.05
        out.append(
            f'    <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin:.2f}s" fill="freeze"/>\n'
            f'      <rect x="{x}" y="{y}" width="{width}" height="30" rx="15" fill="#FFFFFF" fill-opacity="0.05" stroke="{stroke}" stroke-opacity="0.5"><animate attributeName="stroke-opacity" values="0.3;0.7;0.3" dur="{pulse}s" repeatCount="indefinite"/></rect>\n'
            f'      <text x="{x + width / 2}" y="{y + 20}" text-anchor="middle" fill="{t["text"]}">{name}</text>\n'
            "    </g>"
        )
        x += width + 8
        i_offset += 1
    return out


def build_svg(theme_name, spotify, bucket):
    t = dict(THEMES[theme_name])
    t["c1"], t["c2"], t["c3"] = bucket["c1"], bucket["c2"], bucket["c3"]
    w, h = 1180, 360
    panel_h = h - 48

    pill_state = {"seen": []}
    rows = []
    rows += build_pill_row(t, SKILLS_ROW1, 600, 112, pill_state)
    rows += build_pill_row(t, SKILLS_ROW2, 600, 152, pill_state)
    rows += build_pill_row(t, SKILLS_ROW3, 600, 192, pill_state)
    pills_svg = "\n".join(rows)

    # --- "Şu An Dinliyorum" block: sits under the SKILLS column, mirroring
    # the quick-info block on the left. Cover art is embedded as a base64
    # data URI (fetched once at build time) so the card stays self-contained.
    sp_x = 600
    cover_size = 46
    cover_x, cover_y = sp_x, 258
    text_x = cover_x + cover_size + 14

    if spotify:
        verb = "Şu an dinliyor" if spotify["playing"] else "Son dinlediği"
        track = spotify["track"]
        if len(track) > 34:
            track = track[:33].rstrip() + "…"
        artist = spotify["artist"]
        if len(artist) > 34:
            artist = artist[:33].rstrip() + "…"

        if spotify.get("cover_b64"):
            cover_svg = (
                f'<image x="{cover_x}" y="{cover_y}" width="{cover_size}" height="{cover_size}" '
                f'clip-path="url(#coverClip)" preserveAspectRatio="xMidYMid slice" '
                f'href="data:{spotify["cover_mime"]};base64,{spotify["cover_b64"]}"/>'
            )
        else:
            cover_svg = (
                f'<rect x="{cover_x}" y="{cover_y}" width="{cover_size}" height="{cover_size}" rx="10" fill="{t["muted"]}" fill-opacity="0.15"/>'
                f'<text x="{cover_x + cover_size / 2}" y="{cover_y + cover_size / 2 + 5}" text-anchor="middle" font-size="18" fill="{t["muted"]}">♪</text>'
            )

        dot = ""
        if spotify["playing"]:
            dot = (
                f'<circle cx="{cover_x + cover_size + 6}" cy="{cover_y + 6}" r="4" fill="{t["c3"]}">'
                f'<animate attributeName="opacity" values="0.3;1;0.3" dur="1.6s" repeatCount="indefinite"/></circle>'
            )

        spotify_block = (
            f'    <line x1="{sp_x}" y1="238" x2="1140" y2="238" stroke="{t["muted"]}" stroke-opacity="0.15"/>\n'
            f'    <text x="{sp_x}" y="252" fill="{t["muted"]}" font-size="12">🎧 {verb}</text>\n'
            f'    {cover_svg}\n'
            f'    {dot}\n'
            f'    <text x="{text_x}" y="{cover_y + 19}" font-size="14" font-weight="700" fill="{t["text"]}">{esc(track)}</text>\n'
            f'    <text x="{text_x}" y="{cover_y + 37}" font-size="12.5" fill="{t["muted"]}">{esc(artist)}</text>'
        )
    else:
        cover_svg = (
            f'<rect x="{cover_x}" y="{cover_y}" width="{cover_size}" height="{cover_size}" rx="10" fill="{t["muted"]}" fill-opacity="0.12"/>'
            f'<text x="{cover_x + cover_size / 2}" y="{cover_y + cover_size / 2 + 5}" text-anchor="middle" font-size="18" fill="{t["muted"]}">♪</text>'
        )
        spotify_block = (
            f'    <line x1="{sp_x}" y1="238" x2="1140" y2="238" stroke="{t["muted"]}" stroke-opacity="0.15"/>\n'
            f'    <text x="{sp_x}" y="252" fill="{t["muted"]}" font-size="12">🎧 Spotify</text>\n'
            f'    {cover_svg}\n'
            f'    <text x="{text_x}" y="{cover_y + 28}" font-size="13" fill="{t["muted"]}">Spotify henüz bağlanmadı</text>'
        )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
  <clipPath id="cardClip"><rect x="0" y="0" width="{w}" height="{h}" rx="24"/></clipPath>

  <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{t['c1']}"><animate attributeName="stop-color" values="{t['c1']};{t['c2']};{t['c3']};{t['c1']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="50%" stop-color="{t['c2']}"><animate attributeName="stop-color" values="{t['c2']};{t['c3']};{t['c1']};{t['c2']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="100%" stop-color="{t['c3']}"><animate attributeName="stop-color" values="{t['c3']};{t['c1']};{t['c2']};{t['c3']}" dur="8s" repeatCount="indefinite"/></stop>
  </linearGradient>

  <radialGradient id="glowViolet" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0.5"/>
    <stop offset="100%" stop-color="{t['c1']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glowCyan" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c2']}" stop-opacity="0.4"/>
    <stop offset="100%" stop-color="{t['c2']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glowEmerald" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{t['c3']}" stop-opacity="0.35"/>
    <stop offset="100%" stop-color="{t['c3']}" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="borderShimmer" gradientUnits="userSpaceOnUse" x1="-300" y1="0" x2="100" y2="0">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{t['c2']}" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="{t['c3']}" stop-opacity="0"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;1480 0;0 0" dur="7s" repeatCount="indefinite"/>
  </linearGradient>

  <filter id="noiseFilter" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" result="noise"/>
    <feColorMatrix in="noise" type="matrix" values="0 0 0 0 {t['noise'].split()[0]}  0 0 0 0 {t['noise'].split()[1]}  0 0 0 0 {t['noise'].split()[2]}  0 0 0 0.02 0"/>
  </filter>

  <clipPath id="phraseClip0"><rect x="72" y="134" width="0" height="26"><animate attributeName="width" keyTimes="0;0.05;0.249;0.25;1" values="0;220;220;0;0" dur="16s" repeatCount="indefinite"/></rect></clipPath>
  <clipPath id="phraseClip1"><rect x="72" y="134" width="0" height="26"><animate attributeName="width" keyTimes="0;0.25;0.30;0.499;0.5;1" values="0;0;252;252;0;0" dur="16s" repeatCount="indefinite"/></rect></clipPath>
  <clipPath id="phraseClip2"><rect x="72" y="134" width="0" height="26"><animate attributeName="width" keyTimes="0;0.5;0.55;0.749;0.75;1" values="0;0;252;252;0;0" dur="16s" repeatCount="indefinite"/></rect></clipPath>
  <clipPath id="phraseClip3"><rect x="72" y="134" width="0" height="26"><animate attributeName="width" keyTimes="0;0.75;0.8;0.999;1" values="0;0;252;252;0" dur="16s" repeatCount="indefinite"/></rect></clipPath>

  <clipPath id="coverClip"><rect x="{cover_x}" y="{cover_y}" width="{cover_size}" height="{cover_size}" rx="10"/></clipPath>
</defs>

<rect width="{w}" height="{h}" rx="24" fill="{t['bg']}"/>

<g clip-path="url(#cardClip)">
  <circle cx="140" cy="80" r="180" fill="url(#glowViolet)">
    <animateTransform attributeName="transform" type="translate" values="0,0; 25,15; -10,25; 0,0" dur="14s" repeatCount="indefinite"/>
  </circle>
  <circle cx="1030" cy="300" r="220" fill="url(#glowCyan)">
    <animateTransform attributeName="transform" type="translate" values="0,0; -20,-20; 15,10; 0,0" dur="16s" repeatCount="indefinite"/>
  </circle>
  <circle cx="650" cy="30" r="150" fill="url(#glowEmerald)">
    <animateTransform attributeName="transform" type="translate" values="0,0; 18,20; -12,-8; 0,0" dur="12s" repeatCount="indefinite"/>
  </circle>

  <rect width="{w}" height="{h}" filter="url(#noiseFilter)" opacity="0.5"/>

  <g fill="{t['particle']}">
    <circle cx="90" cy="300" r="1.6" opacity="0.5"><animate attributeName="cy" values="300;270;300" dur="6s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;0.7;0" dur="6s" repeatCount="indefinite"/></circle>
    <circle cx="300" cy="60" r="1.3" opacity="0.5"><animate attributeName="cy" values="60;30;60" dur="7.5s" repeatCount="indefinite" begin="0.5s"/><animate attributeName="opacity" values="0;0.6;0" dur="7.5s" repeatCount="indefinite" begin="0.5s"/></circle>
    <circle cx="520" cy="330" r="1.4" opacity="0.5"><animate attributeName="cy" values="330;300;330" dur="8s" repeatCount="indefinite" begin="1s"/><animate attributeName="opacity" values="0;0.6;0" dur="8s" repeatCount="indefinite" begin="1s"/></circle>
    <circle cx="760" cy="60" r="1.2" opacity="0.4"><animate attributeName="cy" values="60;30;60" dur="9s" repeatCount="indefinite" begin="1.5s"/><animate attributeName="opacity" values="0;0.5;0" dur="9s" repeatCount="indefinite" begin="1.5s"/></circle>
    <circle cx="950" cy="120" r="1.5" opacity="0.5"><animate attributeName="cy" values="120;90;120" dur="6.5s" repeatCount="indefinite" begin="2s"/><animate attributeName="opacity" values="0;0.6;0" dur="6.5s" repeatCount="indefinite" begin="2s"/></circle>
    <circle cx="1100" cy="250" r="1.4" opacity="0.5"><animate attributeName="cy" values="250;220;250" dur="7s" repeatCount="indefinite" begin="0.3s"/><animate attributeName="opacity" values="0;0.6;0" dur="7s" repeatCount="indefinite" begin="0.3s"/></circle>
    <circle cx="200" cy="200" r="1.3" opacity="0.4"><animate attributeName="cy" values="200;170;200" dur="8.5s" repeatCount="indefinite" begin="1.2s"/><animate attributeName="opacity" values="0;0.5;0" dur="8.5s" repeatCount="indefinite" begin="1.2s"/></circle>
    <circle cx="430" cy="140" r="1.3" opacity="0.4"><animate attributeName="cy" values="140;110;140" dur="7.2s" repeatCount="indefinite" begin="2.4s"/><animate attributeName="opacity" values="0;0.5;0" dur="7.2s" repeatCount="indefinite" begin="2.4s"/></circle>
  </g>

  <rect x="24" y="24" width="1132" height="{panel_h}" rx="18" fill="{t['panel']}" fill-opacity="0.55" stroke="{t['panel_stroke']}" stroke-opacity="{t['panel_stroke_op']}" stroke-width="1"/>
  <rect x="24" y="24" width="1132" height="{panel_h}" rx="18" fill="none" stroke="url(#borderShimmer)" stroke-width="1.4"/>

  <rect x="24" y="24" width="1132" height="38" rx="18" fill="{t['header']}"/>
  <rect x="24" y="42" width="1132" height="20" fill="{t['header']}"/>
  <circle cx="48" cy="43" r="6" fill="#FF5F56"/>
  <circle cx="68" cy="43" r="6" fill="#FFBD2E"/>
  <circle cx="88" cy="43" r="6" fill="#27C93F"/>
  <text x="590" y="47" text-anchor="middle" fill="{t['muted']}" font-size="12" font-family="'Courier New',monospace">yigit@dev: ~</text>
  <text x="{w - 44}" y="47" text-anchor="end" font-size="12" fill="{t['muted']}">{bucket['emoji']} {bucket['label']}</text>

  <text x="40" y="100" fill="{t['text']}" font-size="20" font-weight="600" opacity="0">Hi 👋<animate attributeName="opacity" values="0;1" dur="0.6s" begin="0.2s" fill="freeze"/></text>
  <text x="40" y="138" fill="{t['text']}" font-size="29" font-weight="700" opacity="0">I'm Yiğit Enes Kaya<animate attributeName="opacity" values="0;1" dur="0.6s" begin="0.7s" fill="freeze"/></text>

  <text x="40" y="174" font-family="'Courier New',monospace" font-size="18" fill="{t['muted']}" opacity="0">&gt;<animate attributeName="opacity" values="0;1" dur="0.4s" begin="1.2s" fill="freeze"/></text>

  <g clip-path="url(#phraseClip0)">
    <text x="72" y="174" font-family="'Courier New',monospace" font-size="18" font-weight="600" fill="url(#accentGrad)">Full-Stack Developer</text>
    <rect x="286" y="159" width="9" height="20" fill="{t['c2']}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="0.9s" repeatCount="indefinite"/></rect>
  </g>
  <g clip-path="url(#phraseClip1)">
    <text x="72" y="174" font-family="'Courier New',monospace" font-size="18" font-weight="600" fill="url(#accentGrad)">Fleet Management Builder</text>
    <rect x="318" y="159" width="9" height="20" fill="{t['c2']}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="0.9s" repeatCount="indefinite"/></rect>
  </g>
  <g clip-path="url(#phraseClip2)">
    <text x="72" y="174" font-family="'Courier New',monospace" font-size="18" font-weight="600" fill="url(#accentGrad)">B2B2C Product Enthusiast</text>
    <rect x="318" y="159" width="9" height="20" fill="{t['c2']}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="0.9s" repeatCount="indefinite"/></rect>
  </g>
  <g clip-path="url(#phraseClip3)">
    <text x="72" y="174" font-family="'Courier New',monospace" font-size="18" font-weight="600" fill="url(#accentGrad)">Open Source Contributor</text>
    <rect x="318" y="159" width="9" height="20" fill="{t['c2']}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="0.9s" repeatCount="indefinite"/></rect>
  </g>

  <line x1="40" y1="196" x2="560" y2="196" stroke="{t['muted']}" stroke-opacity="0.15"/>

  <g font-size="14">
    <text x="40" y="224" opacity="0" fill="{t['muted']}">📍 <tspan fill="{t['text']}">Türkiye · UTC+03:00</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.6s" fill="freeze"/></text>
    <text x="40" y="252" opacity="0" fill="{t['muted']}">💼 <tspan fill="{t['text']}">Odak: Filo Yönetimi &amp; B2B2C</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.75s" fill="freeze"/></text>
    <text x="40" y="280" opacity="0" fill="{t['muted']}">🔧 <tspan fill="{t['text']}">Geliştiriyor: React Native + Django</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="1.9s" fill="freeze"/></text>
    <text x="40" y="308" opacity="0" fill="{t['muted']}">📧 <tspan fill="{t['text']}">eneskaaya3@gmail.com</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="2.05s" fill="freeze"/></text>
  </g>

  <text x="600" y="100" fill="{t['muted']}" font-size="12" letter-spacing="2" opacity="0">SKILLS<animate attributeName="opacity" values="0;1" dur="0.5s" begin="2.2s" fill="freeze"/></text>

  <g font-family="'Courier New',monospace" font-size="12.5" font-weight="600">
{pills_svg}
  </g>

  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.1s" fill="freeze"/>
{spotify_block}
  </g>
</g>

<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    spotify = fetch_spotify()
    bucket = get_time_bucket()
    for theme in ("dark", "light"):
        svg = build_svg(theme, spotify, bucket)
        out_path = OUT_DIR / f"{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} :: spotify={'connected' if spotify else 'not configured'}, {bucket['emoji']} {bucket['label']}")


if __name__ == "__main__":
    main()
