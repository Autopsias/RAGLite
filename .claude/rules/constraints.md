# Critical Development Constraints

**PRIORITY: HIGHEST** - These rules override all other guidance.

---

## Anti-Over-Engineering Rules

### RULE 1: KISS (Keep It Simple, Stupid)
- This is a ~600-800 line MVP. If you find yourself adding design patterns, abstractions, or "future-proofing," STOP.
- NO custom base classes, factories, builders, or abstract layers unless explicitly specified in architecture docs
- NO "framework" or "engine" abstractions - write simple, direct functions
- ONE level of indirection maximum - if you need a helper function, call it directly

### RULE 2: Technology Stack is LOCKED
- ONLY use libraries listed in `docs/architecture/5-technology-stack-definitive.md`
- NEVER add SDKs, frameworks, or libraries not documented in the requirements
- NEVER use "improved" or "alternative" libraries (e.g., no LangChain, no LlamaIndex, no custom wrappers)
- If a library isn't in the tech stack table -> ASK FIRST, never assume

### RULE 3: No Customization Beyond Standard SDKs
- Use SDKs EXACTLY as documented in their official documentation
- NO custom wrappers around FastMCP, Qdrant client, or any SDK
- NO "simplified interfaces" or "convenience layers" unless approved
- If SDK documentation says `client.search()`, use `client.search()` - don't wrap it in `MyCustomSearch()`

### RULE 4: User Approval Required For
- Any dependency not in `docs/architecture/5-technology-stack-definitive.md`
- Any abstraction layer beyond simple utility functions
- Any "framework" or "pattern" not shown in `docs/architecture/6-complete-reference-implementation.md`
- Any deviation from the 15-file repository structure in section 3

### RULE 5: When In Doubt
- Check: Is this in the reference implementation? NO -> Don't add it
- Check: Is this library in the tech stack table? NO -> Ask user first
- Check: Am I adding this for "scalability" or "best practices"? YES -> Remove it
- Check: Would this work as a simple 20-line function? YES -> Do that instead

---

## Red Flags (STOP and Ask User)

Before proceeding, STOP if you're about to:
- Add a new Python package not in requirements
- Create a `BaseClass` or `AbstractInterface`
- Write a "config loader framework"
- Add dependency injection
- Create a plugin system
- Write middleware layers
- Use decorators beyond `@mcp.tool()` and `@pytest.fixture`
- Add caching layers (Redis, etc.) before Phase 4
- Create custom exception hierarchies beyond what's in reference implementation

---

## NOT Approved Libraries (Do Not Use)

- LangChain (use direct SDK calls instead)
- LlamaIndex (use Qdrant directly)
- Haystack (use Qdrant directly)
- Semantic Kernel (use direct SDK calls)
- Any ORM beyond Pydantic models
- Redis/Memcached (not needed until Phase 4)
- Celery/RQ (not needed for monolith)
- Custom abstraction libraries (write direct code)

**Exception:** LangGraph IS conditionally approved for Epic 2 Phase 3 (Agentic Coordination) - ONLY if Phase 2 achieves <85% accuracy.

---

## Development Discipline

- **Target is 600-800 lines TOTAL:** If module exceeds target, you're over-engineering
- **MVP means MINIMAL:** Every line of code must justify its existence
- **No "nice to have" features:** Only implement what's in the current story
- **No premature optimization:** Get it working first, optimize in Phase 4 if needed
- **Official docs ONLY:** Use SDK examples from official documentation, not blog posts
- **Ask before adding:** ANY new dependency requires explicit user approval
