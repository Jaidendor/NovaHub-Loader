"""Makes today's Nova Hub keys: the normal key and the tester key.

1. Picks a random key per kind and publishes only its SHA-256 fingerprint
   (next to yesterday's, so yesterday's key keeps working until the next one).
2. Waits until GitHub's raw file cache has the new fingerprints.
3. Shows each key in its Discord channel by editing the bot's key message (or posting it).

The keys themselves only ever go to Discord. A kind is skipped while its webhook
secret isn't set: DISCORD_KEY_WEBHOOK (#get-key), DISCORD_TESTER_KEY_WEBHOOK (tester channel).
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
KINDS = [
    # secret, fingerprint file, message id file, key prefix, embed title, who it's for
    ("DISCORD_KEY_WEBHOOK", "keyhash.txt", ".github/key-message.txt", "NOVA",
     "🔑 Today's Nova Hub Key", "Paste it into the key window when you run the script."),
    ("DISCORD_TESTER_KEY_WEBHOOK", "testerkeyhash.txt", ".github/tester-key-message.txt", "TEST",
     "🧪 Today's Tester Key", "This key loads the **tester version** of Nova Hub. Report what breaks in #tester-chat."),
]
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


def post_key(webhook, message_file, key, title, intro):
    now = int(time.time())
    next_key = (now // 86400 + 1) * 86400 + 7 * 60
    payload = {
        "username": "Nova Hub",
        "avatar_url": ICON,
        "content": "",
        "embeds": [{
            "title": title,
            "description": (
                f"```\n{key}\n```\n"
                f"{intro}\n"
                f"Next key <t:{next_key}:R>. Yesterday's key keeps working until then.\n\n"
                "**Don't share the key outside this server.**"
            ),
            "color": COLOR,
            "footer": {"text": "Nova Hub"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }],
    }
    message_id = message_file.read_text().strip() if message_file.exists() else ""
    if message_id:
        try:  # edit the existing message so the channel stays one clean post
            discord("PATCH", f"{webhook}/messages/{message_id}", payload)
            return False
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    sent = discord("POST", f"{webhook}?wait=true", payload)
    message_file.write_text(sent["id"] + "\n")
    return True


def main():
    todo = []
    for secret, hash_name, message_name, prefix, title, intro in KINDS:
        webhook = os.environ.get(secret)
        if not webhook:
            print(f"{secret} isn't set, skipping that key")
            continue
        key = prefix + "-" + "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(2))
        hashes = ROOT / hash_name
        old = hashes.read_text().split() if hashes.exists() else []
        hashes.write_text("\n".join([hashlib.sha256(key.encode()).hexdigest()] + old[:1]) + "\n")
        todo.append((webhook, ROOT / message_name, key, title, intro, hashes))
    if not todo:
        return
    commit([str(t[5]) for t in todo], "Daily keys [skip changelog]")

    time.sleep(int(os.environ.get("CACHE_WAIT", "330")))  # raw.githubusercontent.com caches ~5 minutes

    new_ids = [str(message_file) for webhook, message_file, key, title, intro, _ in todo
               if post_key(webhook, message_file, key, title, intro)]
    if new_ids:
        commit(new_ids, "Key message ids [skip changelog]")
    print(f"made {len(todo)} key(s)")


if __name__ == "__main__":
    main()
