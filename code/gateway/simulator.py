import requests
import time
import random

URL = "http://127.0.0.1:8000/notifications"

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": "team17-secret-key"
}

CHANNELS = ["email", "push", "inapp"]
PRIORITIES = ["high", "normal"]


def send_notification(i):
    # 每第7条发送一个非法消息（进入DLQ）
    if i % 7 == 0:
        channel = "fax"
        priority = "urgent"
    else:
        channel = random.choice(CHANNELS)
        priority = random.choice(PRIORITIES)

    data = {
        "user_id": f"u{i}",
        "channel": channel,
        "priority": priority,
        "title": "Test Notification",
        "message": f"Message {i}",
        "recipient": f"user{i}@example.com"
    }

    try:
        response = requests.post(URL, json=data, headers=HEADERS)
        result = response.json()

        if result.get("success"):
            print(f"✅ Sent {i}: {channel} ({priority})")
        else:
            print(f"❌ Failed {i}: {channel} ({priority}) → {result.get('error_code')}")

    except Exception as e:
        print(f"⚠️ Error sending {i}: {e}")


def main():
    print("🚀 Starting distributed routing simulator...")

    for i in range(1, 21):
        send_notification(i)
        time.sleep(0.1)

    print("✅ Demo batch completed!")


if __name__ == "__main__":
    main()