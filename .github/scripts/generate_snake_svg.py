#!/usr/bin/env python3

import os
import sys
import argparse
import requests
import svgwrite

GQL_URL = "https://api.github.com/graphql"

GRAPHQL_QUERY = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

def fetch_calendar(username, token):
    headers = {"Authorization": f"bearer {token}"}
    resp = requests.post(
        GQL_URL,
        json={"query": GRAPHQL_QUERY, "variables": {"login": username}},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    grid = []
    for week in weeks:
        col = []
        for d in week["contributionDays"]:
            col.append({
                "date": d["date"],
                "count": d["contributionCount"],
                "color": d["color"] if d["color"] else "#161b22"
            })
        grid.append(col)
    return grid

def build_svg(grid, out_path, cell=12, gap=3, margin=20):
    cols = len(grid)
    rows = 7
    width = margin * 2 + cols * (cell + gap)
    height = margin * 2 + rows * (cell + gap) + 80

    dwg = svgwrite.Drawing(out_path, size=(f"{width}px", f"{height}px"), profile='full')
    defs = dwg.defs

    grad = dwg.linearGradient((0,0), (1,1), id="snakeGrad")
    grad.add_stop_color(0, "#ffb84d")
    grad.add_stop_color(1, "#ff7a00")
    defs.add(grad)

    dwg.add(dwg.rect(insert=(0,0), size=(width, height), fill="none"))

    dwg.add(dwg.text(
        "snake contribution graph",
        insert=(width/2, 40),
        text_anchor="middle",
        font_size=26,
        fill="#e5e7eb",
        font_family="Inter, Arial, sans-serif",
        font_weight="600"
    ))

    coords = []
    for c in range(cols):
        x = margin + c * (cell + gap)
        col_coords = []
        for r in range(rows):
            y = margin + 50 + r * (cell + gap)
            col_coords.append((x, y))
        coords.append(col_coords)

    for c in range(cols):
        for r in range(rows):
            x, y = coords[c][r]
            day = grid[c][r]
            color = day["color"]
            op = 0.28 if day["count"] == 0 else min(0.22 + day["count"] * 0.07, 1)
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(cell, cell),
                rx=3, ry=3,
                fill=color,
                opacity=op
            ))

    pts = []
    for c in range(cols):
        row_order = list(range(rows)) if c % 2 == 0 else list(range(rows - 1, -1, -1))
        for r in row_order:
            cx, cy = coords[c][r]
            pts.append((cx + cell/2, cy + cell/2))

    def bezier_path(points, smooth=0.35):
        if not points:
            return ""
        d = f"M {points[0][0]},{points[0][1]} "
        for i in range(1, len(points)):
            px, py = points[i - 1]
            cx = px + (points[i][0] - px) * smooth
            cy = py + (points[i][1] - py) * smooth
            d += f"Q {cx},{cy} {points[i][0]},{points[i][1]} "
        return d

    d_path = bezier_path(pts)

    dwg.add(dwg.path(
        d=d_path,
        fill="none",
        stroke="rgba(0,0,0,0.55)",
        stroke_width=22,
        stroke_linecap="round",
        stroke_linejoin="round",
        opacity=0.45
    ))

    dwg.add(dwg.path(
        d=d_path,
        fill="none",
        stroke="url(#snakeGrad)",
        stroke_width=16,
        stroke_linecap="round",
        stroke_linejoin="round"
    ))

    dwg.add(dwg.path(
        d=d_path,
        fill="none",
        stroke="rgba(255,255,255,0.45)",
        stroke_width=3,
        stroke_linecap="round",
        stroke_linejoin="round",
        opacity=0.6
    ))

    if pts:
        hx, hy = pts[-1]
        dwg.add(dwg.circle(center=(hx, hy), r=10, fill="#ffcc00"))
        dwg.add(dwg.circle(center=(hx + 4, hy - 3), r=2.2, fill="#111827"))

    if pts:
        mx, my = pts[len(pts)//2]
        dwg.add(dwg.ellipse(center=(mx, my+18), r=(80, 12), fill="rgba(0,0,0,0.24)", opacity=0.6))

    dwg.save()
    print(f"Saved SVG → {out_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is missing", file=sys.stderr)
        sys.exit(2)

    grid = fetch_calendar(args.user, token)
    build_svg(grid, args.out)

if __name__ == "__main__":
    main()
