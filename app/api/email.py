from fastapi import APIRouter, HTTPException
import smtplib
from email.message import EmailMessage

app = APIRouter()


@app.post("/send_email/")
async def send_email(to_email: str, subject: str, message: str):
    try:
        email_address = "teamwhipup@gmail.com"
        email_password = "kbccxgmiccctafpl"
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_address
        msg['To'] = to_email
        msg.set_content(message)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(msg)

        return {"message": "Email sent successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
