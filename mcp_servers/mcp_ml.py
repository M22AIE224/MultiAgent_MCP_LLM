import os
import json
import logging
import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    root_mean_squared_error,
    mean_absolute_error,
    r2_score,
)

# --------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="ML MCP Server", version="1.1")

# --------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------
def load_dataset() -> pd.DataFrame:
    """Load the processed dataset."""
    data_path = os.getenv("DATA_PROCESSED_PATH", "./processed/processed_data.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Processed data not found at {data_path}")
    df = pd.read_csv(data_path)
    logger.info(f"✅ Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def train_random_forest(X_train, y_train) -> RandomForestRegressor:
    """Train the RandomForest model."""
    model = RandomForestRegressor(random_state=42, n_estimators=200)
    model.fit(X_train, y_train)
    logger.info("✅ RandomForest training complete.")
    return model


def evaluate_model(model, X_test, y_test) -> dict:
    """Compute evaluation metrics."""
    y_pred = model.predict(X_test)

    metrics = {
        "RMSE": round(float(root_mean_squared_error(y_test, y_pred)), 4),
        "MAE": round(float(mean_absolute_error(y_test, y_pred)), 4),
        "R2": round(float(r2_score(y_test, y_pred)), 4),
    }

    logger.info(f"📊 Model metrics: {json.dumps(metrics, indent=2)}")
    return metrics, y_pred


def save_artifacts(model, y_test, y_pred, X_train, X_test, metrics) -> dict:
    """Save model, metrics, and predictions to artifacts directory."""
    model_path = os.getenv("MODEL_PATH", "./models/random_forest.pkl")
    result_dir = "./artifacts/ml_results"
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Save model
    joblib.dump(model, model_path)
    logger.info(f"💾 Model saved at {model_path}")

    # Save predictions
    pred_path = os.path.join(result_dir, "predictions.csv")
    pd.DataFrame({"y_true": y_test, "y_pred": y_pred}).to_csv(pred_path, index=False)
    logger.info(f"💾 Predictions saved at {pred_path}")

    # Save metrics
    metrics_path = os.path.join(result_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"💾 Metrics saved at {metrics_path}")

    return {
        "status": "success",
        "metrics": metrics,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "model_path": model_path,
        "predictions_path": pred_path,
        "metrics_path": metrics_path,
        "result_path": result_dir,
    }


# --------------------------------------------------------------------
# API Endpoint
# --------------------------------------------------------------------
@app.post("/critic")
async def train_model():
    """MCP to run critic"""
    try:
        logger.info("🚀 Starting model training process...")
        target_col = os.getenv("TARGET_COLUMN", "target")

        df = load_dataset()
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in dataset.")

        X = df.drop(columns=[target_col])
        y = df[target_col]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = train_random_forest(X_train, y_train)
        metrics, y_pred = evaluate_model(model, X_test, y_test)
        result = save_artifacts(model, y_test, y_pred, X_train, X_test, metrics)

        logger.info("✅ Model training complete. Returning result summary.")
        logger.info(json.dumps(result, indent=2))
        return result

    except Exception as e:
        logger.exception("Model training failed")
        raise HTTPException(status_code=500, detail=str(e))
    
# --------------------------------------------------------------------
# API Endpoint
# --------------------------------------------------------------------
@app.post("/model/train")
async def train_model():
    """Main training pipeline for RandomForest."""
    try:
        logger.info("🚀 Starting model training process...")
        target_col = os.getenv("TARGET_COLUMN", "target")

        df = load_dataset()
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in dataset.")

        X = df.drop(columns=[target_col])
        y = df[target_col]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = train_random_forest(X_train, y_train)
        metrics, y_pred = evaluate_model(model, X_test, y_test)
        result = save_artifacts(model, y_test, y_pred, X_train, X_test, metrics)

        logger.info("✅ Model training complete. Returning result summary.")
        logger.info(json.dumps(result, indent=2))
        return result

    except Exception as e:
        logger.exception("Model training failed")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------
# Main Entrypoint
# --------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ML_MCP_PORT", 10020))
    logger.info(f"🚀 ML MCP Server running on http://0.0.0.0:{port}/critic")
    uvicorn.run(app, host="0.0.0.0", port=port)
