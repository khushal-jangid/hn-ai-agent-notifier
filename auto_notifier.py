"""
AgentScout Always-On Background Notifier
----------------------------------------
Monitors Hacker News for NEW high-signal AI Agent stories.
Sends email notifications only when unseen stories appear.
"""

import os
import sys
import io
import time
import json
import datetime
from pathlib import Path

# Force UTF-8 output encoding for Windows terminal compatibility
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Fix paths for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import scout
import delivery

SEEN_DB_FILE = current_dir / "seen_stories.json"
CHECK_INTERVAL_SECONDS = int(os.environ.get("AGENTSCOUT_POLL_INTERVAL", 900)) # 15 minutes default

def load_seen_ids() -> set[str]:
    if SEEN_DB_FILE.exists():
        try:
            with open(SEEN_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("seen_ids", []))
        except Exception as e:
            print(f"Could not load seen_stories.json: {e}")
    return set()

def save_seen_ids(seen_ids: set[str]):
    try:
        with open(SEEN_DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen_ids": list(seen_ids), "updated_at": datetime.datetime.now().isoformat()}, f, indent=2)
    except Exception as e:
        print(f"Could not save seen_stories.json: {e}")

def check_for_new_stories():
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking Hacker News for new AI stories...")
    seen_ids = load_seen_ids()
    
    try:
        live_stories = scout.curate_stories(live=True, top_n=10)
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return

    new_stories = []
    for story in live_stories:
        story_key = story.hn_url or story.url
        if story_key not in seen_ids:
            new_stories.append(story)
            seen_ids.add(story_key)

    if not new_stories:
        print("No new unseen stories found.")
        return

    print(f"Found {len(new_stories)} NEW high-signal stories!")
    
    # Save updated seen IDs
    save_seen_ids(seen_ids)

    # Render brief for new stories only
    brief = scout.render_brief(new_stories, watch_mode="live_notifier")
    payload = brief.to_dict()

    # Attempt delivery
    email_to = os.environ.get("AGENTSCOUT_EMAIL_TO", "khushaljangra013@gmail.com")
    smtp_pass = os.environ.get("AGENTSCOUT_SMTP_PASSWORD", "bcakeoqlbkrwcxdj")
    
    os.environ["AGENTSCOUT_EMAIL_TO"] = email_to
    os.environ["AGENTSCOUT_EMAIL_FROM"] = email_to
    os.environ["AGENTSCOUT_SMTP_PASSWORD"] = smtp_pass

    print(f"Sending notification email to {email_to}...")
    res = delivery.send_brief(payload)
    print(f"Delivery Result: {res}")

def start_notifier():
    print("=" * 60)
    print(" AGENTSCOUT ALWAYS-ON NOTIFIER STARTED ")
    print(f" Polling Interval: Every {CHECK_INTERVAL_SECONDS // 60} minutes")
    print("=" * 60)
    
    while True:
        try:
            check_for_new_stories()
        except Exception as e:
            print(f"Error in check loop: {e}")
        
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    start_notifier()
