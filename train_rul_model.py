"""
train_rul_model.py — RUL Model Training Script
================================================
Trains a RandomForestRegressor on the NASA CMAPSS FD001 dataset to predict
Remaining Useful Life (RUL) for turbofan engines.

Usage (run from ANY directory):
    python train_rul_model.py

Dataset required:
    Dataset/nasa-turbofan-engine-degradation-simulation/train_FD001.txt
    (relative to the project root)

Output:
    models/rul_model.pkl  — pickled RandomForestRegressor
    Validation RMSE and R² score printed to stdout.
"""

import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Resolve paths relative to this script's location so the script works
# regardless of the working directory it is invoked from.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = _SCRIPT_DIR                                                # fleet_maintenance_orchestrator/
_CAPSTONE_ROOT = os.path.abspath(os.path.join(_PROJECT_ROOT, '..'))       # Capstone project/

DATASET_PATH = os.path.join(
    _CAPSTONE_ROOT,
    'Dataset',
    'nasa-turbofan-engine-degradation-simulation',
    'train_FD001.txt'
)
MODEL_OUTPUT_PATH = os.path.join(_PROJECT_ROOT, 'models', 'rul_model.pkl')


def train_model():
    print("Loading NASA CMAPSS FD001 training data...")

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found at:\n  {DATASET_PATH}\n"
            "Please ensure the NASA CMAPSS dataset is placed in:\n"
            "  <Capstone project>/Dataset/nasa-turbofan-engine-degradation-simulation/"
        )

    # Read space-separated text file.
    # Columns: engine_id, cycle, settings 1-3, sensors 1-21
    df = pd.read_csv(DATASET_PATH, sep=r'\s+', header=None)

    col_names = ['engine_id', 'cycle', 'setting_1', 'setting_2', 'setting_3']
    for i in range(1, 22):
        col_names.append(f'sensor_{i}')
    df.columns = col_names

    print(f"Loaded {len(df)} rows from {len(df['engine_id'].unique())} engines.")

    # Calculate RUL: for each engine, RUL at cycle t = max_cycle - t
    max_cycle = df.groupby('engine_id')['cycle'].max().reset_index()
    max_cycle.columns = ['engine_id', 'max_cycle']

    df = df.merge(max_cycle, on='engine_id')
    df['RUL'] = df['max_cycle'] - df['cycle']

    # Cap RUL at 125 cycles (standard piecewise-linear approach for CMAPSS FD001)
    df['RUL_capped'] = df['RUL'].clip(upper=125)

    features = [
        'setting_1', 'setting_2', 'setting_3',
        'sensor_2', 'sensor_11', 'sensor_9', 'sensor_8', 'sensor_15'
    ]

    X = df[features]
    y = df['RUL_capped']

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"Training set: {len(X_train)} samples | Validation set: {len(X_val)} samples")
    print("Training Random Forest Regressor (n_estimators=100, max_depth=12)...")

    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    print(f"\n=== Model Evaluation ===")
    print(f"Validation RMSE : {rmse:.2f} cycles")
    print(f"Validation R²   : {r2:.4f}")
    print("========================\n")

    # Save
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    with open(MODEL_OUTPUT_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to: {MODEL_OUTPUT_PATH}")


if __name__ == '__main__':
    train_model()
