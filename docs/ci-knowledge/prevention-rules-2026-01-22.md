# CI Prevention Rules - Updated 2026-01-22

**Strategic Analysis Date:** 2026-01-22
**Root Causes Addressed:** Worker Memory Exhaustion, xdist Parallelism, Mock Coverage

---

## Rule 1: Resource-Based Sharding

Different test suites have different memory profiles. Allocate VM and worker count based on resource requirements, not uniformly.

### Implementation
- Retrieval shard: 8GB VM, 2 workers (embedding model: 2GB per worker)
- MCP shard: 4GB VM, 4 workers (no embedding model)
- Parallel ingestion: Moved to retrieval shard (not MCP)

### Validation
```bash
grep "retrieval.*shard" .github/workflows/ci.yml | grep workers
# Expected: workers: 2

grep "mcp.*shard" .github/workflows/ci.yml | grep workers
# Expected: workers: 4
```

---

## Rule 2: Embedding Model Test Isolation

Embedding model (Fin-E5, 2GB) is a singleton. Multiple parallel loads cause memory explosion.

### Implementation
- ALL embedding tests marked: `@pytest.mark.xdist_group(name="embedding_model")`
- xdist_group enforces sequential execution within group
- Prevents duplicate embedding loads

### Validation
```bash
python scripts/validate-xdist-markers.py
# Expected: ✅ Validation passed - 0 gaps
```

---

## Rule 3: Integration Test Timeouts

Different test categories need different timeouts.

### Implementation
- Unit tests: 10 seconds (should complete <3s)
- Integration (fast): 30 seconds (should complete <10s)
- Integration (embedding): 45 minutes (30-40 min execution + 5 min buffer)

### Validation
```bash
grep "timeout-minutes" .github/workflows/ci.yml | grep integration
# Expected: timeout-minutes: 45
```

---

## Rule 4: Mock Coverage 100%

Incomplete mock coverage causes hidden external API calls and timeouts.

### Implementation
- Mock BOTH primary AND fallback functions
- Patch at usage location (not definition)
- Validate: `python scripts/validate-mock-coverage.py`

### Validation
```bash
python scripts/validate-mock-coverage.py
# Expected: ✅ Mock coverage PASSED - 0 gaps
```

---

## Rule 5: Docker Daemon Health Checks

Docker daemon can enter zombie state. Verify responsiveness, not just socket existence.

### Implementation
- Check: `timeout 5 docker info`
- If unresponsive: Force cleanup (not retry)
- Run: `./scripts/ensure-colima-health.sh` before tests

### Validation
```bash
./scripts/ensure-colima-health.sh
# Expected: ✅ Docker daemon responsive
```

---

## Pre-Commit Checklist

- [ ] `python scripts/validate-xdist-markers.py` passes
- [ ] `python scripts/validate-mock-coverage.py` passes
- [ ] No embedding tests in MCP shard
- [ ] Integration tests have 45-minute timeout
- [ ] No new OOM or SIGKILL errors in logs
- [ ] Memory usage <4GB peak

---

## Related Docs

- `docs/ci-knowledge/worker-memory-exhaustion-2026-01-22.md` - Full analysis
- `docs/ci-strategy.md` - Resource allocation strategy
- `docs/ci-failure-runbook.md` - Section 26 (Worker Memory Exhaustion)
