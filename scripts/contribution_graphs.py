import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = "gireeshvpai2007-maker"
TOKEN = os.environ["GITHUB_TOKEN"]
GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    repositories(first: 1, ownerAffiliations: OWNER) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

payload = json.dumps({"query": QUERY, "variables": {
    "login": USERNAME,
    "from": start.isoformat(),
    "to": now.isoformat(),
}}).encode("utf-8")

request = urllib.request.Request(
    GRAPHQL_URL,
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
start_date = start.date()
end_date = now.date()

all_days = []
for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        if start_date <= d <= end_date:
            all_days.append((day["date"], day["contributionCount"]))
all_days.sort()


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def smooth_path(points, tension=0.75):
    if len(points) < 2:
        return ""
    if len(points) == 2:
        return f"M {points[0][0]:.2f} {points[0][1]:.2f} L {points[1][0]:.2f} {points[1][1]:.2f}"
    path = f"M {points[0][0]:.2f} {points[0][1]:.2f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1x = p1[0] + (p2[0] - p0[0]) * tension / 6
        c1y = p1[1] + (p2[1] - p0[1]) * tension / 6
        c2x = p2[0] - (p3[0] - p1[0]) * tension / 6
        c2y = p2[1] - (p3[1] - p1[1]) * tension / 6
        path += f" C {c1x:.2f} {c1y:.2f}, {c2x:.2f} {c2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}"
    return path


def smooth_area_path(points, base_y, tension=0.75):
    if not points:
        return ""
    line = smooth_path(points, tension)
    first = f"M {points[0][0]:.2f} {points[0][1]:.2f}"
    body = line[len(first):] if line.startswith(first) else line
    return f"M {points[0][0]:.2f} {base_y:.2f} L {points[0][0]:.2f} {points[0][1]:.2f} {body} L {points[-1][0]:.2f} {base_y:.2f} Z"


def month_shift(year, month, offset):
    index = year * 12 + month - 1 + offset
    return index // 12, index % 12 + 1


def month_key(year, month):
    return f"{year:04d}-{month:02d}"


def journey_curve(points, top_y, base_y):
    """Smooth monthly curve with control points clamped to chart bounds."""
    n = len(points)
    if n < 2:
        return ""
    if n == 2:
        return f"M {points[0][0]:.2f} {points[0][1]:.2f} L {points[1][0]:.2f} {points[1][1]:.2f}"
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    h = [x[i + 1] - x[i] for i in range(n - 1)]
    delta = [(y[i + 1] - y[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0] = delta[0]
    m[-1] = delta[-1]
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])

    def clamp(v):
        return max(top_y, min(base_y, v))

    path = f"M {x[0]:.2f} {y[0]:.2f}"
    for i in range(n - 1):
        dx = h[i]
        c1y = clamp(y[i] + m[i] * dx / 3)
        c2y = clamp(y[i + 1] - m[i + 1] * dx / 3)
        path += f" C {x[i] + dx / 3:.2f} {c1y:.2f}, {x[i + 1] - dx / 3:.2f} {c2y:.2f}, {x[i + 1]:.2f} {y[i + 1]:.2f}"
    return path


def journey_area(points, top_y, base_y):
    line = journey_curve(points, top_y, base_y)
    first = f"M {points[0][0]:.2f} {points[0][1]:.2f}"
    body = line[len(first):] if line.startswith(first) else line
    return f"M {points[0][0]:.2f} {base_y:.2f} L {points[0][0]:.2f} {points[0][1]:.2f} {body} L {points[-1][0]:.2f} {base_y:.2f} Z"


def styles():
    return """
<style>
.card{fill:#191b29}.title{font:700 21px Arial,sans-serif;fill:#6fa0ff}
.axis-label,.x-label,.label{font:13px Arial,sans-serif;fill:#6fa0ff}
.grid{stroke:#30466f;stroke-width:1;stroke-dasharray:2 4}
.line{fill:none;stroke:#79a7ff;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.area{fill:#79a7ff;opacity:.08}.point{fill:#a9bde8}
.username{font:32px Arial,sans-serif;fill:#6fa0ff}.stat{font:18px Arial,sans-serif;fill:#27d7c2}
.chart-title{font:13px Arial,sans-serif;fill:#27d7c2}
.journey-line{fill:none;stroke:#27d7c2;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.journey-area{fill:#b88cff;opacity:.85}.journey-point{fill:#27d7c2}
</style>
"""


def write_activity_graph():
    # Preserve the existing preferred activity graph.
    days = all_days[-31:]
    width, height = 1100, 460
    left, right, top, bottom = 80, 35, 85, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_count = max([c for _, c in days] + [1])
    points = []
    for i, (d, count) in enumerate(days):
        x = left if len(days) == 1 else left + i / (len(days) - 1) * plot_w
        y = top + plot_h - count / max_count * plot_h
        points.append((x, y, d, count))
    xy = [(x, y) for x, y, _, _ in points]
    path = smooth_path(xy)
    base_y = top + plot_h
    area = smooth_area_path(xy, base_y)
    grid = []
    for i in range(7):
        y = top + i / 6 * plot_h
        value = round(max_count - i / 6 * max_count)
        grid.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        grid.append(f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" class="axis-label">{value}</text>')
    labels = []
    for i, (x, _, d, _) in enumerate(points):
        if i % 2 == 0 or i == len(points) - 1:
            dt = datetime.strptime(d, "%Y-%m-%d")
            labels.append(f'<text x="{x:.2f}" y="{height - 25}" text-anchor="middle" class="x-label">{dt.strftime("%d")}</text>')
    circles = [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" class="point"><title>{esc(d)}: {count} contributions</title></circle>' for x, y, d, count in points]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{styles()}<rect width="100%" height="100%" class="card"/>
<text x="{width/2}" y="48" text-anchor="middle" class="title">{esc(user['name'] or USERNAME).upper()}'s Contribution Graph</text>
{''.join(grid)}<path d="{area}" class="area"/><path d="{path}" class="line"/>{''.join(circles)}{''.join(labels)}
<text x="{width/2}" y="{height - 5}" text-anchor="middle" class="axis-label">Days</text>
<text x="20" y="{height/2}" transform="rotate(-90 20 {height/2})" text-anchor="middle" class="axis-label">Contributions</text></svg>'''
    with open("assets/activity-graph.svg", "w", encoding="utf-8") as f:
        f.write(svg)


def write_journey_graph():
    # Exactly 12 calendar months: current month + previous 11 months.
    # This fixes the previous 13-label rolling-window bug.
    month_keys = [month_key(*month_shift(now.year, now.month, offset)) for offset in range(-11, 1)]
    monthly = {key: 0 for key in month_keys}
    for d, count in all_days:
        if d[:7] in monthly:
            monthly[d[:7]] += count
    items = [(key, monthly[key]) for key in month_keys]

    width, height = 1100, 420
    left, right, top, bottom = 450, 70, 80, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    base_y = top + plot_h
    max_value = max([v for _, v in items] + [1])

    points = []
    for i, (month, value) in enumerate(items):
        x = left if len(items) == 1 else left + i / (len(items) - 1) * plot_w
        y = base_y - value / max_value * plot_h
        points.append((x, y, month, value))

    xy = [(x, y) for x, y, _, _ in points]
    line = journey_curve(xy, top, base_y)
    area = journey_area(xy, top, base_y)

    y_axis = []
    for i in range(5):
        fraction = i / 4
        y = top + fraction * plot_h
        value = round(max_value * (1 - fraction))
        y_axis.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/><text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" class="axis-label">{value}</text>')

    labels = []
    for x, _, month, _ in points:
        dt = datetime.strptime(month, "%Y-%m")
        labels.append(f'<text x="{x:.2f}" y="{base_y + 35}" text-anchor="middle" class="label">{dt.strftime("%y/%m")}</text>')

    point_svg = [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" class="journey-point"><title>{esc(month)}: {value} contributions</title></circle>' for x, y, month, value in points]
    total = calendar["totalContributions"]
    repos = user["repositories"]["totalCount"]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{styles()}<defs><clipPath id="journeyPlot"><rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}"/></clipPath></defs>
<rect width="100%" height="100%" rx="12" class="card"/><rect x="20" y="20" width="1060" height="380" rx="12" fill="#191b29"/>
<text x="55" y="75" class="username">{esc(USERNAME)}</text>
<text x="55" y="125" class="stat">◉ {total} Contributions on GitHub</text>
<text x="55" y="175" class="stat">▣ {repos} Public Repositories</text>
<text x="55" y="225" class="stat">◷ Contribution Journey</text>
<text x="55" y="275" class="stat">✦ Building every day</text>
<text x="820" y="70" text-anchor="middle" class="chart-title">contributions in the last year</text>
{''.join(y_axis)}<g clip-path="url(#journeyPlot)"><path d="{area}" class="journey-area"/><path d="{line}" class="journey-line"/></g>
{''.join(point_svg)}{''.join(labels)}</svg>'''
    with open("assets/contribution-journey.svg", "w", encoding="utf-8") as f:
        f.write(svg)


os.makedirs("assets", exist_ok=True)
write_activity_graph()
write_journey_graph()
print("Generated activity-graph.svg and corrected contribution-journey.svg")
