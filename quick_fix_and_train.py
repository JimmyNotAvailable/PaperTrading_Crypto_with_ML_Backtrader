import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from aidea_folder.learn_model import train_model

# Generate synthetic crypto data for demonstration
def create_synthetic_crypto_data(symbols=None, hours=1000):
    if symbols is None:from datetime import datetime, timedelta
    try:
        from aidea_folder.learn_model import train_model
    except Exception:
        # Fallback simple train_model implementation when aidea_folder is not available.
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        import joblib

        def train_model(csv_path):
            df = pd.read_csv(csv_path, parse_dates=['timestamp'])
            df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
            df['prev_close'] = df.groupby('symbol')['close'].shift(1).fillna(method='bfill')
            features = df[['prev_close', 'volume']].fillna(0)
            target = df['close']
            scaler = StandardScaler()
            X = scaler.fit_transform(features)
            X_train, X_test, y_train, y_test = train_test_split(X, target, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(X_train, y_train)
            joblib.dump(model, 'fallback_model.joblib')
            joblib.dump(scaler, 'fallback_scaler.joblib')
            return model, scaler
        symbols = ['BTC', 'ETH', 'BNB']
    data = []
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    for symbol in symbols:
        current_price = random.uniform(20000, 60000) if symbol == 'BTC' else random.uniform(1000, 4000) if symbol == 'ETH' else random.uniform(200, 600)
        for i in range(hours):
            timestamp = start_time + timedelta(hours=i)
            open_price = current_price * (1 + random.uniform(-0.02, 0.02))
            high_price = open_price * (1 + random.uniform(0, 0.03))
            low_price = open_price * (1 + random.uniform(-0.03, 0))
            close_price = random.uniform(low_price, high_price)
            volume = random.uniform(100, 10000)
            data.append([timestamp, symbol, open_price, high_price, low_price, close_price, volume])
            current_price = close_price

    df = pd.DataFrame(data, columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
    df = df.sort_values(by=['timestamp', 'symbol']).reset_index(drop=True)
    return df

# Save the synthetic data to a CSV file
synthetic_data = create_synthetic_crypto_data()
synthetic_data.to_csv('synthetic_crypto_data.csv', index=False)

# Train the model with the synthetic data
model, scaler = train_model('synthetic_crypto_data.csv')
print("Model training completed with synthetic data.")
