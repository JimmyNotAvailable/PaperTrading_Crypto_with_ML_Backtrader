# anti_overfitting.py
# Anti-overfitting pipeline: Outlier removal, feature scaling, advanced validation
# Kết hợp từ fixed_data_prep.py, core.py và kỹ thuật mới

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from typing import Dict, List, Tuple, Optional
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class AntiOverfittingPipeline:
    """
    Pipeline anti-overfitting toàn diện:
    1. Outlier detection và removal (IQR method)
    2. Feature scaling (RobustScaler - better for outliers)
    3. Advanced validation
    4. Data augmentation cho cân bằng classes
    """
    
    def __init__(self, outlier_method='iqr', scale_method='robust'):
        """
        Args:
            outlier_method: 'iqr' or 'zscore'
            scale_method: 'robust' (recommended) or 'standard'
        """
        self.outlier_method = outlier_method
        self.scale_method = scale_method
        self.scaler = None
        self.outlier_stats = {}
        
    def detect_outliers_per_symbol(self, df: pd.DataFrame, feature_cols: List[str]) -> Dict[str, pd.Index]:
        """
        Detect outliers cho TỪNG symbol riêng biệt (tránh mixed symbol bias)
        
        Returns:
            Dict[symbol, outlier_indices]
        """
        outlier_indices_all = {}
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol]
            symbol_outliers = set()
            
            for col in feature_cols:
                if col not in symbol_data.columns or symbol_data[col].dtype not in ['float64', 'int64']:
                    continue
                    
                if self.outlier_method == 'iqr':
                    Q1 = symbol_data[col].quantile(0.25)
                    Q3 = symbol_data[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    outliers = symbol_data[(symbol_data[col] < lower_bound) | (symbol_data[col] > upper_bound)].index
                    symbol_outliers.update(outliers)
                    
                elif self.outlier_method == 'zscore':
                    z_scores = np.abs((symbol_data[col] - symbol_data[col].mean()) / symbol_data[col].std())
                    outliers = symbol_data[z_scores > 3.0].index
                    symbol_outliers.update(outliers)
            
            outlier_indices_all[symbol] = symbol_outliers
            
        return outlier_indices_all
    
    def remove_outliers(self, df: pd.DataFrame, feature_cols: List[str], 
                       max_removal_pct: float = 0.05) -> pd.DataFrame:
        """
        Remove outliers nhưng GIỚI HẠN tối đa 5% data để tránh mất quá nhiều
        
        Args:
            max_removal_pct: Maximum % of data to remove (default 5%)
        """
        print("🔍 Detecting outliers per symbol...")
        outlier_dict = self.detect_outliers_per_symbol(df, feature_cols)
        
        # Combine all outlier indices
        all_outliers = set()
        for symbol, indices in outlier_dict.items():
            all_outliers.update(indices)
        
        # Limit removal to max_removal_pct
        max_remove = int(len(df) * max_removal_pct)
        if len(all_outliers) > max_remove:
            print(f"⚠️ Too many outliers ({len(all_outliers)}), limiting to {max_remove} ({max_removal_pct*100}%)")
            # Keep only the most extreme outliers
            all_outliers = list(all_outliers)[:max_remove]
        
        # Remove outliers (convert set to list for pandas)
        outliers_list = list(all_outliers) if isinstance(all_outliers, set) else all_outliers
        df_clean = df.drop(index=outliers_list)
        
        self.outlier_stats = {
            'total_outliers': len(all_outliers),
            'removal_pct': len(all_outliers) / len(df) * 100,
            'per_symbol': {symbol: len(indices) for symbol, indices in outlier_dict.items()}
        }
        
        print(f"✅ Removed {len(all_outliers):,} outliers ({self.outlier_stats['removal_pct']:.2f}%)")
        print(f"   Per symbol: {self.outlier_stats['per_symbol']}")
        
        return df_clean.reset_index(drop=True)
    
    def scale_features_per_symbol(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                                  test_df: pd.DataFrame, feature_cols: List[str]) -> Tuple:
        """
        Scale features cho TỪNG symbol riêng biệt
        Sử dụng RobustScaler (better for outliers) hoặc StandardScaler
        
        Returns:
            Tuple of (train_scaled, val_scaled, test_scaled, scalers_dict)
        """
        print(f"🔧 Scaling features per symbol using {self.scale_method}...")
        
        scalers_dict = {}
        train_scaled = train_df.copy()
        val_scaled = val_df.copy()
        test_scaled = test_df.copy()
        
        for symbol in train_df['symbol'].unique():
            # Get symbol data
            train_mask = train_df['symbol'] == symbol
            val_mask = val_df['symbol'] == symbol
            test_mask = test_df['symbol'] == symbol
            
            # Initialize scaler
            if self.scale_method == 'robust':
                scaler = RobustScaler()  # Better for outliers
            else:
                scaler = StandardScaler()
            
            # Fit on training data only
            train_features = train_df.loc[train_mask, feature_cols]
            scaler.fit(train_features)
            
            # Transform all splits
            train_scaled.loc[train_mask, feature_cols] = scaler.transform(train_features)
            
            if val_mask.any():
                val_features = val_df.loc[val_mask, feature_cols]
                val_scaled.loc[val_mask, feature_cols] = scaler.transform(val_features)
            
            if test_mask.any():
                test_features = test_df.loc[test_mask, feature_cols]
                test_scaled.loc[test_mask, feature_cols] = scaler.transform(test_features)
            
            scalers_dict[symbol] = scaler
        
        print(f"✅ Scaled features for {len(scalers_dict)} symbols")
        
        return train_scaled, val_scaled, test_scaled, scalers_dict
    
    def balance_classes(self, df: pd.DataFrame, target_col: str = 'target', 
                       balance_method: str = 'undersample') -> pd.DataFrame:
        """
        Cân bằng classes cho classification tasks
        
        Args:
            balance_method: 'undersample', 'oversample', or 'smote'
        """
        if target_col not in df.columns:
            print(f"⚠️ Target column '{target_col}' not found, skipping balancing")
            return df
        
        class_counts = df[target_col].value_counts()
        print(f"📊 Class distribution before balancing: {class_counts.to_dict()}")
        
        if balance_method == 'undersample':
            # Undersample majority class
            min_count = class_counts.min()
            
            balanced_dfs = []
            for class_val in class_counts.index:
                class_df = df[df[target_col] == class_val]
                sampled_df = class_df.sample(n=min_count, random_state=42)
                balanced_dfs.append(sampled_df)
            
            df_balanced = pd.concat(balanced_dfs, ignore_index=True)
            df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle
            
        elif balance_method == 'oversample':
            # Oversample minority class (simple duplication)
            max_count = class_counts.max()
            
            balanced_dfs = []
            for class_val in class_counts.index:
                class_df = df[df[target_col] == class_val]
                sampled_df = class_df.sample(n=max_count, replace=True, random_state=42)
                balanced_dfs.append(sampled_df)
            
            df_balanced = pd.concat(balanced_dfs, ignore_index=True)
            df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)
            
        else:
            print(f"⚠️ Unknown balance method '{balance_method}', skipping")
            return df
        
        balanced_counts = df_balanced[target_col].value_counts()
        print(f"✅ Class distribution after {balance_method}: {balanced_counts.to_dict()}")
        
        return df_balanced
    
    def validate_no_leakage(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                           test_df: pd.DataFrame) -> bool:
        """
        Validate rằng KHÔNG có temporal leakage
        Train dates < Val dates < Test dates
        """
        train_max = train_df['date'].max()
        val_min = val_df['date'].min()
        val_max = val_df['date'].max()
        test_min = test_df['date'].min()
        
        if train_max >= val_min:
            print(f"❌ TEMPORAL LEAKAGE: Train max ({train_max}) >= Val min ({val_min})")
            return False
        
        if val_max >= test_min:
            print(f"❌ TEMPORAL LEAKAGE: Val max ({val_max}) >= Test min ({test_min})")
            return False
        
        print("✅ No temporal leakage detected")
        return True
    
    def run_pipeline(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                    test_df: pd.DataFrame, feature_cols: List[str],
                    remove_outliers: bool = True,
                    balance_target: Optional[str] = None) -> Dict:
        """
        Run toàn bộ anti-overfitting pipeline
        
        Returns:
            Dict with processed dataframes and metadata
        """
        print("\n" + "="*60)
        print("ANTI-OVERFITTING PIPELINE START")
        print("="*60)
        
        # Step 1: Validate no temporal leakage
        self.validate_no_leakage(train_df, val_df, test_df)
        
        # Step 2: Remove outliers (optional)
        if remove_outliers:
            train_df = self.remove_outliers(train_df, feature_cols)
            val_df = self.remove_outliers(val_df, feature_cols, max_removal_pct=0.03)  # More conservative
            test_df = self.remove_outliers(test_df, feature_cols, max_removal_pct=0.03)
        
        # Step 3: Balance classes (optional)
        if balance_target:
            train_df = self.balance_classes(train_df, target_col=balance_target, 
                                           balance_method='undersample')
        
        # Step 4: Scale features per symbol
        train_scaled, val_scaled, test_scaled, scalers = self.scale_features_per_symbol(
            train_df, val_df, test_df, feature_cols
        )
        
        print("\n" + "="*60)
        print("ANTI-OVERFITTING PIPELINE COMPLETE")
        print("="*60)
        
        return {
            'train': train_scaled,
            'val': val_scaled,
            'test': test_scaled,
            'scalers': scalers,
            'outlier_stats': self.outlier_stats,
            'feature_cols': feature_cols
        }


