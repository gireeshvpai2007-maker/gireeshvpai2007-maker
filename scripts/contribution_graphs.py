import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "gireeshvpai2007-maker"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    createdAt
    repositories(first: 1, ownerAffiliations: OWNER) {
      totalCount
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

payload = json.dumps({
    "query": QUERY,
    "variables": {
        "login": USERNAME,
        "from": start.isoformat(),
        "to": now.isoformat(),
    },
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gireeshvpai2007-maker-profile",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"], indent=2))

user = result["data"]["user"]
calendar = user["contributionsCollection"]["contributionCalendar"]

all_days = []
for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        all_days.append((day["date"], day["contributionCount"]))

all_days.sort()


def esc(value):
    return (str(value).replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def write_activity_graph():
    # Last 31 days: the line graph shown in the user's reference image.
    days = all_days[-31:]
    width, height = 1100, 460
    left, right, top, bottom = 80, 35, 85, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_count = max([c for _, c in days] + [1])

    points = []
    for i, (date, count) in enumerate(days):
        x = left if len(days) == 1 else left + i / (len(days) - 1) * plot_w
        y = top + plot_h - (count / max_count) * plot_h
        points.append((x, y, date, count))

    path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y, _, _ in points)
    base_y = top + plot_h
    area = f"M {points[0][0]:.2f} {base_y:.2f} " + " L ".join(
        f"{x:.2f} {y:.2f}" for x, y, _, _ in points
    ) + f" L {points[-1][0]:.2f} {base_y:.2f} Z"

    grid = []
    for i in range(7):
        y = top + i / 6 * plot_h
        value = round(max_count - i / 6 * max_count)
        grid.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        grid.append(f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" class="axis-label">{value}</text>')

    labels = []
    for i, (x, _, date, _) in enumerate(points):
        if i % 1 == 0:
            dt = datetime.strptime(date, "%Y-%m-%d")
            labels.append(f'<text x="{x:.2f}" y="{height - 25}" text-anchor="middle" class="x-label">{dt.strftime("%d")}</text>')

    circles = []
    for x, y, date, count in points:
        circles.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" class="point">'
            f'<title>{esc(date)}: {count} contributions</title></circle>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#191b29"/>
<style>
.title {{ font: 700 21px Arial,sans-serif; fill:#6fa0ff; }}
.axis-label,.x-label {{ font: 13px Arial,sans-serif; fill:#6fa0ff; }}
.grid {{ stroke:#30466f; stroke-width:1; stroke-dasharray:2 4; }}
.line {{ fill:none; stroke:#79a7ff; stroke-width:4; stroke-linecap:round; stroke-linejoin:round; }}
.area {{ fill:#79a7ff; opacity:.10; }}
.point {{ fill:#a9bde8; }}
</style>
<text x="{width/2}" y="48" text-anchor="middle" class="title">{esc((user['name'] or USERNAME).upper())}'s Contribution Graph</text>
{''.join(grid)}
<path d="{area}" class="area"/>
<path d="{path}" class="line"/>
{''.join(circles)}
{''.join(labels)}
<text x="{width/2}" y="{height - 5}" text-anchor="middle" class="axis-label">Days</text>
<text x="20" y="{height/2}" transform="rotate(-90 20 {height/2})" text-anchor="middle" class="axis-label">Contributions</text>
</svg>'''

    with open("assets/activity-graph.svg", "w", encoding="utf-8") as f:
        f.write(svg)


def write_journey_graph():
    monthly = {}
    for date, count in all_days:
        month = date[:7]
        monthly[month] = monthly.get(month, 0) + count

    items = sorted(monthly.items())[-12:]
    width, height = 1100, 420
    left, right, top, bottom = 430, 70, 80, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_value = max([v for _, v in items] + [1])

    points = []
    for i, (month, value) in enumerate(items):
        x = left if len(items) == 1 else left + i / (len(items) - 1) * plot_w
        y = top + plot_h - value / max_value * plot_h
        points.append((x, y, month, value))

    base_y = top + plot_h
    line = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y, _, _ in points)
    area = f"M {points[0][0]:.2f} {base_y:.2f} " + " L ".join(
        f"{x:.2f} {y:.2f}" for x, y, _, _ in points
    ) + f" L {points[-1][0]:.2f} {base_y:.2f} Z"

    labels = []
    for x, _, month, _ in points:
        dt = datetime.strptime(month, "%Y-%m")
        labels.append(f'<text x="{x:.2f}" y="{base_y + 35}" text-anchor="middle" class="label">{dt.strftime("%y/%m")}</text>')

    total = calendar["totalContributions"]
    repos = user["repositories"]["totalCount"]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="12" fill="#0d1117"/>
<rect x="20" y="20" width="1060" height="380" rx="12" fill="#191b29"/>
<style>
.username {{ font:32px Arial,sans-serif; fill:#6fa0ff; }}
.stat {{ font:18px Arial,sans-serif; fill:#27d7c2; }}
.chart-title,.label {{ font:13px Arial,sans-serif; fill:#27d7c2; }}
.axis {{ stroke:#27d7c2; stroke-width:2; }}
.journey-line {{ fill:none; stroke:#27d7c2; stroke-width:2; }}
.area {{ fill:#b88cff; opacity:.85; }}
</style>
<text x="55" y="75" class="username">{esc(USERNAME)}</text>
<text x="55" y="125" class="stat">◉ {total} Contributions on GitHub</text>
<text x="55" y="175" class="stat">▣ {repos} Public Repositories</text>
<text x="55" y="225" class="stat">◷ Contribution Journey</text>
<text x="55" y="275" class="stat">✦ Building every day</text>
<text x="800" y="70" text-anchor="middle" class="chart-title">contributions in the last year</text>
<line x1="{left}" y1="{base_y}" x2="{left + plot_w}" y2="{base_y}" class="axis"/>
<path d="{area}" class="area"/>
<path d="{line}" class="journey-line"/>
{''.join(labels)}
</svg>'''

    with open("assets/contribution-journey.svg", "w", encoding="utf-8") as f:
        f.write(svg)


os.makedirs("assets", exist_ok=True)
write_activity_graph()
write_journey_graph()
print("Generated activity-graph.svg and contribution-journey.svg")
