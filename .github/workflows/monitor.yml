name: Spillway Monitor

on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
  workflow_dispatch:        # Manual trigger
  push:
    branches: [ main, master ]
    paths:
      - 'spillway_monitor/**'
      - '.github/workflows/spillway-monitor.yml'
      - 'requirements.txt'

env:
  PYTHON_VERSION: '3.11'
  DATA_DIR: 'data'
  LOG_DIR: 'logs'

jobs:
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      # 1️⃣ Checkout repository
      - name: Checkout repository
        uses: actions/checkout@v4
    
      # 2️⃣ Set up Python with caching
      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
    
      # 3️⃣ Install dependencies
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install requests
    
      # 4️⃣ Create necessary directories
      - name: Create data and log directories
        run: |
          mkdir -p ${{ env.DATA_DIR }} ${{ env.LOG_DIR }}
    
      # 5️⃣ Load previous state (if exists)
      - name: Load previous state
        id: cache-state
        uses: actions/cache@v4
        with:
          path: ${{ env.DATA_DIR }}
          key: spillway-state-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            spillway-state-${{ runner.os }}-
    
      # 6️⃣ Run the monitor script
      - name: Run spillway monitor
        id: monitor
        run: |
          python -m spillway_monitor.monitor
          echo "exit_code=$?" >> $GITHUB_OUTPUT
        env:
          PUSHOVER_TOKEN: ${{ secrets.PUSHOVER_TOKEN }}
          PUSHOVER_USER: ${{ secrets.PUSHOVER_USER }}
          PYTHONPATH: ${{ github.workspace }}
    
      # 7️⃣ Save current state for next run
      - name: Save monitoring state
        if: steps.monitor.outputs.exit_code == '0'
        uses: actions/cache@v4
        with:
          path: ${{ env.DATA_DIR }}
          key: spillway-state-${{ runner.os }}-${{ github.sha }}
    
      # 8️⃣ Upload logs as artifact (for debugging)
      - name: Upload logs artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: monitor-logs-${{ github.run_id }}-${{ github.run_attempt }}
          path: |
            ${{ env.LOG_DIR }}/
            ${{ env.DATA_DIR }}/
          retention-days: 7
          if-no-files-found: ignore
    
      # 9️⃣ Upload monitor script output
      - name: Upload monitor output
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: monitor-output-${{ github.run_id }}-${{ github.run_attempt }}
          path: |
            ${{ github.workspace }}/monitor_output.log
          retention-days: 7
          if-no-files-found: ignore
