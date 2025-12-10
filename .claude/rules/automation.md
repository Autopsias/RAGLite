# Automated Slash Command Usage

**CRITICAL:** Use these slash commands AUTOMATICALLY when their trigger conditions are met. Do NOT wait for explicit user requests.

---

## Development Workflow Automation

### When CI/CD Pipeline Fails
- **Trigger:** GitHub Actions failures, quality gate violations, CI errors mentioned
- **Action:** Automatically invoke `/ci_orchestrate` or suggest it prominently
- **Example:** "CI is failing" -> Use `/ci_orchestrate --fix-all`

### When Tests Fail
- **Trigger:** pytest failures, test errors, unit/integration/API test issues mentioned
- **Action:** Automatically invoke `/test_orchestrate` or suggest it prominently
- **Example:** "Fix the failing tests" -> Use `/test_orchestrate --run-first`

### When Creating Pull Requests
- **Trigger:** User mentions "create PR", "pull request", "ready to merge"
- **Action:** Automatically invoke `/pr create [story-id]` if applicable
- **Example:** "Create a PR for story 2.1" -> Use `/pr create story 2.1`

### When Making Commits
- **Trigger:** User says "commit these changes", "ready to commit", multiple files modified
- **Action:** Automatically invoke `/commit_orchestrate` with quality checks
- **Example:** "Commit the changes" -> Use `/commit_orchestrate --quality-first`

### When Session Needs Continuation
- **Trigger:** Long task completion, end of work session, context handoff needed
- **Action:** Automatically invoke `/nextsession` to generate continuation prompt
- **Example:** Near token limit or work pause -> Use `/nextsession`

### When Parallelizing Work
- **Trigger:** Multiple independent tasks, batch operations, parallel fixes needed
- **Action:** Automatically invoke `/parallelize` or `/parallelize_agents`
- **Example:** "Fix all linting issues" -> Use `/parallelize_agents --strategy=lint`

---

## Recognition Patterns

### CI Failure Indicators
- "CI failing", "GitHub Actions failing", "quality gates"
- "linting errors", "type errors", "security scan failed"
- "pipeline broken", "checks failing"

### Test Failure Indicators
- "tests failing", "pytest errors", "test suite broken"
- "API tests failing", "database tests failing"
- "coverage dropping", "test errors"

### PR Workflow Indicators
- "create PR", "pull request", "merge to main"
- "PR status", "ready to merge", "PR for story X"

### Commit Workflow Indicators
- "commit changes", "git commit", "ready to commit"
- "save changes", "checkpoint", "create commit"

### Parallelization Indicators
- "fix all", "batch fix", "multiple files"
- "parallel", "at once", "all errors"

---

## Command Selection Logic

### Decision Tree
1. Is there a CI/CD failure? -> `/ci_orchestrate`
2. Are there test failures (without CI context)? -> `/test_orchestrate`
3. Is user creating/managing PRs? -> `/pr [action]`
4. Is user ready to commit? -> `/commit_orchestrate`
5. Is work parallelizable? -> `/parallelize_agents`
6. Does session need continuation? -> `/nextsession`

### Priority Order (if multiple applicable)
1. CI failures (most critical - blocks merges)
2. Test failures (blocks development)
3. PR operations (workflow progression)
4. Commit operations (save work)
5. Parallelization (efficiency gains)

---

## Guardrails

### Do NOT auto-invoke commands when:
- User explicitly specifies a different approach
- User says "--no-chain" or "don't automate"
- Command was just used in last 3 messages (avoid loops)
- Uncertainty about user intent (ask first)
- User is exploring/debugging manually

### DO auto-invoke commands when:
- Failure patterns clearly match command purpose
- User intent is unambiguous
- Efficiency gain is significant (>5 minutes saved)
- User has used similar commands before in session
- Pattern matches 2+ indicators from recognition list

---

## Chain Invocation Intelligence

### Automatic Command Chaining
- `/ci_orchestrate` detects test failures -> auto-chain to `/test_orchestrate`
- `/test_orchestrate` succeeds with changes -> auto-chain to `/commit_orchestrate`
- `/commit_orchestrate` succeeds -> optionally suggest `/pr create`

### Chain Prevention
- Respect `--no-chain` flag in any command
- Stop after 3-level depth (prevent infinite loops)
- Stop if user interrupts or provides new direction
