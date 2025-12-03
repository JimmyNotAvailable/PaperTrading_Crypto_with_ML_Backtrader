# 📊 Hybrid Training Report - BTC/USDT
**Date**: November 29, 2025  
**Strategy**: Train on Historical (2023) → Test on Real-Time (Nov 2025)

---

## 🎯 Executive Summary

**CRITICAL FINDING**: Model KHÔNG generalize từ historical data (2023) sang real-time market (2025)

### Accuracy Comparison

| Model | Historical Val (2023) | Real-Time Test (Nov 2025) | **Generalization Gap** |
|-------|----------------------|---------------------------|------------------------|
| Random Forest | **52.57%** | **50.78%** | ⚠️ -1.79% |
| SVM | **55.48%** | **49.22%** | 🔴 **-6.26%** |
| Logistic Regression | **55.34%** | **49.00%** | 🔴 **-6.34%** |

**All models perform worse than random chance (~50%) on real-time data!**

---

## 📈 Training Details

### Phase 1: Historical Data (2023)
- **Date Range**: March 25, 2023 → October 19, 2023
- **Total Samples**: 4,951 (after feature engineering)
- **Train**: 3,465 samples (70%)
- **Val**: 743 samples (15%)
- **Test**: 743 samples (15%)

### Phase 2: Real-Time Data (Nov 2025)
- **Date Range**: November 10, 2025 → November 29, 2025
- **Total Samples**: 451
- **Purpose**: Final generalization test

### Anti-Overfitting Pipeline
✅ **Applied**:
- IQR outlier removal (4.99% train, 2.96% val/test)
- RobustScaler per symbol
- Class balancing (1635 DOWN, 1635 UP)
- 26 technical features (MACD, ATR, EMA, RSI, etc.)

---

## 🔍 Performance Analysis

### Random Forest (Best Real-Time: 50.78%)
**Historical Val Performance**:
```
              precision    recall  f1-score   support
        DOWN       0.51      0.43      0.46       348
          UP       0.54      0.62      0.57       373
    accuracy                           0.53       721
```

**Real-Time Performance** 🔴:
```
              precision    recall  f1-score   support
        DOWN       0.51      1.00      0.67       229  ← Predicts only DOWN!
          UP       0.00      0.00      0.00       222  ← Never predicts UP
    accuracy                           0.51       451
```

**Issue**: Model collapsed to predicting only DOWN class on real-time data.

---

### SVM (Worst Real-Time: 49.22%)
**Historical Val Performance**:
```
              precision    recall  f1-score   support
        DOWN       0.55      0.40      0.47       348
          UP       0.56      0.70      0.62       373
    accuracy                           0.55       721
```

**Real-Time Performance** 🔴:
```
              precision    recall  f1-score   support
        DOWN       0.00      0.00      0.00       229  ← Never predicts DOWN!
          UP       0.49      1.00      0.66       222  ← Predicts only UP
    accuracy                           0.49       451
```

**Issue**: Model collapsed to predicting only UP class on real-time data (opposite of Random Forest).

---

### Logistic Regression (49.00%)
**Real-Time Performance** 🔴:
```
              precision    recall  f1-score   support
        DOWN       0.50      0.79      0.61       229
          UP       0.45      0.18      0.25       222  ← Very low recall for UP
    accuracy                           0.49       451
```

**Issue**: Heavy bias toward DOWN class, poor UP detection.

---

## 🚨 Root Cause Analysis

### 1. **Market Regime Change** (Primary Issue)
- **2023 data**: Bear/sideways market (post-FTX crash, pre-halving)
- **Nov 2025 data**: Bull market (Trump election, institutional adoption)
- **Result**: Features learned from 2023 don't apply to 2025 market dynamics

### 2. **Feature Distribution Shift**
Historical data (2023):
- Lower volatility
- Different price ranges ($20k-$30k BTC)
- Pre-ETF approval market structure

Real-time data (Nov 2025):
- Higher volatility
- Different price ranges ($90k+ BTC)
- Post-ETF, post-halving market

### 3. **Temporal Decay**
**2-year gap** between training data (2023) and real-time data (2025) is too large for crypto markets.

### 4. **Class Imbalance in Real-Time**
Real-time test set may have different UP/DOWN distribution than balanced historical training set.

---

## 📊 Data Statistics

### Historical Training Data (2023)
```
Features: 26 indicators
  - Trend: SMA_10, SMA_50, EMA_12, EMA_26
  - Momentum: RSI_14, MACD, MACD_signal, MACD_hist
  - Volatility: ATR_14, BB_WIDTH, Volatility_20
  - Volume: Volume_SMA, Volume_Ratio
  - Price: Returns_1, Returns_5, Returns_10, Price_Change_Pct

Outliers Removed: 217 samples (4.4%)
Class Balance: 50% DOWN, 50% UP (after undersampling)
```

