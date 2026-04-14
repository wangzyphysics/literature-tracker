#!/bin/bash
# Daily Literature Report Automation
# Run by OpenClaw AI Assistant

cd /root/.openclaw/workspace/literature-tracker

DATE=$(date +%Y-%m-%d)
LOG_FILE="/tmp/literature_daily_${DATE}.log"

echo "========================================" | tee -a $LOG_FILE
echo "📚 Daily Literature Report - $DATE" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "Start time: $(date)" | tee -a $LOG_FILE

# 1. Fetch literature
echo -e "\n📥 Fetching literature..." | tee -a $LOG_FILE
timeout 300 python3 run_optimized_sync.py 2>&1 | tail -50 | tee -a $LOG_FILE || echo "Fetch completed or timeout" | tee -a $LOG_FILE

# 2. Generate daily data
echo -e "\n📊 Generating daily data..." | tee -a $LOG_FILE
python3 -c "
import sys
sys.path.insert(0, '.')
from regenerate_daily import regenerate_daily
regenerate_daily('$DATE')
" 2>&1 | tee -a $LOG_FILE

# 3. Check if data exists
if [ ! -f "ai_prompts/${DATE}_data.json" ]; then
    echo "⚠️ No data for $DATE" | tee -a $LOG_FILE
    exit 0
fi

# 4. Generate HTML (OpenClaw AI will handle translation separately)
echo -e "\n📝 Generating HTML..." | tee -a $LOG_FILE
python3 generate_with_local_ai.py $DATE 2>&1 | tee -a $LOG_FILE

# 5. Push to GitHub
echo -e "\n🚀 Pushing to GitHub..." | tee -a $LOG_FILE
git add -A 2>&1 | tee -a $LOG_FILE
git commit -m "📚 Daily update $DATE [OpenClaw AI]" 2>&1 | tee -a $LOG_FILE || true
git pull origin main --no-rebase 2>&1 | tee -a $LOG_FILE || true
git push origin main 2>&1 | tee -a $LOG_FILE

echo -e "\n✅ Completed at $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

# Send notification if configured
if [ -n "$DAILY_NOTIFY_URL" ]; then
    curl -s "$DAILY_NOTIFY_URL" -d "Daily report $DATE completed" || true
fi
