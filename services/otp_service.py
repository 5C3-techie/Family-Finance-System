import random
from datetime import datetime, timedelta

def generate_otp():
    otp = random.randint(100000, 999999)
    expiry = datetime.now() + timedelta(minutes=5)
    return str(otp), expiry.strftime("%Y-%m-%d %H:%M:%S")