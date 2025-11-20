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

    dv_html = None

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if not question:
            error = "Please enter a valid question."
        else:
            try:
                res = requests.post(SUPERVISOR_URL, json={"question": question}, timeout=300)

                if res.status_code == 200:
                    response = res.json()
                else:
                    error = f"Supervisor error: {res.text}"

            except requests.RequestException as e:
                error = f"Error connecting to Supervisor: {str(e)}"
                

    #print("Raw Response :", res)
    print("UI RECEIVED:", response)
    print("DV_HTML:", response.get("dv_html") if response else None)

    if isinstance(response, dict) and "dv_html" in response:
        dv_html = response["dv_html"]

    # Clean HTML
    dv_html = clean_dv_html(dv_html)

    return render_template("index.html", dv_html=dv_html)


def clean_dv_html(raw_html):
    if not raw_html:
        return ""

    # Remove  only script tags
    raw_html = re.sub(r"<script[^>]*>.*?</script>", "", raw_html,
                      flags=re.DOTALL | re.IGNORECASE)  

    # Remove javascript: hrefs
    raw_html = re.sub(r'href=[\'"]javascript:[^\'"]*[\'"]', "", raw_html,
                      flags=re.IGNORECASE)

    # Remove inline JS events (onclick, onload, etc.)
    raw_html = re.sub(r'on\w+="[^"]*"', "", raw_html,
                      flags=re.IGNORECASE)

    # Remove external images (but keep local /static/)
    raw_html = re.sub(r'<img[^>]*(src="http[^"]*")[^>]*>', "", raw_html,
                      flags=re.IGNORECASE)

    return raw_html.strip()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
