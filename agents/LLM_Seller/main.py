import os
import time
import logging
import pandas as pd
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from email.message import EmailMessage
import smtplib
from typing import Dict


EXCEL_FILE = "data/email_enq.xlsx"
OUTPUT_DIR = "output"
MODEL_NAME = "gpt-4o-mini"
API_SLEEP = 0.5


# SMTP config from environment
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
#Since SMTP is not configured it will save the template in outut folder


with open('data/api_key.txt') as f:
    os.environ["OPENAI_API_KEY"] = f.read().strip()

# initialize
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# Initialize OpenAI-like client
client = OpenAI()  # requires OPENAI_API_KEY in env


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
    
    
SYSTEM_PROMPT = "You are a helpful sales assistant that extracts key information and drafts professional seller responses and proposals."

EXTRACTION_PROMPT = """You are an assistant for sales. From the customer message below extract:
- Customer Name (if present)
- Product of Interest (short)
- Customer Intent (Enquiry/Price/Buy/Bulk/Comparison/Support/Other)
- Key Questions (bullet list)
- Tone (Formal/Neutral/Casual)
Return the result in JSON only.
---
{content}
"""

DRAFT_REPLY_PROMPT = """You are a sales representative drafting a reply email to the customer. Use the extracted details below and the original customer message to:
- Acknowledge the customer's enquiry
- Answer the questions if the information is straightforward (or provide next steps if you need to check stock/pricing)
- Offer relevant options (financing/EMIs/warranty) if appropriate
- Suggest a clear next action (reply, call, quote, sample)
Return the reply message in plain text.
---
Extracted JSON:
{extracted}
Original Customer Message:
{content}
"""

PROPOSAL_PROMPT = """You are to create a short, professional PDF-ready proposal or information sheet tailored to the customer's subject and enquiry. Include:
- Title (based on subject)
- Short summary of product capabilities
- Technical highlights (RAM/CPU/GPU etc if mentioned)
- Available options (configurations, financing, delivery)
- Estimated delivery timeline placeholders (we'll replace with actual values)
Return the proposal as formatted plain text (headings and short paragraphs).
---
Subject: {subject}
Extracted JSON:
{extracted}
Customer Message:
{content}
"""


def process_row(row: Dict, idx: int):
    to_addr = row.get("mailid", "").strip()
    subject = row.get("subject", "").strip()
    content = row.get("content", "").strip()

    logging.info("Processing row %d -> %s | %s", idx, to_addr, subject[:60])

    # 1) Extract key details (JSON) from email
    extraction_prompt_filled = EXTRACTION_PROMPT.format(content=content)
    try:
        extracted_raw = call_llm(extraction_prompt_filled, system=SYSTEM_PROMPT)
        # The LLM is instructed to return JSON; attempt to parse it.
        import json
        try:
            extracted_json = json.loads(extracted_raw)
        except Exception:
            # If JSON parse fails, wrap in a simple dict with raw text
            extracted_json = {"llm_extraction_raw": extracted_raw}
            logging.warning("Extraction did not return valid JSON for %s. Keeping raw text.", to_addr)
    except Exception as e:
        logging.error("LLM extraction failed for %s : %s", to_addr, str(e))
        extracted_json = {"error": str(e)}

    time.sleep(API_SLEEP)

    # 2) Generate a seller reply draft
    draft_prompt_filled = DRAFT_REPLY_PROMPT.format(extracted=str(extracted_json), content=content)
    try:
        draft_reply = call_llm(draft_prompt_filled, system=SYSTEM_PROMPT)
    except Exception as e:
        draft_reply = "Sorry, could not generate draft reply due to an error."
        logging.error("Draft generation failed: %s", str(e))

    time.sleep(API_SLEEP)

    # 3) Generate a proposal document based on subject
    proposal_prompt_filled = PROPOSAL_PROMPT.format(subject=subject, extracted=str(extracted_json), content=content)
    try:
        proposal_text = call_llm(proposal_prompt_filled, system=SYSTEM_PROMPT)
    except Exception as e:
        proposal_text = "Sorry, could not generate proposal due to an error."
        logging.error("Proposal generation failed: %s", str(e))

    # 4) Build PDF
    pdf_filename = os.path.join(OUTPUT_DIR, f"response_{idx+1}.pdf")
    try:
        # PDF content: include subject, draft reply, and proposal
        combined_text = f"Subject: {subject}\n\n--- Proposal ---\n{proposal_text}\n\n--- Draft Reply ---\n{draft_reply}\n\n--- Original Message ---\n{content}"
        build_pdf(combined_text, pdf_filename)
        logging.info("Saved PDF: %s", pdf_filename)
    except Exception as e:
        logging.error("Failed to build PDF for %s : %s", to_addr, str(e))
        pdf_filename = ""

    # 5) Send email (or save locally)
    if to_addr and pdf_filename:
        email_subject = f"Re: {subject} - Response from Sales"
        # Keep the LLM-drafted reply as the body, but optionally prepend a short salutation/signature
        full_email_body = f"Hello,\n\n{draft_reply}\n\nBest regards,\nSales Team\n"
        sent = send_email_with_attachment(to_addr, email_subject, full_email_body, pdf_filename)
        if not sent:
            # Save the email and draft to a text file so the seller can manually send
            out_txt = os.path.join(OUTPUT_DIR, f"response_{idx+1}.txt")
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(f"To: {to_addr}\nSubject: {email_subject}\n\n{full_email_body}\n\nAttachment: {pdf_filename}\n")
            logging.info("Saved local draft email: %s", out_txt)
    else:
        logging.warning("Skipping send/save because missing recipient or PDF for row %d", idx+1)

    # Return a summary record for bookkeeping
    return {
        "row": idx + 1,
        "to": to_addr,
        "subject": subject,
        "pdf": pdf_filename,
        "extracted": extracted_json,
        "draft_reply_snippet": (draft_reply[:300] + "...") if draft_reply else ""
    }

def main():
    # Load excel
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl")
    # Ensure expected cols exist
    expected = {"mailid", "subject", "content"}
    if not expected.issubset(set(df.columns.str.lower())):
        # Try tolerant column lookup (case-insensitive)
        cols = {c.lower(): c for c in df.columns}
        if expected.issubset(set(cols.keys())):
            df = df.rename(columns={cols[k]: k for k in cols if k in expected})
        else:
            logging.error("Excel file must contain columns: mailid, subject, content (case-insensitive). Found: %s", df.columns.tolist())
            return

    # Normalize column names
    df.columns = [c.lower() for c in df.columns]

    results = []
    for idx, row in df.iterrows():
        try:
            res = process_row(row, idx)
            results.append(res)
        except Exception as e:
            logging.error("Failed processing row %d: %s", idx + 1, str(e))

    # Save a summary CSV
    summary_df = pd.DataFrame(results)
    summary_path = os.path.join(OUTPUT_DIR, "processing_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    logging.info("Processing complete. Summary saved to %s", summary_path)


if __name__ == "__main__":
    main()
