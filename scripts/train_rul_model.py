import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

def train_model():
    print("Loading NASA CMAPSS FD001 training data...")
    train_path = 'Dataset/nasa-turbofan-engine-degradation-simulation/train_FD001.txt'
    
    if not os.path.exists(train_path):
        # Let's check if the path is relative to the Capstone project folder
        train_path = '../Dataset/nasa-turbofan-engine-degradation-simulation/train_FD001.txt'
    
    # Read space separated text file
    # Columns are:
    # 0: engine_id, 1: cycle, 2-4: settings 1-3, 5-25: sensors 1-21
    df = pd.read_csv(train_path, sep=r'\s+', header=None)
    
    # Give columns names to keep it clean
    col_names = ['engine_id', 'cycle', 'setting_1', 'setting_2', 'setting_3']
    for i in range(1, 22):
        col_names.append(f'sensor_{i}')
    df.columns = col_names
    
    print(f"Loaded {len(df)} rows of training data.")
    
    # Calculate RUL for each engine
    # Group by engine_id to find max_cycle
    max_cycle = df.groupby('engine_id')['cycle'].max().reset_index()
    max_cycle.columns = ['engine_id', 'max_cycle']
    
    df = df.merge(max_cycle, on='engine_id')
    df['RUL'] = df['max_cycle'] - df['cycle']
    
    # Cap RUL at 125 cycles to improve model accuracy (standard piecewise linear RUL)
    df['RUL_capped'] = df['RUL'].clip(upper=125)
    
    # Select features that match our synthetic telemetry and are most predictive
    # setting_1 -> Altitude
    # setting_2 -> Mach_Number
    # setting_3 -> Throttle_Resolver_Angle
    # sensor_2  -> T24_LPC_Outlet_Temp
    # sensor_11 -> P30_HPC_Outlet_Pressure (Ps30 static pressure at HPC outlet)
    # sensor_9  -> Nf_Fan_Speed
    # sensor_8  -> Nc_Core_Speed
    # sensor_15 -> BPR_Bypass_Ratio
    
    features = [
        'setting_1', 'setting_2', 'setting_3',
        'sensor_2', 'sensor_11', 'sensor_9', 'sensor_8', 'sensor_15'
    ]
    
    X = df[features]
    y = df['RUL_capped']
    
    # Split into train/validation sets
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Regressor...")
    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    r2 = r2_score(y_val, y_pred)
    print(f"Validation RMSE: {rmse:.2f} cycles")
    print(f"Validation R2 Score: {r2:.4f}")
    
    # Save the model
    os.makedirs('models', exist_ok=True)
    with open('models/rul_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    print("Saved model to models/rul_model.pkl")

if __name__ == '__main__':
    train_model()
