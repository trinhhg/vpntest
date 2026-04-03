name: Update VPN Subs Automatically

on:
  schedule:
    - cron: '*/30 * * * *' # Chạy mỗi 30 phút
  workflow_dispatch:      # Bấm chạy bằng tay

jobs:
  update-subs:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout Repo
        uses: actions/checkout@v4 # Up lên v4 hết báo lỗi

      - name: Set up Python
        uses: actions/setup-python@v5 # Up lên v5 hết báo lỗi
        with:
          python-version: '3.10'

      - name: Install Requests
        run: pip install requests

      - name: Run Script Rename Nodes
        run: python update_sub.py

      - name: Commit and Push
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add subs/
          git commit -m "Auto-update VPN subs" || echo "No changes to commit"
          git push
