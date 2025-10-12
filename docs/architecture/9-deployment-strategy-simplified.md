# 9. Deployment Strategy (Simplified)

## Phase 1-3: Local Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_data:/qdrant/storage

  raglite:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/data
      - ./.env:/app/.env
    environment:
      - QDRANT_HOST=qdrant
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    depends_on:
      - qdrant
```

**Setup:**
```bash
