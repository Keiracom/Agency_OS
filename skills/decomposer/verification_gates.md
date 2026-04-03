---

# Verification Gates — Reusable Patterns

| Gate Type | Command | Expected Output |
|-----------|---------|----------------|
| pytest | cd ~/clawd/Agency_OS && pytest | X passed, 0 failed |
| grep_absent | grep -r "PATTERN" src/ --include="*.py" | no output |
| grep_present | grep -r "PATTERN" src/ --include="*.py" | at least 1 match |
| file_exists | ls -la PATH | file present, size > 0 |
| import_clean | python3 -c "from src.MODULE import CLASS" | no error |
| supabase_write | SELECT * FROM TABLE WHERE KEY=VALUE | row exists |
| pr_created | gh pr list --state open --head BRANCH | PR listed |
| manual_updated | Check Google Drive Manual for section | section present |
| test_baseline | pytest count >= BASELINE and 0 failed | count verified |
| config_verify | cat FILE \| grep KEY | expected value present |
| service_alive | systemctl --user status SERVICE | active (running) |

---
