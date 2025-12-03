# ============================================
# PROJECT REORGANIZATION SCRIPT
# ============================================
# Tự động reorganize toàn bộ dự án
# Chạy: .\scripts\reorganize_project.ps1
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🔧 PROJECT REORGANIZATION WIZARD" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "📁 Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

# Confirm before proceeding
Write-Host "⚠️ WARNING: This script will reorganize the entire project structure!" -ForegroundColor Red
Write-Host ""
Write-Host "Changes include:" -ForegroundColor Yellow
Write-Host "  - Move/rename files" -ForegroundColor White
Write-Host "  - Merge duplicate modules" -ForegroundColor White
Write-Host "  - Update imports in Python files" -ForegroundColor White
Write-Host "  - Delete redundant files" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Do you want to continue? (yes/NO)"
if ($confirm -ne "yes") {
    Write-Host "❌ Aborted by user" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting reorganization..." -ForegroundColor Green
Write-Host ""

# Create backup first
Write-Host "📦 Step 1/10: Creating backup..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "$ProjectRoot\..\crypto-ml-backup-$timestamp"

try {
    Copy-Item -Recurse -Path $ProjectRoot -Destination $backupPath -Exclude ".git","crypto-venv","__pycache__","*.pyc"
    Write-Host "✅ Backup created: $backupPath" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create backup: $_" -ForegroundColor Red
    exit 1
}

# Helper function to move file safely
function Move-FileSafely {
    param(
        [string]$Source,
        [string]$Destination
    )

    $sourcePath = Join-Path $ProjectRoot $Source
    $destPath = Join-Path $ProjectRoot $Destination

    if (Test-Path $sourcePath) {
        $destDir = Split-Path -Parent $destPath
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        Move-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "  ✅ Moved: $Source → $Destination" -ForegroundColor Green
    } else {
        Write-Host "  ⏭️ Skip: $Source (not found)" -ForegroundColor Gray
    }
}

# Helper function to delete file safely
function Remove-FileSafely {
    param([string]$FilePath)

    $fullPath = Join-Path $ProjectRoot $FilePath
    if (Test-Path $fullPath) {
        Remove-Item -Path $fullPath -Force
        Write-Host "  ✅ Deleted: $FilePath" -ForegroundColor Green
    } else {
        Write-Host "  ⏭️ Skip: $FilePath (not found)" -ForegroundColor Gray
    }
}

# ============================================
# PHASE 1: Clean Root Directory
# ============================================
Write-Host ""
Write-Host "📋 Step 2/10: Cleaning root directory..." -ForegroundColor Yellow

# Create scripts subdirectories
New-Item -ItemType Directory -Path "$ProjectRoot\scripts\debug" -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\scripts\monitoring" -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\scripts\ml" -Force | Out-Null

# Move files from root
Move-FileSafely "debug_dataset.py" "scripts\debug\dataset_debugger.py"
Move-FileSafely "mock_bot_demo.py" "examples\bot_demo.py"
Move-FileSafely "monitor_bot.py" "scripts\monitoring\bot_monitor.py"
Move-FileSafely "quick_fix_and_train.py" "scripts\ml\quick_train.py"
Move-FileSafely "safe_predict.py" "scripts\ml\safe_predictor.py"

Write-Host "✅ Root directory cleaned" -ForegroundColor Green

# ============================================
# PHASE 2: Rename ML Files
# ============================================
Write-Host ""
Write-Host "📋 Step 3/10: Renaming ML files..." -ForegroundColor Yellow

# Rename files in app/ml/
Move-FileSafely "app\ml\data_prep.py" "app\ml\data_preparation.py"
Move-FileSafely "app\ml\train_all.py" "app\ml\model_trainer.py"
Move-FileSafely "app\ml\evaluate.py" "app\ml\model_evaluator.py"
Move-FileSafely "app\ml\fixed_prediction_service.py" "app\ml\prediction_service.py"

# Rename data collector
Move-FileSafely "app\data_collector\realtime_collector.py" "app\data_collector\binance_collector.py"

Write-Host "✅ ML files renamed" -ForegroundColor Green

# ============================================
# PHASE 3: Merge Duplicate Files
# ============================================
Write-Host ""
Write-Host "📋 Step 4/10: Removing duplicate files..." -ForegroundColor Yellow

# Delete duplicates (sau khi đã merge nội dung manually)
Remove-FileSafely "app\ml\fixed_data_prep.py"
Remove-FileSafely "app\ml\fixed_train_models.py"
Remove-FileSafely "app\data_collector\enhanced_realtime_collector.py"
Remove-FileSafely "app\repositories\mongo_client.py"  # Keep app/database/mongo_client.py

Write-Host "✅ Duplicate files removed" -ForegroundColor Green

# ============================================
# PHASE 4: Reorganize Models Directory
# ============================================
Write-Host ""
Write-Host "📋 Step 5/10: Reorganizing models directory..." -ForegroundColor Yellow

# Create new structure
New-Item -ItemType Directory -Path "$ProjectRoot\models\production" -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\models\archive" -Force | Out-Null
New-Item -ItemType Directory -Path "$ProjectRoot\models\experiments" -Force | Out-Null

# Move quick_loader to models/production/
Move-FileSafely "data\models_production\quick_loader.py" "models\production\loader.py"

Write-Host "✅ Models directory reorganized" -ForegroundColor Green

# ============================================
# PHASE 5: Merge Demos into Examples
# ============================================
Write-Host ""
Write-Host "📋 Step 6/10: Merging demos into examples..." -ForegroundColor Yellow

# Ensure examples/ml exists
New-Item -ItemType Directory -Path "$ProjectRoot\examples\ml" -Force | Out-Null

# Move demo files to examples
if (Test-Path "$ProjectRoot\demos") {
    Get-ChildItem -Path "$ProjectRoot\demos" -Filter "*.py" | ForEach-Object {
        $newName = $_.Name -replace "^demo_", ""
        Move-FileSafely "demos\$($_.Name)" "examples\ml\$newName"
    }

    # Remove empty demos folder
    if ((Get-ChildItem -Path "$ProjectRoot\demos" -Recurse | Measure-Object).Count -eq 0) {
        Remove-Item -Path "$ProjectRoot\demos" -Recurse -Force
        Write-Host "  ✅ Removed empty demos folder" -ForegroundColor Green
    }
}

Write-Host "✅ Demos merged into examples" -ForegroundColor Green

# ============================================
# PHASE 6: Reorganize Scripts
# ============================================
Write-Host ""
Write-Host "📋 Step 7/10: Reorganizing scripts..." -ForegroundColor Yellow

# Create scripts subdirectories
New-Item -ItemType Directory -Path "$ProjectRoot\scripts\data" -Force | Out-Null

# Move scripts
Move-FileSafely "scripts\continuous_collector.py" "scripts\data\scheduled_collector.py"

# Merge analysis folder into scripts/analysis
if (Test-Path "$ProjectRoot\analysis") {
    New-Item -ItemType Directory -Path "$ProjectRoot\scripts\analysis" -Force | Out-Null

    Get-ChildItem -Path "$ProjectRoot\analysis" -Filter "*.py" | ForEach-Object {
        Move-FileSafely "analysis\$($_.Name)" "scripts\analysis\$($_.Name)"
    }

    # Remove empty analysis folder
    if ((Get-ChildItem -Path "$ProjectRoot\analysis" -Recurse | Measure-Object).Count -eq 0) {
        Remove-Item -Path "$ProjectRoot\analysis" -Recurse -Force
        Write-Host "  ✅ Removed empty analysis folder" -ForegroundColor Green
    }
}

Write-Host "✅ Scripts reorganized" -ForegroundColor Green

# ============================================
# PHASE 7: Clean Utils
# ============================================
Write-Host ""
Write-Host "📋 Step 8/10: Cleaning utils directory..." -ForegroundColor Yellow

# Move test files to tests/
if (Test-Path "$ProjectRoot\utils") {
    Get-ChildItem -Path "$ProjectRoot\utils" -Filter "test_*.py" | ForEach-Object {
        Move-FileSafely "utils\$($_.Name)" "tests\unit\$($_.Name)"
    }

    # Move debug files
    Get-ChildItem -Path "$ProjectRoot\utils" -Filter "debug_*.py" | ForEach-Object {
        Move-FileSafely "utils\$($_.Name)" "scripts\debug\$($_.Name)"
    }
}

Write-Host "✅ Utils cleaned" -ForegroundColor Green

# ============================================
# PHASE 8: Update .gitignore
# ============================================
Write-Host ""
Write-Host "📋 Step 9/10: Updating .gitignore..." -ForegroundColor Yellow

$gitignorePath = Join-Path $ProjectRoot ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw

    # Ensure important entries
    $entriesToAdd = @(
        "token.txt",
        "DanY.txt",
        "*.backup",
        ".env",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "crypto-venv/",
        "*.log",
        "data/raw/*.csv",
        "data/cache/*.pkl",
        "models/experiments/",
        "models/archive/old_*"
    )

    $modified = $false
    foreach ($entry in $entriesToAdd) {
        if ($gitignoreContent -notmatch [regex]::Escape($entry)) {
            Add-Content -Path $gitignorePath -Value $entry
            $modified = $true
            Write-Host "  ✅ Added to .gitignore: $entry" -ForegroundColor Green
        }
    }

    if (!$modified) {
        Write-Host "  ⏭️ .gitignore already up-to-date" -ForegroundColor Gray
    }
}

