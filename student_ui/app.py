from flask import Flask, render_template, request
import requests
import os
import re


app = Flask(__name__)

# Supervisor API endpoint (update if different)
SUPERVISOR_URL = os.getenv("SUPERVISOR_URL", "http://localhost:10500/ask")

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    error = None

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if not question:
            error = "Please enter a valid question."
        else:
            try:
                res = requests.post(SUPERVISOR_URL, json={"question": question}, timeout=30)
                if res.status_code == 200:
                    response = res.json()
                else:
                    error = f"Supervisor error: {res.text}"
            except requests.RequestException as e:
                error = f"Error connecting to Supervisor: {str(e)}"

    dv_html = None

    if response and "dv_result" in response:
        try:
            dv_html = response["dv_result"]["result"]["parts"][0]["text"]
        except Exception as e:
            dv_html = f"Error extracting DV result: {e}"

   
    # Clean for safe rendering
    dv_html = clean_dv_html(dv_html)

    return render_template("index.html", dv_html=dv_html)
        #return render_template("index.html", response=response, error=error)
    return render_template("index.html", dv_html=dv_html, error=error)



def clean_dv_html(raw_html):
    if not raw_html:
        return ""

    # Remove full <html> / <head> / <body> blocks
    raw_html = re.sub(r"<\/?(html|head|body)[^>]*>", "", raw_html, flags=re.IGNORECASE)

    # Remove all <script> tags
    raw_html = re.sub(r"<script[^>]*>.*?<\/script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)

    # Remove all <link> CSS references
    raw_html = re.sub(r"<link[^>]*>", "", raw_html, flags=re.IGNORECASE)

    # Remove images pointing to external website
    raw_html = re.sub(r"<img[^>]*>", "", raw_html, flags=re.IGNORECASE)

    # Remove any IITJ site assets
    raw_html = re.sub(r"\/Website[^\"'> ]*", "", raw_html, flags=re.IGNORECASE)

    # Remove background images in inline styles
    raw_html = re.sub(r"url\([^)]+\)", "", raw_html, flags=re.IGNORECASE)

    return raw_html.strip()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
