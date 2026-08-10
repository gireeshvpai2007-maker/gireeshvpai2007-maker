import os
import json
import urllib.request
from datetime import datetime, timedelta


USERNAME = "gireeshvpai2007-maker"

GRAPHQL_URL = "https://api.github.com/graphql"
TOKEN = os.environ["GITHUB_TOKEN"]


def github_query(query):
    data = json.dumps({"query": query}).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-contribution-graph"
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


# ---------------------------------------------------------
# Get contribution data
# ---------------------------------------------------------

query = f"""
{{
  user(login: "{USERNAME}") {{
    name
    login
    createdAt

    contributionsCollection {{
      contributionCalendar {{
        totalContributions

        weeks {{
          contributionDays {{
            date
            contributionCount
          }}
        }}
      }}
    }}

    repositories(first: 1, ownerAffiliations: OWNER) {{
      totalCount
    }}
  }}
}}
"""

data = github_query(query)
user = data["user"]

calendar = user["contributionsCollection"]["contributionCalendar"]

days = []

for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        days.append({
            "date": day["date"],
            "count": day["contributionCount"]
        })


days.sort(key=lambda x: x["date"])


# ---------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------

def svg_header(width, height):
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}">

    <rect width="100%" height="100%" fill="#0d1117"/>
    '''


def svg_footer():
    return "</svg>"


def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------
# GRAPH 1
# Daily activity line graph
# ---------------------------------------------------------

recent = days[-30:]

WIDTH = 1000
HEIGHT = 430

LEFT = 80
RIGHT = 30
TOP = 90
BOTTOM = 60

plot_width = WIDTH - LEFT - RIGHT
plot_height = HEIGHT - TOP - BOTTOM

max_value = max([x["count"] for x in recent] + [1])

points = []

for i, item in enumerate(recent):

    if len(recent) == 1:
        x = LEFT
    else:
        x = LEFT + (i / (len(recent) - 1)) * plot_width

    y = TOP + plot_height - (
        item["count"] / max_value
    ) * plot_height

    points.append((x, y))


svg = svg_header(WIDTH, HEIGHT)

svg += f'''
<text
    x="{WIDTH / 2}"
    y="45"
    text-anchor="middle"
    fill="#79a7ff"
    font-family="Arial"
    font-size="22"
    font-weight="bold">
    {escape(user["name"] or USERNAME)}'s Contribution Graph
</text>
'''

# Grid lines

for i in range(7):

    y = TOP + (i / 6) * plot_height

    value = round(max_value - (i / 6) * max_value)

    svg += f'''
    <line
        x1="{LEFT}"
        y1="{y}"
        x2="{WIDTH - RIGHT}"
        y2="{y}"
        stroke="#30466f"
        stroke-width="1"
        stroke-dasharray="2 4"/>

    <text
        x="{LEFT - 12}"
        y="{y + 5}"
        text-anchor="end"
        fill="#79a7ff"
        font-family="Arial"
        font-size="12">
        {value}
    </text>
    '''

# Line

path = "M " + " L ".join(
    f"{x:.2f} {y:.2f}"
    for x, y in points
)

svg += f'''
<path
    d="{path}"
    fill="none"
    stroke="#79a7ff"
    stroke-width="4"
    stroke-linecap="round"
    stroke-linejoin="round"/>
'''

# Points

for x, y in points:

    svg += f'''
    <circle
        cx="{x}"
        cy="{y}"
        r="5"
        fill="#a9bde8"/>
    '''

# X labels

for i, item in enumerate(recent):

    x = points[i][0]

    date = datetime.strptime(
        item["date"],
        "%Y-%m-%d"
    )

    label = date.strftime("%d")

    svg += f'''
    <text
        x="{x}"
        y="{HEIGHT - 25}"
        text-anchor="middle"
        fill="#79a7ff"
        font-family="Arial"
        font-size="12">
        {label}
    </text>
    '''

svg += f'''
<text
    x="{WIDTH / 2}"
    y="{HEIGHT - 5}"
    text-anchor="middle"
    fill="#79a7ff"
    font-family="Arial"
    font-size="14">
    Days
</text>

<text
    x="20"
    y="{HEIGHT / 2}"
    transform="rotate(-90 20 {HEIGHT / 2})"
    text-anchor="middle"
    fill="#79a7ff"
    font-family="Arial"
    font-size="14">
    Contributions