### Real-Time Test Data (Nov 2025)
```
Samples: 451
Date Range: 19 days (Nov 10-29, 2025)
Class Distribution:
  - DOWN: 229 samples (50.8%)
  - UP: 222 samples (49.2%)
```

---

## ✅ What Worked

1. **Anti-overfitting pipeline** ran successfully
2. **Historical validation** showed reasonable accuracy (~53-55%)
3. **Data pipeline** loaded both historical CSV and real-time API data
4. **Feature engineering** calculated 26 indicators correctly
5. **Class balancing** prevented overfitting to majority class

---

## ❌ What Failed

1. **Generalization**: Models learned 2023 patterns that don't apply to 2025
2. **Class prediction**: Models collapsed to single-class predictions on real-time data
3. **Accuracy**: All models ≤50.78% (worse than coin flip)
4. **Feature stability**: 2-year gap caused feature distribution shift

---

## 🔧 Recommended Solutions

### Option 1: **Retrain with Recent Data** ⭐ RECOMMENDED
```python
# Use last 6-12 months of data (Dec 2024 - Nov 2025)
python app/ml/hybrid_train_models.py --symbol BTC --historical 4000 --realtime 500
```
**Pros**:
- Features learned from similar market regime
- Reduced temporal decay
- Better generalization to current market

**Cons**:
- Need to fetch recent historical data (Binance API or CSV)

---

### Option 2: **Online Learning / Continuous Retraining**
```python
# Retrain model weekly with rolling window (last 90 days)
Schedule: Every Monday 00:00 UTC
Window: 2160 samples (90 days × 24 hours)
```
**Pros**:
- Model adapts to market changes
- Always uses fresh data
- Production-ready solution

**Cons**:
- Requires automation infrastructure
- Higher computational cost

---

### Option 3: **Ensemble with Market Regime Detection**
```python
# Train separate models for different market regimes
if current_regime == 'bull':
    model = bull_market_model
elif current_regime == 'bear':
    model = bear_market_model
else:
    model = sideways_market_model
```
**Pros**:
- Handles regime changes
- Better accuracy per regime

**Cons**:
- Complex to implement
- Need regime detection algorithm

---

### Option 4: **Deep Learning (LSTM/Transformer)**
```python
# Use LSTM to capture temporal dependencies
model = LSTM(input_size=26, hidden_size=128, num_layers=2)
```
**Pros**:
- Better at capturing non-linear patterns
- Can handle longer sequences

**Cons**:
- Requires more data (>10,000 samples)
- Harder to debug/interpret
- Risk of overfitting

---

## 📝 Next Steps

### Immediate Actions (Next 24 hours)
1. ✅ **Fetch recent historical data** (Dec 2024 - Oct 2025)
   - Use Binance API: `fetch_ohlcv('BTC/USDT', '1h', since='2024-12-01')`
   - Save to `data/historical/Crypto_Data_2024_2025/`

2. ✅ **Retrain with recent data**
   ```bash
   python app/ml/hybrid_train_models.py --symbol BTC --historical 8000 --realtime 500
   ```
   Expected: 8000 samples (Dec 2024 - Oct 2025) for training

3. ✅ **Validate generalization**
   - Target: Real-time accuracy ≥ 60%
   - Acceptable gap: ≤5% between historical and real-time accuracy

### Short-Term (Next week)
4. ⏳ **Train all symbols** (ETH, SOL, BNB) with recent data
5. ⏳ **Implement A/B testing** (old model vs new model)
6. ⏳ **Set up monitoring** for accuracy drift

### Long-Term (Next month)
7. ⏳ **Implement online learning** (weekly retraining)
8. ⏳ **Explore LSTM/Transformer** architectures
9. ⏳ **Deploy to production** if accuracy ≥65%

---

## 📌 Conclusion

**The hybrid training strategy works correctly**, but reveals a critical issue:

> **2-year-old data is USELESS for predicting current crypto markets.**

**Action Required**:
- ✅ Use **recent data (last 6-12 months)** for training
- ✅ Implement **continuous retraining** (weekly/monthly)
- ✅ Monitor **accuracy drift** in production

**Acceptable Accuracy Target**:
- Historical Validation: ≥60%
- Real-Time Test: ≥58% (allow 2-5% generalization gap)

---

## 📁 Files Generated
```
app/ml/models/random_forest_BTC_20251129_111610.joblib
app/ml/models/svm_BTC_20251129_111610.joblib
app/ml/models/logistic_regression_BTC_20251129_111610.joblib
app/ml/models/metadata_BTC_20251129_111610.joblib
```

⚠️ **Warning**: These models should NOT be deployed to production due to poor real-time performance.
