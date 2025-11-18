import os

# SMTP config from environment
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")



# ---------- Utility functions ----------
def call_llm(prompt: str, system: str = None) -> str:
    """
    Basic wrapper to call chat completions. Returns assistant message content.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        # you can add max_tokens, temperature, etc here
    )
    # adapt based on SDK response shape used earlier
    return resp.choices[0].message.content

def build_pdf(text: str, filename: str):
    """
    Create a simple PDF with the provided text.
    """
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    flow = []
    for line in text.splitlines():
        if line.strip():
            flow.append(Paragraph(line.replace("\t", "    "), styles["Normal"]))
            flow.append(Spacer(1, 8))
    doc.build(flow)

def send_email_with_attachment(to_addr: str, subject: str, body_text: str, attachment_path: str) -> bool:
    """
    Send an email using SMTP with a single PDF attachment. Returns True on success.
    If SMTP not configured, returns False.
    """
    if not (SMTP_SERVER and SMTP_USER and SMTP_PASS):
        logging.warning("SMTP not configured. Skipping send for %s", to_addr)
        return False

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body_text)

    # Attach PDF
    with open(attachment_path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(attachment_path))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        logging.info("Email successfully sent to %s", to_addr)
        return True
    except Exception as e:
        logging.error("Failed to send email to %s : %s", to_addr, str(e))
        return False