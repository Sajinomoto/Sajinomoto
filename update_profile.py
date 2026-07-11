import datetime
import os
import urllib.request
import json
import re

# Constants
USER_NAME = "Sajinomoto"
CREATION_DATE = datetime.datetime(2019, 4, 11)  # April 11, 2019

def load_ascii_art(filepath):
    try:
        with open(filepath) as f:
            lines = [line.rstrip('\r\n') for line in f]
    except Exception as e:
        print(f"Error reading ASCII file: {e}")
        return []

    if len(lines) < 3:
        return lines

    # Skip first and last line (top/bottom borders)
    content_lines = lines[1:-1]

    # Strip rightmost 4 characters of each line (right border)
    cleaned_lines = [line[:-4] if len(line) >= 4 else line for line in content_lines]
            
    # Find bounding box of non-space lines
    non_empty_indices = []
    for idx, line in enumerate(cleaned_lines):
        if line.strip(): # contains non-whitespace characters
            non_empty_indices.append(idx)
            
    if not non_empty_indices:
        return []
        
    start_row = min(non_empty_indices)
    end_row = max(non_empty_indices)
    
    min_col = 9999
    max_col = 0
    for r in range(start_row, end_row + 1):
        line = cleaned_lines[r]
        non_space = [c_idx for c_idx, char in enumerate(line) if char != ' ']
        if non_space:
            min_col = min(min_col, min(non_space))
            max_col = max(max_col, max(non_space))
            
    cropped_lines = []
    for r in range(start_row, end_row + 1):
        cropped_lines.append(cleaned_lines[r][min_col:max_col+1])
        
    return cropped_lines

def get_uptime(creation_date):
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    years = now.year - creation_date.year
    months = now.month - creation_date.month
    days = now.day - creation_date.day
    
    if days < 0:
        # borrow from previous month
        # get last day of previous month
        prev_month = now.replace(day=1) - datetime.timedelta(days=1)
        days += prev_month.day
        months -= 1
        
    if months < 0:
        months += 12
        years -= 1
        
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
        
    return ", ".join(parts) if parts else "0 days"

def get_github_stats():
    # Cache / fallback values
    stats = {
        "repos": 23,
        "stars": 3,
        "commits": 383,
        "followers": 26,
        "contributed": 25,
        "loc": 12500,
        "loc_add": 15400,
        "loc_del": 2900
    }
    
    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
        
    # Set User-Agent to avoid API block
    headers["User-Agent"] = "Sajinomoto-Profile-Updater"
        
    try:
        # Fetch general profile info
        req = urllib.request.Request(f"https://api.github.com/users/{USER_NAME}", headers=headers)
        with urllib.request.urlopen(req) as response:
            user_data = json.loads(response.read().decode())
            stats["followers"] = user_data.get("followers", stats["followers"])
            stats["repos"] = user_data.get("public_repos", stats["repos"])
            
        # Fetch repos to sum stars
        req = urllib.request.Request(f"https://api.github.com/users/{USER_NAME}/repos?per_page=100", headers=headers)
        with urllib.request.urlopen(req) as response:
            repos_data = json.loads(response.read().decode())
            stats["stars"] = sum(repo.get("stargazers_count", 0) for repo in repos_data)
            
        # Fetch commits count using Search API
        req_url = f"https://api.github.com/search/commits?q=author:{USER_NAME}"
        req = urllib.request.Request(req_url, headers={**headers, "Accept": "application/vnd.github.cloak-preview"})
        with urllib.request.urlopen(req) as response:
            search_data = json.loads(response.read().decode())
            stats["commits"] = search_data.get("total_count", stats["commits"])
            
    except Exception as e:
        print(f"Warning: Failed to fetch dynamic stats: {e}. Using cache/fallback values.")
        
    return stats

def justify_dots(key_text, value_text, max_len=58):
    current_len = len(key_text) + len(str(value_text))
    needed = max_len - current_len
    if needed <= 1:
        return " "
    return " " + ("." * (needed - 2)) + " "

def format_stat_line(x, y, key_path, value, max_len=58):
    if len(key_path) == 1:
        key_str = key_path[0]
        key_span = f'<tspan class="key">{key_str}</tspan>'
    else:
        key_span = f'<tspan class="key">{key_path[0]}</tspan>.<tspan class="key">{key_path[1]}</tspan>'
        key_str = f"{key_path[0]}.{key_path[1]}"
        
    full_key = f". {key_str}:"
    dots = justify_dots(full_key, str(value), max_len)
    
    return f'<tspan x="{x}" y="{y}" class="cc">. </tspan>{key_span}:<tspan class="cc">{dots}</tspan><tspan class="value">{value}</tspan>'