</text>
'''

svg += svg_footer()

os.makedirs("assets", exist_ok=True)

with open(
    "assets/activity-graph.svg",
    "w",
    encoding="utf-8"
) as file:
    file.write(svg)


# ---------------------------------------------------------
# GRAPH 2
# Contribution Journey
# ---------------------------------------------------------

# Group contributions by month

monthly = {}

for item in days:

    month = item["date"][:7]

    monthly[month] = (
        monthly.get(month, 0) +
        item["count"]
    )


monthly_items = list(monthly.items())[-12:]

WIDTH = 1100
HEIGHT = 420

LEFT = 420
RIGHT = 70
TOP = 80
BOTTOM = 70

plot_width = WIDTH - LEFT - RIGHT
plot_height = HEIGHT - TOP - BOTTOM

max_month = max(
    [x[1] for x in monthly_items] + [1]
)

points = []

for i, (month, value) in enumerate(monthly_items):

    if len(monthly_items) == 1:
        x = LEFT
    else:
        x = LEFT + (
            i / (len(monthly_items) - 1)
        ) * plot_width

    y = TOP + plot_height - (
        value / max_month
    ) * plot_height

    points.append((x, y))


svg = svg_header(WIDTH, HEIGHT)

# Card

svg += '''
<rect
    x="20"
    y="20"
    width="1060"
    height="380"
    rx="12"
    fill="#161b26"/>
'''

svg += f'''
<text
    x="55"
    y="75"
    fill="#6fa0ff"
    font-family="Arial"
    font-size="28">
    {escape(USERNAME)}
</text>
'''

total = calendar["totalContributions"]

repos = user["repositories"]["totalCount"]

svg += f'''
<text
    x="55"
    y="125"
    fill="#27d7c2"
    font-family="Arial"
    font-size="18">
    ● {total} Contributions on GitHub
</text>

<text
    x="55"
    y="175"
    fill="#27d7c2"
    font-family="Arial"
    font-size="18">
    ▣ {repos} Public Repositories
</text>

<text
    x="55"
    y="225"
    fill="#27d7c2"
    font-family="Arial"
    font-size="18">
    ◷ GitHub Contribution Journey
</text>

<text
    x="55"
    y="275"
    fill="#27d7c2"
    font-family="Arial"
    font-size="18">
    ✦ Building every day
</text>
'''

# Chart title

svg += '''
<text
    x="800"
    y="70"
    text-anchor="middle"
    fill="#27d7c2"
    font-family="Arial"
    font-size="16">
    contributions in the last year
</text>
'''

# Baseline

base_y = TOP + plot_height

svg += f'''
<line
    x1="{LEFT}"
    y1="{base_y}"
    x2="{WIDTH - RIGHT}"
    y2="{base_y}"
    stroke="#27d7c2"
    stroke-width="2"/>
'''

# Filled area

if points:

    area = (
        f"M {points[0][0]} {base_y} "
        + " L ".join(
            f"{x} {y}"
            for x, y in points
        )
        + f" L {points[-1][0]} {base_y} Z"
    )

    svg += f'''
    <path
        d="{area}"
        fill="#b88cff"
        fill-opacity="0.85"/>
    '''

    # Line

    line = "M " + " L ".join(
        f"{x} {y}"
        for x, y in points
    )

    svg += f'''
    <path
        d="{line}"
        fill="none"
        stroke="#27d7c2"
        stroke-width="2"/>
    '''

# Y axis labels

for i in range(7):

    value = round(
        max_month -
        (i / 6) * max_month
    )

    y = TOP + (
        i / 6
    ) * plot_height

    svg += f'''
    <text
        x="{WIDTH - RIGHT + 10}"
        y="{y + 5}"
        fill="#27d7c2"
        font-family="Arial"
        font-size="13">
        {value}
    </text>
    '''

# X labels

for i, (month, _) in enumerate(monthly_items):

    x = points[i][0]

    dt = datetime.strptime(
        month,
        "%Y-%m"
    )

    label = dt.strftime("%y/%m")

    svg += f'''
    <text
        x="{x}"
        y="{base_y + 35}"
        text-anchor="middle"
        fill="#27d7c2"
        font-family="Arial"
        font-size="12">
        {label}
    </text>
    '''

svg += svg_footer()

with open(
    "assets/contribution-journey.svg",
    "w",
    encoding="utf-8"
) as file:
    file.write(svg)

print("Graphs generated successfully.")