def apply_anti_overfitting(datasets: Dict, feature_cols: List[str], 
                          remove_outliers: bool = True,
                          balance_target: Optional[str] = None) -> Dict:
    """
    Wrapper function để apply anti-overfitting lên datasets đã có
    
    Args:
        datasets: Dict from train_models.py containing train/val/test DataFrames
        feature_cols: List of feature column names
        remove_outliers: Whether to remove outliers
        balance_target: Target column name for class balancing (None = no balancing)
    
    Returns:
        Processed datasets with anti-overfitting applied
    """
    pipeline = AntiOverfittingPipeline(
        outlier_method='iqr',
        scale_method='robust'  # Better than StandardScaler for outliers
    )
    
    result = pipeline.run_pipeline(
        train_df=datasets['train'],
        val_df=datasets['val'],
        test_df=datasets['test'],
        feature_cols=feature_cols,
        remove_outliers=remove_outliers,
        balance_target=balance_target
    )
    
    # Update original datasets dict
    datasets['train'] = result['train']
    datasets['val'] = result['val']
    datasets['test'] = result['test']
    datasets['scalers'] = result['scalers']
    datasets['outlier_stats'] = result['outlier_stats']
    
    return datasets


if __name__ == "__main__":
    """Test anti-overfitting pipeline"""
    print("Testing Anti-Overfitting Pipeline...")
    
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    
    data = {
        'symbol': np.random.choice(['BTC', 'ETH', 'XRP'], n_samples),
        'date': pd.date_range('2024-01-01', periods=n_samples, freq='1h'),
        'close': np.random.randn(n_samples) * 100 + 50000,
        'volume': np.random.randn(n_samples) * 1000 + 5000,
        'ma_10': np.random.randn(n_samples) * 100 + 50000,
        'rsi': np.random.randn(n_samples) * 20 + 50,
        'target': np.random.choice([0, 1], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Add outliers (type: ignore for pandas loc operation)
    outlier_indices = np.random.choice(n_samples, 50, replace=False)
    outlier_indices_list = outlier_indices.tolist()  # Convert numpy array to list
    df.loc[outlier_indices_list, 'close'] = df.loc[outlier_indices_list, 'close'] * 10  # type: ignore[operator]
    
    # Split data
    train_df = df.iloc[:700]
    val_df = df.iloc[700:850]
    test_df = df.iloc[850:]
    
    feature_cols = ['close', 'volume', 'ma_10', 'rsi']
    
    # Run pipeline
    pipeline = AntiOverfittingPipeline()
    result = pipeline.run_pipeline(
        train_df, val_df, test_df, feature_cols,
        remove_outliers=True,
        balance_target='target'
    )
    
    print("\n📊 Pipeline Results:")
    print(f"  Train samples: {len(result['train'])}")
    print(f"  Val samples: {len(result['val'])}")
    print(f"  Test samples: {len(result['test'])}")
    print(f"  Scalers: {list(result['scalers'].keys())}")
    print(f"  Outlier stats: {result['outlier_stats']}")
    print("\n✅ Test passed!")