def generate_svg(filename, theme, ascii_art, stats):
    # Theme configuration
    if theme == "dark":
        bg_color = "#161b22"
        text_color = "#c9d1d9"
        key_color = "#ffa657"
        value_color = "#a5d6ff"
        dots_color = "#616e7f"
        add_color = "#3fb950"
        del_color = "#f85149"
    else: # light theme
        bg_color = "#ffffff"
        text_color = "#24292f"
        key_color = "#b85c00"
        value_color = "#004880"
        dots_color = "#8c9ba5"
        add_color = "#1a7f37"
        del_color = "#cf222e"
        
    # Calculate Uptime
    uptime_val = get_uptime(CREATION_DATE)
    
    # Calculate right-side stats starting x
    # Monospace characters at 8px font-size are approx 4.8px wide
    # Max width of ASCII is 84 characters. 84 * 4.8 = ~403px.
    # We add 25px left margin, so right side stats can start at x=450px.
    stats_x = 450
    
    # Calculate total height of the card
    # 61 lines of ASCII * 9.5px = 580px height
    # Let's add 30px padding on top and bottom -> height = 640px.
    # Width of the card can be 1040px to give plenty of space on the right (1040 - 450 = 590px for stats)
    card_width = 1040
    card_height = 640
    
    # Write SVG Header
    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{card_width}px" height="{card_height}px" font-size="15px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {key_color};}}
