"""Posts each update as a Discord embed in #changelog.

Commit message layout (what I write when pushing a build):
    Title line                     -> embed title
    Game: Noob Incremental         -> shown in bold under the title (optional)
    - first change                 -> bullet list
    - second change
A commit with "[skip changelog]" in it is not posted.
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

COLOR = 0x8A2BE2  # Nova Hub purple
LOADSTRING = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/Jaidendor/NovaHub-Loader/main/Loader.lua"))()'


def commits_args(args):
    out = subprocess.run(["git", "log", "--reverse", "--format=%B%x00", *args],
                         capture_output=True, text=True, check=True).stdout
    return [m.strip() for m in out.split("\x00") if m.strip()]


def embed(message):
    lines = [l.rstrip() for l in message.splitlines()]
    title, rest = lines[0], lines[1:]
    game = next((l.split(":", 1)[1].strip() for l in rest if l.lower().startswith("game:")), None)
    bullets = [l.lstrip("-* ").strip() for l in rest if l.lstrip().startswith(("-", "*"))]
    new_game = title.lower().startswith("new supported game")

    parts = []
    if game:
        parts.append(f"**{game}**\n")
    if bullets:
        parts.append("Features:" if new_game else "Changes:")
        parts += [f"• {b}" for b in bullets]
    parts.append(f"\n🔄 Re-run the loadstring to update:\n```lua\n{LOADSTRING}\n```")
    return {
        "title": ("🎮 " if new_game else "📢 ") + title,
        "description": "\n".join(parts)[:4000],
        "color": COLOR,
        "footer": {"text": "Nova Hub"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    if not os.environ.get("DISCORD_CHANGELOG_WEBHOOK"):
        print("DISCORD_CHANGELOG_WEBHOOK secret isn't set yet, nothing posted")
        return
    before, after = sys.argv[1], sys.argv[2]
    if not before or set(before) == {"0"}:  # manual run or a brand-new branch: the latest real update
        messages = [m for m in commits_args(["-30", after]) if "[skip changelog]" not in m][-1:]
    else:
        messages = [m for m in commits_args([f"{before}..{after}"]) if "[skip changelog]" not in m]
    if not messages:
        print("nothing to post")
        return
    embeds = [embed(m) for m in messages][-10:]  # Discord allows 10 embeds per message
    req = urllib.request.Request(
        os.environ["DISCORD_CHANGELOG_WEBHOOK"],
        data=json.dumps({"username": "Nova Hub", "embeds": embeds}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "NovaHubChangelog"},
    )
    urllib.request.urlopen(req, timeout=20)
    print(f"posted {len(embeds)} update(s)")


if __name__ == "__main__":
    main()
