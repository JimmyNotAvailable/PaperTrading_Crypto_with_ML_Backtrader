"""
Multi-Symbol Training and Testing Script
=========================================
Comprehensive script to train models and test the multi-symbol system.

This script will:
1. Train ML models for all supported symbols (BTC, ETH, XRP, SOL, BNB)
2. Verify models are saved correctly
3. Test the ML Consumer with multi-symbol data
"""
import sys
import time
import subprocess
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.symbols_config import get_all_symbols, get_base_symbol

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_virtual_env():
    """Check if virtual environment is activated."""
    venv_active = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not venv_active:
        print("⚠️ Virtual environment not detected!")
        print("Please activate: .\\crypto-venv\\Scripts\\Activate.ps1")
        return False
    
    print("✅ Virtual environment active")
    return True


def train_all_models():
    """Train models for all supported symbols."""
    print_section("Step 1: Training ML Models for All Symbols")
    
    print("🎯 Training models for: BTC, ETH, XRP, SOL, BNB")
    print("⏰ This will take approximately 5-10 minutes...\n")
    
    # Run training script with --all flag
    try:
        subprocess.run(
            ["python", "app\\ml\\train_models.py", "--all"],
            check=True
        )
        print("\n✅ All models trained successfully!")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Training failed! Check errors above.")
        return False


def verify_models():
    """Verify that all model files exist."""
    print_section("Step 2: Verifying Model Files")
    
    models_dir = Path("app/ml/models")
    required_models = ['random_forest', 'svm', 'logistic_regression']
    symbols = [get_base_symbol(s) for s in get_all_symbols()]
    
    all_exist = True
    
    for symbol in symbols:
        print(f"\nChecking {symbol} models:")
        for model_name in required_models:
            model_file = models_dir / f"{model_name}_{symbol}_latest.joblib"
            
            if model_file.exists():
                size_kb = model_file.stat().st_size / 1024
                print(f"  ✅ {model_name}_{symbol}_latest.joblib ({size_kb:.1f} KB)")
            else:
                print(f"  ❌ {model_name}_{symbol}_latest.joblib NOT FOUND")
                all_exist = False
    
    if all_exist:
        print("\n✅ All model files verified!")
    else:
        print("\n⚠️ Some models are missing. Training may have failed.")
    
    return all_exist


def test_symbols_config():
    """Test symbols configuration."""
    print_section("Step 3: Testing Symbols Configuration")
    
    try:
        subprocess.run(
            ["python", "config\\symbols_config.py"],
            check=True
        )
        print("\n✅ Symbols configuration working correctly!")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Symbols configuration test failed!")
        return False


def print_next_steps():
    """Print instructions for next steps."""
    print_section("Next Steps: Testing the Complete System")
    
    print("🎯 To test the multi-symbol ML prediction system:\n")
    
    print("Terminal 1 - Start ML Consumer:")
    print("  .\\crypto-venv\\Scripts\\Activate.ps1")
    print("  python app\\consumers\\ml_predictor.py\n")
    
    print("Terminal 2 - Start Producer (All Symbols):")
    print("  .\\crypto-venv\\Scripts\\Activate.ps1")
    print("  python app\\producers\\multi_symbol_producer.py --all --parallel\n")
    
    print("Terminal 3 - Monitor ML Signals:")
    print("  .\\crypto-venv\\Scripts\\Activate.ps1")
    print("  python test_phase3_debug_ml_signals.py\n")
    
    print("Or test specific symbols:")
    print("  python app\\producers\\multi_symbol_producer.py --symbols BTC ETH SOL\n")
    
    print("📊 You should see predictions for all 5 symbols:")
    print("  - BTC (Bitcoin)")
    print("  - ETH (Ethereum)")
    print("  - XRP (Ripple)")
    print("  - SOL (Solana)")
    print("  - BNB (Binance Coin)\n")


def main():
    """Main workflow."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        Multi-Symbol ML Trading System - Setup & Test            ║
║                                                                  ║
║  This script will train models for all supported symbols:       ║
║  BTC, ETH, XRP, SOL, BNB                                        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Check environment
    if not check_virtual_env():
        return
    
    # Ask user for confirmation
    print("\n⚠️ This will train 15 models (3 models × 5 symbols)")
    print("⏰ Estimated time: 5-10 minutes")
    response = input("\n👉 Continue? (y/n): ").lower().strip()
    
    if response != 'y':
        print("❌ Cancelled by user")
        return
    
    # Step 1: Train all models
    if not train_all_models():
        return
    
    time.sleep(1)
    
    # Step 2: Verify models
    if not verify_models():
        print("\n⚠️ Warning: Some models missing, but continuing...")
    
    time.sleep(1)
    
    # Step 3: Test config
    test_symbols_config()
    
    # Print next steps
    print_next_steps()
    
    print("\n✅ Setup complete! Follow the instructions above to test the system.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
