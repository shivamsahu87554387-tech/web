import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


EMAIL = "shivamshivamsahu87@gmail.com"
APP_PASSWORD = "gsjnpacaiopvdarp"


def send_otp(email, otp):

    subject = "Workmitra Password Reset OTP"

    body = f"""
Hello,

Your Workmitra Password Reset OTP is:

{otp}

This OTP is valid for 10 minutes.

Do not share this OTP with anyone.

Thanks,
Workmitra Team
"""

    message = MIMEMultipart()

    message["From"] = EMAIL
    message["To"] = email
    message["Subject"] = subject

    message.attach(
        MIMEText(body, "plain")
    )

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        EMAIL,
        APP_PASSWORD
    )

    server.sendmail(
        EMAIL,
        email,
        message.as_string()
    )

    server.quit()
