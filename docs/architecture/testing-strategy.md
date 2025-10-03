# Testing Strategy

## Testing Pyramid

```
                  ┌───────────────┐
                  │  E2E Tests    │  ← 5% (Accuracy validation)
                  │  (Accuracy)   │
                  └───────────────┘
               ┌────────────────────┐
               │ Integration Tests  │  ← 15% (Service integration)
               │  (Microservices)   │
               └────────────────────┘
         ┌──────────────────────────────┐
         │      Unit Tests              │  ← 80% (Code coverage)
         │   (Functions, Classes)       │
         └──────────────────────────────┘
```

## Unit Tests (80%+ Coverage Target)

**Scope:**
- Individual functions and classes
- Mocked external dependencies (Qdrant, Neo4j, Claude API)
- Fast execution (<5 min for full suite)

**Example:**

```python