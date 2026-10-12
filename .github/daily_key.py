"""Makes today's Nova Hub key.

1. Picks a random key and publishes only its SHA-256 fingerprint in keyhash.txt
   (next to yesterday's, so yesterday's key keeps working until the next one).
2. Waits until GitHub's raw file cache has the new fingerprint.
3. Shows the key in #get-key by editing the bot's key message (or posting it).

The key itself only ever goes to Discord. Needs the DISCORD_KEY_WEBHOOK secret.
"""
import hashlib
import json
import os
import pathlib
import secrets
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
HASHES = ROOT / "keyhash.txt"
MESSAGE_ID = ROOT / ".github" / "key-message.txt"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I mix-ups
COLOR = 0x8A2BE2
ICON = "https://raw.githubusercontent.com/Jaidendor/NovaHub-Loader/main/Assets/icon_v1.png"


def git(*args):
    subprocess.run(["git", *args], check=True, cwd=ROOT)


def commit(paths, message):
    git("add", *paths)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        git("commit", "-m", message)
        git("pull", "--rebase", "-q")
        git("push")


def discord(method, url, payload=None):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", "User-Agent": "NovaHubKey"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r) if r.status != 204 else None


def main():
    webhook = os.environ.get("DISCORD_KEY_WEBHOOK")
    if not webhook:
        print("DISCORD_KEY_WEBHOOK secret isn't set yet, no key made")
        return

    key = "NOVA-" + "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(2))
    new_hash = hashlib.sha256(key.encode()).hexdigest()
    old = HASHES.read_text().split() if HASHES.exists() else []
    HASHES.write_text("\n".join([new_hash] + old[:1]) + "\n")
    commit([str(HASHES)], "Daily key [skip changelog]")

    time.sleep(int(os.environ.get("CACHE_WAIT", "330")))  # raw.githubusercontent.com caches ~5 minutes

    now = int(time.time())
    next_key = (now // 86400 + 1) * 86400 + 7 * 60
    payload = {
        "username": "Nova Hub",
        "avatar_url": ICON,
        "content": "",
        "embeds": [{
            "title": "🔑 Today's Nova Hub Key",
            "description": (
                f"```\n{key}\n```\n"
                "Paste it into the key window when you run the script.\n"
                f"Next key <t:{next_key}:R>. Yesterday's key keeps working until then.\n\n"
                "**Don't share the key outside this server.**"
            ),
            "color": COLOR,
            "footer": {"text": "Nova Hub"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }],
    }
    message_id = MESSAGE_ID.read_text().strip() if MESSAGE_ID.exists() else ""
    if message_id:
        try:  # edit the existing message so the channel stays one clean post
            discord("PATCH", f"{webhook}/messages/{message_id}", payload)
            print("key message updated")
            return
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    sent = discord("POST", f"{webhook}?wait=true", payload)
    MESSAGE_ID.write_text(sent["id"] + "\n")
    commit([str(MESSAGE_ID)], "Key message id [skip changelog]")
    print("key message posted")


if __name__ == "__main__":
    main()
