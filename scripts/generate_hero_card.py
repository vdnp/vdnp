#!/usr/bin/env python3
"""Generate the profile hero card (dark.svg / light.svg): greeting, typing
role rotation, quick info, skill pills — plus a live 'Şu An Dinliyorum'
Spotify strip at the bottom (via the user's own Spotify Web API app, not
any third-party proxy, since those tend to shut down).

If Spotify secrets aren't configured (or the API call fails), the strip
falls back to a neutral "not connected" line instead of breaking the card.

Run manually:  python scripts/generate_hero_card.py
Run by CI:     see .github/workflows/dynamic-readme.yml
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- Spotify --

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
                        return dict(playing=True, track=item["name"],
                                    artist=", ".join(a["name"] for a in item["artists"]))
        except urllib.error.HTTPError:
            pass

        req2 = urllib.request.Request("https://api.spotify.com/v1/me/player/recently-played?limit=1", headers=auth)
        with urllib.request.urlopen(req2, timeout=8) as r:
            data = json.loads(r.read().decode())
            items = data.get("items", [])
            if items:
                item = items[0]["track"]
                return dict(playing=False, track=item["name"],
                            artist=", ".join(a["name"] for a in item["artists"]))
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


def build_svg(theme_name, spotify):
    t = THEMES[theme_name]
    w, h = 1180, 380

    pill_state = {"seen": []}
    rows = []
    rows += build_pill_row(t, SKILLS_ROW1, 600, 112, pill_state)
    rows += build_pill_row(t, SKILLS_ROW2, 600, 152, pill_state)
    rows += build_pill_row(t, SKILLS_ROW3, 600, 192, pill_state)
    pills_svg = "\n".join(rows)

    if spotify:
        verb = "Şu an dinliyor" if spotify["playing"] else "Son dinlediği"
        track = spotify["track"]
        if len(track) > 40:
            track = track[:39].rstrip() + "…"
        artist = spotify["artist"]
        if len(artist) > 30:
            artist = artist[:29].rstrip() + "…"
        spotify_text = f'{verb}: <tspan fill="{t["text"]}" font-weight="700">{esc(track)}</tspan> — {esc(artist)}'
        bars_anim = True
    else:
        spotify_text = "Spotify henüz bağlanmadı"
        bars_anim = False

    bars = ""
    if bars_anim:
        bar_specs = [(0, "0.9s"), (5, "0.7s"), (10, "1.1s")]
        bar_svgs = []
        for dx, dur in bar_specs:
            bar_svgs.append(
                f'<rect x="{40 + dx}" y="342" width="3" height="10" fill="url(#accentGrad)">'
                f'<animate attributeName="height" values="6;16;6" dur="{dur}" repeatCount="indefinite"/>'
                f'<animate attributeName="y" values="345;337;345" dur="{dur}" repeatCount="indefinite"/></rect>'
            )
        bars = "".join(bar_svgs)
    else:
        bars = f'<circle cx="47" cy="347" r="3" fill="{t["muted"]}"/>'

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

  <rect x="24" y="24" width="1132" height="332" rx="18" fill="{t['panel']}" fill-opacity="0.55" stroke="{t['panel_stroke']}" stroke-opacity="{t['panel_stroke_op']}" stroke-width="1"/>
  <rect x="24" y="24" width="1132" height="332" rx="18" fill="none" stroke="url(#borderShimmer)" stroke-width="1.4"/>

  <rect x="24" y="24" width="1132" height="38" rx="18" fill="{t['header']}"/>
  <rect x="24" y="42" width="1132" height="20" fill="{t['header']}"/>
  <circle cx="48" cy="43" r="6" fill="#FF5F56"/>
  <circle cx="68" cy="43" r="6" fill="#FFBD2E"/>
  <circle cx="88" cy="43" r="6" fill="#27C93F"/>
  <text x="590" y="47" text-anchor="middle" fill="{t['muted']}" font-size="12" font-family="'Courier New',monospace">yigit@dev: ~</text>

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

  <line x1="40" y1="326" x2="1140" y2="326" stroke="{t['muted']}" stroke-opacity="0.15"/>
  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.1s" fill="freeze"/>
    {bars}
    <text x="60" y="350" font-size="13" fill="{t['muted']}">🎧 {spotify_text}</text>
  </g>
</g>

<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    spotify = fetch_spotify()
    for theme in ("dark", "light"):
        svg = build_svg(theme, spotify)
        out_path = OUT_DIR / f"{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} :: spotify={'connected' if spotify else 'not configured'}")


if __name__ == "__main__":
    main()
