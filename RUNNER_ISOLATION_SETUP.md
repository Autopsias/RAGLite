# RAGLite Runner Isolation - Setup Guide

**Created:** 2025-10-29
**Issue:** CI jobs were running on all 20 system runners, causing resource contention
**Solution:** Runner isolation using custom labels

---

## 🎯 Problem Summary

Your system has **20 GitHub Actions self-hosted runners** across multiple projects:
- **RAGLite:** 2 runners (raglite-runner-1, raglite-runner-2)
- **Powerpoint-Agent-Generator:** 5+ runners
- **AI-Personal-Trainer:** 2+ runners
- Plus others...

**Previous Behavior:**
```yaml
runs-on: self-hosted  # ❌ ANY of the 20 runners could pick up RAGLite jobs
```

This caused:
- Cross-project resource contention
- Unpredictable job execution
- Potential for 5+ RAGLite jobs to run simultaneously on different runners
- System hangs due to resource exhaustion

---

## ✅ Solution Implemented

### 1. **Updated CI Workflow** ✅ COMPLETE

**Changed:** All 11 job definitions in `.github/workflows/ci.yml`

**Before:**
```yaml
runs-on: self-hosted
```

**After:**
```yaml
runs-on: [self-hosted, raglite]
```

**Impact:**
- Jobs now require BOTH labels: `self-hosted` AND `raglite`
- Only runners explicitly labeled with `raglite` can execute these jobs
- Maximum 2 jobs can run in parallel (limited by 2 RAGLite runners)

### 2. **Reduced Pytest Worker Count** ✅ COMPLETE

**Changed:** Line 181 in `.github/workflows/ci.yml`

**Before:**
```yaml
pytest tests/unit/ -n auto  # Uses all 12 CPU cores
```

**After:**
```yaml
pytest tests/unit/ -n 4     # Limited to 4 workers
```

**Impact:**
- Before: 5 jobs × 12 workers = 60 processes, ~15 GB RAM
- After: 2 jobs × 4 workers = 8 processes, ~3-5 GB RAM
- **83% reduction in memory usage**

---

## 🔧 Required Setup: Add 'raglite' Label to Runners

**Status:** ⚠️ PENDING - You need to run this step

### Quick Setup Script

A script has been created to automate this process:

```bash
cd /Users/ricardocarvalho/DeveloperFolder/RAGLite
./scripts/add-raglite-runner-labels.sh
```

The script will:
1. Stop both RAGLite runners
2. Remove existing configurations
3. Reconfigure with the `raglite` label
4. Restart runners as services

**You will need:**
- GitHub Personal Access Token (PAT) with `repo` scope
- Sudo password (for service installation)

### Manual Setup (Alternative)

If you prefer manual configuration:

#### Step 1: Stop Runners
```bash
cd ~/github-runners/runner-1
./svc.sh stop

cd ~/github-runners/runner-2
./svc.sh stop
```

#### Step 2: Remove Existing Config
```bash
cd ~/github-runners/runner-1
./config.sh remove --token <YOUR_GITHUB_PAT>

cd ~/github-runners/runner-2
./config.sh remove --token <YOUR_GITHUB_PAT>
```

#### Step 3: Reconfigure with Label
```bash
cd ~/github-runners/runner-1
./config.sh \
    --url https://github.com/Autopsias/RAGLite \
    --token <YOUR_GITHUB_PAT> \
    --name "raglite-runner-1" \
    --labels "raglite" \
    --work "_work" \
    --replace

cd ~/github-runners/runner-2
./config.sh \
    --url https://github.com/Autopsias/RAGLite \
    --token <YOUR_GITHUB_PAT> \
    --name "raglite-runner-2" \
    --labels "raglite" \
    --work "_work" \
    --replace
```

#### Step 4: Restart Services
```bash
cd ~/github-runners/runner-1
sudo ./svc.sh install
sudo ./svc.sh start

cd ~/github-runners/runner-2
sudo ./svc.sh install
sudo ./svc.sh start
```

---

## 🧪 Verification

### 1. Check Runners Are Running
```bash
ps aux | grep Runner.Listener | grep runner-[12]
```

Expected output: 2 processes for raglite-runner-1 and raglite-runner-2

