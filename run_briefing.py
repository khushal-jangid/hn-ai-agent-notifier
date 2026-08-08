import sys
import io
import os
import scout
import delivery

# Force UTF-8 output encoding for Windows terminal compatibility
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    print("=" * 60)
    print(" 📰 AGENT SCOUT — Hacker News Live Briefing Agent ")
    print("=" * 60)
    print("Fetching live Hacker News stories...\n")
    
    try:
        brief = scout.run_ambient_scout(live=True, top_n=5)
        print(brief["text"])
        print("\n" + "=" * 60)
        
        # Check delivery options
        email_to = os.environ.get("AGENTSCOUT_EMAIL_TO")
        smtp_pass = os.environ.get("AGENTSCOUT_SMTP_PASSWORD")
        
        if email_to and smtp_pass:
            print(f"Attempting to send email briefing to {email_to}...")
            result = delivery.send_brief(brief)
            print(f"Delivery result: {result}")
        else:
            print("\n💡 NOTE: Email delivery requires setting your email & App Password:")
            print("   $env:AGENTSCOUT_EMAIL_TO = 'your_email@gmail.com'")
            print("   $env:AGENTSCOUT_SMTP_PASSWORD = 'your_app_password'")
            print("   python run_briefing.py")

        print("=" * 60)
    except Exception as e:
        print(f"Error executing briefing agent: {e}")

if __name__ == "__main__":
    main()