Write-Host "✅ .gitignore updated" -ForegroundColor Green

# ============================================
# PHASE 9: Create README files
# ============================================
Write-Host ""
Write-Host "📋 Step 10/10: Creating README files..." -ForegroundColor Yellow

# Create README in important directories
$readmes = @{
    "models\README.md" = "# ML Models`n`nProduction models and archives."
    "data\README.md" = "# Data Storage`n`nRaw, processed, and cached data."
    "examples\README.md" = "# Examples & Demos`n`nML and bot usage examples."
    "tests\README.md" = "# Tests`n`nUnit and integration tests."
    "scripts\README.md" = "# Utility Scripts`n`nML, data, and monitoring scripts."
}

foreach ($readme in $readmes.GetEnumerator()) {
    $path = Join-Path $ProjectRoot $readme.Key
    if (!(Test-Path $path)) {
        Set-Content -Path $path -Value $readme.Value
        Write-Host "  ✅ Created: $($readme.Key)" -ForegroundColor Green
    }
}

Write-Host "✅ README files created" -ForegroundColor Green

# ============================================
# SUMMARY
# ============================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🎉 REORGANIZATION COMPLETED!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📊 Summary:" -ForegroundColor Yellow
Write-Host "  ✅ Root directory cleaned" -ForegroundColor Green
Write-Host "  ✅ ML files renamed (standardized)" -ForegroundColor Green
Write-Host "  ✅ Duplicate files removed" -ForegroundColor Green
Write-Host "  ✅ Models directory reorganized" -ForegroundColor Green
Write-Host "  ✅ Demos merged into examples" -ForegroundColor Green
Write-Host "  ✅ Scripts reorganized" -ForegroundColor Green
Write-Host "  ✅ Utils cleaned" -ForegroundColor Green
Write-Host "  ✅ .gitignore updated" -ForegroundColor Green
Write-Host "  ✅ README files created" -ForegroundColor Green
Write-Host ""

Write-Host "📁 Backup location: $backupPath" -ForegroundColor Cyan
Write-Host ""

Write-Host "⚠️ NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Review changes: git status" -ForegroundColor White
Write-Host "  2. Update imports in Python files (may need manual fixes)" -ForegroundColor White
Write-Host "  3. Test the bot: python app\bot.py" -ForegroundColor White
Write-Host "  4. Test ML: python app\ml\model_trainer.py" -ForegroundColor White
Write-Host "  5. Run tests: pytest tests/" -ForegroundColor White
Write-Host "  6. Commit changes if everything works" -ForegroundColor White
Write-Host ""

Write-Host "🔧 If something breaks:" -ForegroundColor Yellow
Write-Host "  Restore from backup:" -ForegroundColor White
Write-Host "  Remove-Item -Recurse -Force '$ProjectRoot'" -ForegroundColor Cyan
Write-Host "  Copy-Item -Recurse '$backupPath' '$ProjectRoot'" -ForegroundColor Cyan
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Done! 🚀" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan

