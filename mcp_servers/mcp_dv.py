# mcp_servers/mcp_dv.py
import os
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException, Body
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="Data Visualization MCP", version="1.0")

# defaults (env-overridable)
#result_dir = os.getenv("DV_RESULTS_DIR", "./artifacts/dv_results")
result_dir = os.getenv("DV_RESULTS_DIR", "./student_ui/static/resource")
predictions_path_default = os.getenv("PREDICTION_PATH", "./artifacts/ml_results/predictions.csv")
feature_importance_path = os.getenv("FEATURE_IMPORTANCE_PATH", "./artifacts/ml_results/feature_importances.json")

os.makedirs(result_dir, exist_ok=True)

def plot_pred_vs_actual(df: pd.DataFrame, out_path: str):
    plt.figure(figsize=(8, 6))
    plt.scatter(df["y_true"], df["y_pred"], alpha=0.6)
    min_val = min(df["y_true"].min(), df["y_pred"].min())
    max_val = max(df["y_true"].max(), df["y_pred"].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=1.5)
    plt.xlabel("Actual")
    plt.ylabel("Predicted")
    plt.title("Predicted vs Actual")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved plot: %s", out_path)

def plot_residuals(df: pd.DataFrame, out_path: str):
    df["residual"] = df["y_true"] - df["y_pred"]
    plt.figure(figsize=(8, 5))
    plt.scatter(df["y_pred"], df["residual"], alpha=0.6)
    plt.axhline(0, color='r', linestyle='--')
    plt.xlabel("Predicted")
    plt.ylabel("Residual (Actual - Predicted)")
    plt.title("Residuals vs Predicted")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved plot: %s", out_path)

def plot_feature_importances(importances, out_path: str):
    # importances expected list of (feature, importance)
    if not importances:
        raise ValueError("No feature importances provided")
    feat_names, scores = zip(*importances)
    plt.figure(figsize=(8, max(4, len(feat_names) * 0.4)))
    plt.barh(feat_names, scores)
    plt.xlabel("Importance")
    plt.title("Feature Importances")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    logger.info("Saved plot: %s", out_path)

@app.post("/visualize/results")
async def visualize_results(
    payload: dict = Body(default={})
):

    try:
        logger.info("Visualization request received: %s", payload)

        predictions_path = payload.get("predictions_path") or predictions_path_default
        feature_importances = payload.get("feature_importances")  # optional
        save_prefix = payload.get("save_prefix", "pred_vs_actual")

        if not os.path.exists(predictions_path):
            raise FileNotFoundError(f"Predictions CSV not found at {predictions_path}")

        df = pd.read_csv(predictions_path)
        if not {"y_true", "y_pred"}.issubset(df.columns):
            raise ValueError("predictions CSV must contain columns 'y_true' and 'y_pred'")

        # ensure results dir exists
        os.makedirs(result_dir, exist_ok=True)

        # plot 1: predicted vs actual
        pvap = os.path.join(result_dir, f"{save_prefix}_pred_vs_actual.png")
        plot_pred_vs_actual(df, pvap)

        # plot 2: residuals
        residp = os.path.join(result_dir, f"{save_prefix}_residuals.png")
        plot_residuals(df, residp)

        # plot 3: feature importances (if provided inline or in ml_results)
        fi_path = None
        if feature_importances:
            # accept inline list of [feat,score]
            fi_path = os.path.join(result_dir, f"{save_prefix}_feature_importances.png")
            plot_feature_importances(feature_importances, fi_path)
        else:
            # try to read from default ml_results feature importances file
            if os.path.exists(feature_importance_path):
                try:
                    with open(feature_importance_path, "r") as f:
                        fi = json.load(f)
                    # allow either dict or list-of-pairs
                    if isinstance(fi, dict) and "feature_importances" in fi:
                        fi_list = fi["feature_importances"]
                    else:
                        fi_list = fi
                    if fi_list:
                        fi_path = os.path.join(result_dir, f"{save_prefix}_feature_importances.png")
                        plot_feature_importances(fi_list, fi_path)
                except Exception as e:
                    logger.warning("Could not load default feature_importances: %s", e)

        # save summary
        summary = {
            "status": "success",
            "plots": {
                "pred_vs_actual": pvap,
                "residuals": residp,
                "feature_importances": fi_path
            },
            "data_points": int(len(df)),
            "predictions_path": predictions_path
        }
        summary_path = os.path.join(result_dir, f"{save_prefix}_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Visualization complete. Summary saved: %s", summary_path)
        return summary

    except Exception as e:
        logger.exception("Visualization failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/visualize/userresults")
async def visualize_results(payload: dict = Body(default={})):
    try:
        if "files" not in payload:
            raise HTTPException(status_code=400, detail="Payload must include 'files'")

        file_names = payload["files"]
        combined_html_parts = []

        for name in file_names:
            file_path = os.path.join(result_dir, name)

            if not os.path.exists(file_path):
                combined_html_parts.append(
                    f"<div style='color:red'>⚠ File not found: {file_path}</div>"
                )
                continue

            ext = os.path.splitext(name)[1].lower()

            # ---------------------------
            # HTML FILE
            # ---------------------------
            if ext in [".html", ".htm"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                wrapped = f"""
                <section style="margin-bottom:30px; padding:20px; border:1px solid #ccc; border-radius:8px;">
                    <h2>HTML Resource: {name}</h2>
                    <div>{content}</div>
                </section>
                """
                combined_html_parts.append(wrapped)

            # ---------------------------
            # PDF FILE
            # ---------------------------
            elif ext == ".pdf":
                wrapped = f"""
                <section style="margin-bottom:30px; padding:20px; border:1px solid #ccc; border-radius:8px;">
                    <h2>PDF Resource: {name}</h2>
                    <embed src="/static/{name}"
                           type="application/pdf"
                           width="100%" height="800px" />
                </section>
                """
                combined_html_parts.append(wrapped)

            else:
                combined_html_parts.append(
                    f"<p style='color:orange'>Unsupported file type: {name}</p>"
                )

        final_page = f"""
        <html>
        <head>
            <title>Combined Resource Visualization</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background: #f7f7f7;
                }}
                h1 {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
            </style>
        </head>
        <body>
            <h1>Visualization Results</h1>
            {''.join(combined_html_parts)}
        </body>
        </html>
        """

        return HTMLResponse(content=final_page, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DV_MCP_PORT", 10030))
    uvicorn.run(app, host="0.0.0.0", port=port)
