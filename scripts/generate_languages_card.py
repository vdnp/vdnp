#!/usr/bin/env python3
"""Generate a 'language breakdown' SVG card (dark + light): a stacked bar +
legend showing the real byte-weighted language mix across all of the user's
public, non-fork repos (GitHub's own /languages endpoint per repo, summed).

Run manually:  python scripts/generate_languages_card.py
Run by CI:     see .github/workflows/dynamic-readme.yml
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

GITHUB_USERNAME = "vdnp"
OUT_DIR = Path(__file__).resolve().parent.parent
MAX_LANGS = 7

# GitHub linguist-style colors for common languages; unknown languages fall
# back to a neutral grey so the bar never breaks.
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "C#": "#178600", "HTML": "#e34c26", "CSS": "#563d7c", "SCSS": "#c6538c",
    "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584", "PHP": "#4F5D95",
    "Ruby": "#701516", "Swift": "#F05138", "Kotlin": "#A97BFF", "C++": "#f34b7d",
    "C": "#555555", "Shell": "#89e051", "Dockerfile": "#384d54", "Vue": "#41b883",
    "Dart": "#00B4AB", "EJS": "#a91e50",
}


def api_headers():
    h = {"User-Agent": "vdnp-readme-bot", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    return h


def get_json(url):
    req = urllib.request.Request(url, headers=api_headers())
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_language_totals():
    totals = {}
    try:
        repos = get_json(
            f"https://api.github.com/users/{GITHUB_USERNAME}/repos?type=owner&per_page=100"
        )
        for repo in repos:
            if repo.get("fork") or repo.get("archived") or repo.get("size", 0) == 0:
                continue
            try:
                langs = get_json(repo["languages_url"])
            except Exception:
                continue
            for lang, byte_count in langs.items():
                totals[lang] = totals.get(lang, 0) + byte_count
    except Exception:
        return {}
    return totals


def top_languages(totals):
    if not totals:
        return []
    total_bytes = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:MAX_LANGS]
    other_bytes = sum(v for _, v in ranked[MAX_LANGS:])
    result = [(name, bytes_ / total_bytes * 100) for name, bytes_ in top]
    if other_bytes > 0:
        result.append(("Diğer", other_bytes / total_bytes * 100))
    return result


THEMES = {
    "dark": dict(bg="#030712", panel="#0F172A", panel_op="0.55", text="#F8FAFC", muted="#94A3B8",
                 c1="#7C3AED", c2="#22D3EE", c3="#10B981",
                 outer_stroke="#FFFFFF", outer_op="0.06", panel_stroke="#FFFFFF", panel_stroke_op="0.08",
                 track="#FFFFFF", track_op="0.06", other_color="#475569"),
    "light": dict(bg="#FFFFFF", panel="#F8FAFC", panel_op="0.8", text="#0F172A", muted="#475569",
                  c1="#2563EB", c2="#06B6D4", c3="#10B981",
                  outer_stroke="#0F172A", outer_op="0.06", panel_stroke="#0F172A", panel_stroke_op="0.08",
                  track="#0F172A", track_op="0.05", other_color="#94A3B8"),
}


def build_svg(theme_name, langs):
    t = THEMES[theme_name]
    w = 1180
    bar_x, bar_y, bar_w, bar_h = 42, 76, w - 84, 22

    if not langs:
        body = (
            f'  <text x="{w/2}" y="{bar_y + 16}" text-anchor="middle" font-size="13" '
            f'fill="{t["muted"]}">Dil istatistikleri güncelleniyor…</text>'
        )
        h = 140
    else:
        segments = []
        legend = []
        x = bar_x
        cols = 4
        for i, (name, pct) in enumerate(langs):
            seg_w = bar_w * (pct / 100)
            color = LANG_COLORS.get(name, t["other_color"])
            begin = 0.2 + i * 0.12
            segments.append(
                f'    <rect x="{x:.1f}" y="{bar_y}" width="0" height="{bar_h}" fill="{color}">'
                f'<animate attributeName="width" values="0;{seg_w:.1f}" dur="0.6s" begin="{begin:.2f}s" fill="freeze"/></rect>'
            )
            x += seg_w

            col = i % cols
            row = i // cols
            lx = bar_x + col * ((bar_w) / cols)
            ly = bar_y + bar_h + 34 + row * 26
            legend.append(
                f'  <g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="{begin + 0.15:.2f}s" fill="freeze"/>\n'
                f'    <rect x="{lx:.1f}" y="{ly - 11}" width="11" height="11" rx="3" fill="{color}"/>\n'
                f'    <text x="{lx + 18:.1f}" y="{ly - 1}" font-size="12.5" fill="{t["text"]}">{name} <tspan fill="{t["muted"]}">{pct:.1f}%</tspan></text>\n'
                '  </g>'
            )
        rows_count = (len(langs) + cols - 1) // cols
        h = bar_y + bar_h + 34 + rows_count * 26 + 20
        body = (
            f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="11" fill="{t["track"]}" fill-opacity="{t["track_op"]}"/>\n'
            + "\n".join(segments) + "\n" + "\n".join(legend)
        )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif">
<defs>
  <clipPath id="cardClip"><rect x="0" y="0" width="{w}" height="{h}" rx="24"/></clipPath>
  <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="{t['c1']}"><animate attributeName="stop-color" values="{t['c1']};{t['c2']};{t['c3']};{t['c1']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="50%" stop-color="{t['c2']}"><animate attributeName="stop-color" values="{t['c2']};{t['c3']};{t['c1']};{t['c2']}" dur="8s" repeatCount="indefinite"/></stop>
    <stop offset="100%" stop-color="{t['c3']}"><animate attributeName="stop-color" values="{t['c3']};{t['c1']};{t['c2']};{t['c3']}" dur="8s" repeatCount="indefinite"/></stop>
  </linearGradient>
  <linearGradient id="borderShimmer" gradientUnits="userSpaceOnUse" x1="-300" y1="0" x2="100" y2="0">
    <stop offset="0%" stop-color="{t['c1']}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{t['c2']}" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="{t['c3']}" stop-opacity="0"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;1480 0;0 0" dur="7s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="24" fill="{t['bg']}"/>
<g clip-path="url(#cardClip)">
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="{t['panel']}" fill-opacity="{t['panel_op']}" stroke="{t['panel_stroke']}" stroke-opacity="{t['panel_stroke_op']}" stroke-width="1"/>
  <rect x="12" y="12" width="{w - 24}" height="{h - 24}" rx="18" fill="none" stroke="url(#borderShimmer)" stroke-width="1.4"/>
  <text x="42" y="38" font-size="11" letter-spacing="2" fill="{t['muted']}">DİL DAĞILIMI · tüm public repolar</text>
{body}
</g>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="23" fill="none" stroke="{t['outer_stroke']}" stroke-opacity="{t['outer_op']}"/>
</svg>
'''


def main():
    totals = fetch_language_totals()
    langs = top_languages(totals)
    for theme in ("dark", "light"):
        svg = build_svg(theme, langs)
        out_path = OUT_DIR / f"langs-{theme}.svg"
        out_path.write_text(svg, encoding="utf-8")
        print(f"wrote {out_path} ({len(langs)} languages)")


if __name__ == "__main__":
    main()