.value {{fill: {value_color};}}
.addColor {{fill: {add_color};}}
.delColor {{fill: {del_color};}}
.cc {{fill: {dots_color};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="{card_width}px" height="{card_height}px" fill="{bg_color}" rx="15"/>
"""

    # 1. Draw ASCII Art on the left
    # Font size is 8px, line spacing is 9.5px
    # Starts at y = 30
    svg += f'<text x="25" y="30" fill="{text_color}" font-size="8px" font-weight="bold" class="ascii">\n'
    for idx, line in enumerate(ascii_art):
        y_pos = 30 + (idx * 9.5)
        # Escape XML entities in ASCII
        escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        svg += f'<tspan x="25" y="{y_pos:.2f}">{escaped_line}</tspan>\n'
    svg += '</text>\n'
    
    # 2. Draw Stats on the right
    # Font size is 15px, line spacing is 23px
    # Starts at y = 45
    # Max length of right column lines: 52 chars
    svg += f'<text x="{stats_x}" y="45" fill="{text_color}">\n'
    
    # Line 1: Header
    svg += f'<tspan x="{stats_x}" y="45">{USER_NAME.lower()}@github</tspan> <tspan class="cc">{"-" * 40}</tspan>\n'
    
    # Line 2: OS
    svg += format_stat_line(stats_x, 68, ["OS"], "Linux (Ubuntu / Arch), Windows 11") + "\n"
    
    # Line 3: Uptime
    svg += format_stat_line(stats_x, 91, ["Uptime"], uptime_val) + "\n"
    
    # Line 4: Host
    svg += format_stat_line(stats_x, 114, ["Host"], "Universitas Sebelas Maret") + "\n"
    
    # Line 5: Kernel
    svg += format_stat_line(stats_x, 137, ["Kernel"], "Web Developer &amp; Game Enthusiast") + "\n"
    
    # Line 6: IDE
    svg += format_stat_line(stats_x, 160, ["IDE"], "VS Code, Unity, Godot") + "\n"
    
    # Line 7: Empty
    svg += f'<tspan x="{stats_x}" y="183"> </tspan>\n'
    
    # Line 8: Languages.Programming
    svg += format_stat_line(stats_x, 206, ["Languages", "Programming"], "JavaScript, Python, C#, PHP") + "\n"
    
    # Line 9: Languages.Computer
    svg += format_stat_line(stats_x, 229, ["Languages", "Computer"], "HTML, CSS, JSON, SQL") + "\n"
    
    # Line 10: Languages.Real
    svg += format_stat_line(stats_x, 252, ["Languages", "Real"], "Indonesian (Native), English") + "\n"
    
    # Line 11: Empty
    svg += f'<tspan x="{stats_x}" y="275"> </tspan>\n'
    
    # Line 12: Hobbies.Software
    svg += format_stat_line(stats_x, 298, ["Hobbies", "Software"], "Web Crafting, Game Dev, Gaming") + "\n"
    
    # Line 13: Hobbies.Hardware
    svg += format_stat_line(stats_x, 321, ["Hobbies", "Hardware"], "PC Building, Mechanical Keyboards") + "\n"
    
    # Line 14: Empty
    svg += f'<tspan x="{stats_x}" y="344"> </tspan>\n'
    
    # Line 15: Contact divider
    svg += f'<tspan x="{stats_x}" y="367">- Contact</tspan> <tspan class="cc">{"-" * 48}</tspan>\n'
    
    # Line 16: Email
    svg += format_stat_line(stats_x, 390, ["Email"], "saji6787@gmail.com") + "\n"
    
    # Line 17: Instagram
    svg += format_stat_line(stats_x, 413, ["Instagram"], "saji.6787") + "\n"
    
    # Line 18: GitHub
    svg += format_stat_line(stats_x, 436, ["GitHub"], "Sajinomoto") + "\n"
    
    # Line 19: Website
    svg += format_stat_line(stats_x, 459, ["Website"], "sajinomoto.my.id") + "\n"
    
    # Line 20, 21: Empty
    svg += f'<tspan x="{stats_x}" y="482"> </tspan>\n'
    svg += f'<tspan x="{stats_x}" y="505"> </tspan>\n'
    
    # Line 22: GitHub Stats Divider
    svg += f'<tspan x="{stats_x}" y="528">- GitHub Stats</tspan> <tspan class="cc">{"-" * 43}</tspan>\n'
    
    # Line 23: Repos and Stars
    repo_val = stats["repos"]
    contrib_val = stats["contributed"]
    star_val = stats["stars"]
    repos_text = f"{repo_val}"
    contrib_text = f"{{Contributed: {contrib_val}}}"
    stars_text = f"{star_val}"
    
    # Calculate dots for Repos/Stars line
    # Format: . Repos: XXX {Contributed: YYY} | Stars: ZZZ
    # Let's build a customized line
    svg += f'<tspan x="{stats_x}" y="551" class="cc">. </tspan><tspan class="key">Repos</tspan>:<tspan class="cc"> .... </tspan><tspan class="value">{repos_text}</tspan> {{<tspan class="key">Contributed</tspan>: <tspan class="value">{contrib_val}</tspan>}} | <tspan class="key">Stars</tspan>:<tspan class="cc"> ........... </tspan><tspan class="value">{stars_text}</tspan>\n'
    
    # Line 24: Commits and Followers
    commit_val = f"{stats['commits']:,}"
    follower_val = f"{stats['followers']:,}"
    svg += f'<tspan x="{stats_x}" y="574" class="cc">. </tspan><tspan class="key">Commits</tspan>:<tspan class="cc"> ................... </tspan><tspan class="value">{commit_val}</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc"> ....... </tspan><tspan class="value">{follower_val}</tspan>\n'
    
    # Line 25: Lines of Code
    loc_val = f"{stats['loc']:,}"
    loc_add = f"{stats['loc_add']:,}"
    loc_del = f"{stats['loc_del']:,}"
    svg += f'<tspan x="{stats_x}" y="597" class="cc">. </tspan><tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc">. </tspan><tspan class="value">{loc_val}</tspan> ( <tspan class="addColor">{loc_add}</tspan><tspan class="addColor">++</tspan>, <tspan class="delColor">{loc_del}</tspan><tspan class="delColor">--</tspan> )\n'
    
    svg += '</text>\n</svg>'
    
    # Write file
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f"Generated {filename} successfully.")
    except Exception as e:
        print(f"Error writing SVG {filename}: {e}")

if __name__ == "__main__":
    print("Loading ASCII art...")
    ascii_art = load_ascii_art("ascii-art.txt")
    print(f"Loaded ASCII art. Height: {len(ascii_art)} lines.")
    
    print("Fetching GitHub Stats...")
    stats = get_github_stats()
    print("Stats fetched:")
    print(stats)
    
    print("Generating SVGs...")
    generate_svg("dark_mode.svg", "dark", ascii_art, stats)
    generate_svg("light_mode.svg", "light", ascii_art, stats)
    
    # Update README.md
    print("Updating README.md...")
    readme_content = """<a href="https://github.com/Sajinomoto/Sajinomoto">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Sajinomoto/Sajinomoto/main/dark_mode.svg">
    <img alt="Sajinomoto's GitHub Profile README" src="https://raw.githubusercontent.com/Sajinomoto/Sajinomoto/main/light_mode.svg">
  </picture>
</a>
"""
    try:
        with open("README.md", "w") as f:
            f.write(readme_content)
        print("README.md updated.")
    except Exception as e:
        print(f"Error updating README.md: {e}")