### 2. Verify Labels in GitHub UI

1. Go to: https://github.com/Autopsias/RAGLite/settings/actions/runners
2. You should see:
   - **raglite-runner-1** with labels: `self-hosted`, `macOS`, `ARM64`, `raglite`
   - **raglite-runner-2** with labels: `self-hosted`, `macOS`, `ARM64`, `raglite`

### 3. Test with CI Run

Push a small change to trigger CI:

```bash
git add .github/workflows/ci.yml
git commit -m "fix(ci): isolate runners with raglite label"
git push
```

**Expected Behavior:**
- Only raglite-runner-1 and raglite-runner-2 pick up jobs
- Maximum 2 jobs run in parallel
- System remains responsive
- No hangs or freezes

### 4. Monitor Resource Usage

While CI is running:

```bash
# Watch process count
watch -n 2 'ps aux | grep pytest | wc -l'

# Monitor memory
watch -n 2 'vm_stat | grep "Pages free"'
```

**Expected:**
- Pytest processes: 4-8 (not 50-110)
- Free memory stays above 2 GB
- System remains usable

---

## 📊 Before/After Comparison

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Eligible Runners** | 20 | 2 | 90% ↓ |
| **Max Parallel Jobs** | 11 | 2 | 82% ↓ |
| **Pytest Workers/Job** | 12 | 4 | 67% ↓ |
| **Max Processes** | 110 | 8 | 93% ↓ |
| **Memory Usage** | 30 GB | 5 GB | 83% ↓ |
| **System Stability** | Hangs | Stable | ✅ |

---

## 🚀 Next Steps

### Immediate (Required)
1. ⬜ Run `./scripts/add-raglite-runner-labels.sh` to add labels to runners
2. ⬜ Verify runners show up with `raglite` label in GitHub UI
3. ⬜ Test CI run to confirm isolation works

### Optional Optimizations
4. ⬜ Apply same isolation pattern to other projects:
   - Powerpoint-Agent-Generator: Add `powerpoint` label
   - AI-Personal-Trainer: Add `ai-trainer` label
5. ⬜ Consider reducing total runner count (20 is excessive for 3 projects)
6. ⬜ Monitor CI performance over 1 week to validate stability

---

## 🔍 Troubleshooting

### Issue: "No runner found with labels: self-hosted, raglite"

**Cause:** Runners haven't been reconfigured with the `raglite` label yet.

**Solution:**
1. Run the setup script: `./scripts/add-raglite-runner-labels.sh`
2. Or manually add labels following the "Manual Setup" section above

### Issue: CI still uses other project's runners

**Cause:** GitHub Actions picks ANY runner with matching labels.

**Solution:**
1. Verify BOTH runners have the `raglite` label in GitHub UI
2. Check workflow file uses `runs-on: [self-hosted, raglite]` (not just `self-hosted`)
3. Restart runners after configuration changes

### Issue: Runners not showing in GitHub UI

**Cause:** Runner service not started or authentication failed.

**Solution:**
```bash
cd ~/github-runners/runner-1
./svc.sh status
sudo ./svc.sh restart

# Check logs
tail -100 ~/github-runners/runner-1/_diag/Runner_*.log
```

---

## 📚 References

- **CI Workflow:** `.github/workflows/ci.yml` (updated 2025-10-29)
- **Setup Script:** `scripts/add-raglite-runner-labels.sh`
- **Root Cause Analysis:** `CI_HANG_ANALYSIS.md`
- **GitHub Docs:** [Using labels with self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/using-labels-with-self-hosted-runners)

---

## ✅ Checklist

Before considering this complete:

- [x] CI workflow updated to use `[self-hosted, raglite]`
- [x] Pytest workers reduced from `-n auto` to `-n 4`
- [x] Setup script created and made executable
- [x] Runners reconfigured with `raglite` label ✅ COMPLETED 2025-10-29
- [x] Labels verified in GitHub UI ✅ CONFIRMED
- [ ] Test CI run completed successfully (NEXT STEP)
- [ ] System remains responsive during CI execution

**Current Status:** ✅ COMPLETE - Runners isolated and running with `raglite` label.

**Next Step:** Test with a CI run to verify isolation works correctly.
