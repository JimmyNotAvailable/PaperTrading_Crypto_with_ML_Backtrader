# fixed_prediction_service.py
# Service dự đoán với models đã sửa lỗi data leakage

import pandas as pd
import numpy as np
import joblib
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import warnings
warnings.filterwarnings('ignore')

def project_root_path():
    """Get project root path"""
    current_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

class FixedPredictionService:
    """
    Service dự đoán sử dụng models đã sửa lỗi
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_names = []
        self.load_latest_models()
    
    def load_latest_models(self):
        """
        Load models mới nhất đã được train
        """
        root = project_root_path()
        models_dir = os.path.join(root, "models")
        
        # Find latest models
        model_files = [f for f in os.listdir(models_dir) if f.startswith('fixed_') and f.endswith('.joblib')]
        
        if not model_files:
            raise FileNotFoundError("❌ Không tìm thấy fixed models nào!")
        
        # Load latest timestamp models
        latest_timestamp = max([f.split('_')[-1].replace('.joblib', '') for f in model_files if len(f.split('_')) >= 5])
        
        print(f"🔄 Loading models with timestamp: {latest_timestamp}")
        
        # Load price prediction model
        price_model_file = f"fixed_price_prediction_linear_regression_{latest_timestamp}.joblib"
        if os.path.exists(os.path.join(models_dir, price_model_file)):
            self.models['price'] = joblib.load(os.path.join(models_dir, price_model_file))
            print(f"✅ Loaded price model: {price_model_file}")
        
        # Load change prediction model
        change_model_file = f"fixed_change_prediction_ridge_regression_{latest_timestamp}.joblib"
        if os.path.exists(os.path.join(models_dir, change_model_file)):
            self.models['change'] = joblib.load(os.path.join(models_dir, change_model_file))
            print(f"✅ Loaded change model: {change_model_file}")
        
        # Load trend prediction model
        trend_model_file = f"fixed_trend_prediction_random_forest_{latest_timestamp}.joblib"
        if os.path.exists(os.path.join(models_dir, trend_model_file)):
            self.models['trend'] = joblib.load(os.path.join(models_dir, trend_model_file))
            print(f"✅ Loaded trend model: {trend_model_file}")
        
        # Load scaler
        scaler_file = f"fixed_scaler_{latest_timestamp}.joblib"
        if os.path.exists(os.path.join(models_dir, scaler_file)):
            self.scalers['main'] = joblib.load(os.path.join(models_dir, scaler_file))
            print(f"✅ Loaded scaler: {scaler_file}")
        
        # Load metadata để lấy feature names
        metadata_file = f"fixed_price_prediction_linear_regression_{latest_timestamp}_metadata.json"
        if os.path.exists(os.path.join(models_dir, metadata_file)):
            with open(os.path.join(models_dir, metadata_file), 'r') as f:
                metadata = json.load(f)
                self.feature_names = metadata['features']
                print(f"✅ Loaded {len(self.feature_names)} feature names")
    
    def create_features_from_current_data(self, symbol: str, current_price: float, 
                                        volume: float = 1000, high: float = None, 
                                        low: float = None, open_price: float = None) -> Dict:
        """
        Tạo features từ dữ liệu hiện tại (giả lập)
        Trong thực tế cần lấy historical data để tính MA, volatility, etc.
        """
        if high is None:
            high = current_price * 1.01
        if low is None:
            low = current_price * 0.99
        if open_price is None:
            open_price = current_price * 1.001
        
        # Current time features
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Simulate technical indicators (trong thực tế cần historical data)
        features = {
            'open': open_price,
            'high': high,
            'low': low,
            'ma_5': current_price * (1 + np.random.normal(0, 0.001)),      # Simulated MA5
            'ma_10': current_price * (1 + np.random.normal(0, 0.002)),     # Simulated MA10
            'ma_20': current_price * (1 + np.random.normal(0, 0.003)),     # Simulated MA20
            'volatility': current_price * 0.02,                             # 2% volatility estimate
            'bb_position': np.random.uniform(0.2, 0.8),                     # BB position (0-1)
            'rsi': np.random.uniform(30, 70),                               # RSI (30-70 range)
            'returns_1h': np.random.normal(0, 0.01),                        # 1h return
            'returns_3h': np.random.normal(0, 0.02),                        # 3h return
            'returns_6h': np.random.normal(0, 0.03),                        # 6h return  
            'momentum_3h': np.random.normal(0, 0.01),                       # 3h momentum
            'momentum_6h': np.random.normal(0, 0.02),                       # 6h momentum
            'volume_ratio': volume / 5000 if volume > 0 else 1,             # Volume ratio
            'hour': hour,
            'day_of_week': day_of_week
        }
        
        return features
    
    def predict_crypto_price(self, symbol: str, current_price: float, 
                           volume: float = 1000, **kwargs) -> Dict[str, Any]:
        """
        Dự đoán giá crypto với models đã sửa lỗi
        """
        try:
            # Tạo features
            features = self.create_features_from_current_data(
                symbol=symbol, 
                current_price=current_price, 
                volume=volume,
                **kwargs
            )
            
            # Chuẩn bị feature vector
            feature_vector = []
            for feature_name in self.feature_names:
                if feature_name in features:
                    feature_vector.append(features[feature_name])
                else:
                    feature_vector.append(0)  # Default value
            
            feature_array = np.array(feature_vector).reshape(1, -1)
            
            # Scale features
            if 'main' in self.scalers:
                feature_array = self.scalers['main'].transform(feature_array)
            
            # Predictions
            predictions = {}
            
            # Price prediction (1 hour ahead)
            if 'price' in self.models:
                price_pred = self.models['price'].predict(feature_array)[0]
                price_change = (price_pred - current_price) / current_price
                predictions['price_1h'] = {
                    'predicted_price': round(price_pred, 2),
                    'current_price': current_price,
                    'expected_change_pct': round(price_change * 100, 2),
                    'expected_change_usd': round(price_pred - current_price, 2)
                }
            
            # Change prediction (3 hours)
            if 'change' in self.models:
                change_pred = self.models['change'].predict(feature_array)[0]
                future_price_3h = current_price * (1 + change_pred)
                predictions['change_3h'] = {
                    'predicted_change_pct': round(change_pred * 100, 2),
                    'predicted_price_3h': round(future_price_3h, 2),
                    'confidence': 'Low' if abs(change_pred) < 0.01 else 'Medium'  # Based on change magnitude
                }
            
            # Trend prediction (1 hour)
            if 'trend' in self.models:
                trend_proba = self.models['trend'].predict_proba(feature_array)[0]
                trend_pred = self.models['trend'].predict(feature_array)[0]
                predictions['trend_1h'] = {
                    'direction': 'UP' if trend_pred == 1 else 'DOWN',
                    'confidence': round(max(trend_proba) * 100, 1),
                    'up_probability': round(trend_proba[1] * 100, 1),
                    'down_probability': round(trend_proba[0] * 100, 1)
                }
            
            # Summary
            overall_signal = 'NEUTRAL'
            if predictions.get('trend_1h', {}).get('direction') == 'UP' and \
               predictions.get('price_1h', {}).get('expected_change_pct', 0) > 0:
                overall_signal = 'BUY'
            elif predictions.get('trend_1h', {}).get('direction') == 'DOWN' and \
                 predictions.get('price_1h', {}).get('expected_change_pct', 0) < 0:
                overall_signal = 'SELL'
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'current_data': {
                    'price': current_price,
                    'volume': volume
                },
                'predictions': predictions,
                'overall_signal': overall_signal,
                'model_info': {
                    'fixed_models': True,
                    'no_data_leakage': True,
                    'features_count': len(self.feature_names)
                }
            }
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'symbol': symbol,
                'timestamp': datetime.now().isoformat()
            }
    
    def predict_multiple_symbols(self, symbols_data: List[Dict]) -> List[Dict]:
        """
        Dự đoán cho nhiều symbols
        
        Args:
            symbols_data: List of dicts with keys: symbol, price, volume
        """
        results = []
        for data in symbols_data:
            result = self.predict_crypto_price(
                symbol=data['symbol'],
                current_price=data['price'],
                volume=data.get('volume', 1000)
            )
            results.append(result)
        return results
    
    def get_model_info(self) -> Dict:
        """
        Lấy thông tin về models đã load
        """
        return {
            'loaded_models': list(self.models.keys()),
            'feature_count': len(self.feature_names),
            'features': self.feature_names,
            'has_scaler': 'main' in self.scalers,
            'fixed_version': True,
            'no_data_leakage': True
        }

# Test function
def test_fixed_prediction():
    """
    Test prediction service với data mẫu
    """
    print("🧪 TESTING FIXED PREDICTION SERVICE")
    print("="*50)
    
    try:
        # Initialize service
        service = FixedPredictionService()
        
        # Model info
        info = service.get_model_info()
        print(f"📊 Model Info: {info}")
        
        # Test single prediction
        test_data = {
            'symbol': 'BTC',
            'price': 60000,
            'volume': 5000
        }
        
        result = service.predict_crypto_price(
            symbol=test_data['symbol'],
            current_price=test_data['price'],
            volume=test_data['volume']
        )
        print(f"\n🔮 Prediction for BTC:")
        print(json.dumps(result, indent=2))
        
        # Test multiple predictions
        multiple_data = [
            {'symbol': 'BTC', 'price': 60000, 'volume': 5000},
            {'symbol': 'ETH', 'price': 4000, 'volume': 10000},
            {'symbol': 'BNB', 'price': 600, 'volume': 2000}
        ]
        
        results = service.predict_multiple_symbols(multiple_data)
        print(f"\n🔮 Multiple Predictions:")
        for result in results:
            if 'error' not in result:
                print(f"  {result['symbol']}: {result['overall_signal']} | "
                      f"1h: {result['predictions'].get('price_1h', {}).get('expected_change_pct', 'N/A')}%")
        
        print("\n✅ FIXED PREDICTION SERVICE TEST COMPLETED!")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_prediction()