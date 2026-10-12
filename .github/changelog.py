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
# Discord role IDs to ping (Developer Mode -> right-click the role -> Copy Role ID).
# A new game pings only NEW_GAME_ROLE, every other update pings only UPDATE_ROLE.
UPDATE_ROLE = "1559068776404619265"    # "update log"
NEW_GAME_ROLE = "1559069009050083368"  # "new game"
ICON = "https://raw.githubusercontent.com/Jaidendor/NovaHub-Loader/main/Assets/icon_v1.png"
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
    test = os.environ.get("TEST_POST", "")
    if test == "update":
        messages = ["TEST: update ping\nGame: Noob Incremental\n- This is a test post for the update log ping\n- Nothing changed in the script"]
    elif test == "new-game":
        messages = ["New Supported Game (TEST)\nGame: Example Game\n- This is a test post for the new game ping\n- No new game was added yet"]
    elif not before or set(before) == {"0"}:  # manual run or a brand-new branch: the latest real update
        messages = [m for m in commits_args(["-30", after]) if "[skip changelog]" not in m][-1:]
    else:
        messages = [m for m in commits_args([f"{before}..{after}"]) if "[skip changelog]" not in m]
    if not messages:
        print("nothing to post")
        return
    embeds = [embed(m) for m in messages][-10:]  # Discord allows 10 embeds per message
    new_game = any(m.lower().startswith("new supported game") for m in messages)
    role = NEW_GAME_ROLE if new_game else UPDATE_ROLE
    payload = {"username": "Nova Hub", "avatar_url": ICON, "embeds": embeds,
               "allowed_mentions": {"roles": [role] if role else []}}
    if role:
        payload["content"] = f"<@&{role}>"
    req = urllib.request.Request(
        os.environ["DISCORD_CHANGELOG_WEBHOOK"],
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "NovaHubChangelog"},
    )
    urllib.request.urlopen(req, timeout=20)
    print(f"posted {len(embeds)} update(s)")


if __name__ == "__main__":
    main()
