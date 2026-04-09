from datetime import datetime, timezone
import random
import string

# 6 digit suffix
def random_suffix(length=6):
    return ''.join(random.choices(string.digits, k=length))

# generators
def generate_notification_id():
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"noti_{date_part}_{random_suffix()}"

def generate_request_id():
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"req_{date_part}_{random_suffix()}"

def generate_trace_id():
    return f"trace_{random_suffix()}"