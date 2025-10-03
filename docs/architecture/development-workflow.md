# Development Workflow

## Repository Structure

```
raglite/
├── README.md
├── docker-compose.yml              # Local dev environment
├── .env.example                    # Environment template
├── .gitignore
├── pyproject.toml                  # Python dependencies (Poetry)
├── poetry.lock
│
├── services/                       # Microservices
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── main.py                # MCP server entrypoint
│   │   ├── ingestion_pipeline.py
│   │   ├── chunking.py
│   │   ├── embedding.py
│   │   └── tests/
│   ├── retrieval/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── search.py
│   │   ├── reranking.py
│   │   └── tests/
│   ├── graphrag/                  # Phase 2
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── graph_builder.py
│   │   ├── agent_navigator.py
│   │   └── tests/
│   ├── forecasting/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── hybrid_forecaster.py
│   │   └── tests/
│   ├── insights/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── anomaly_detector.py
│   │   └── tests/
│   └── gateway/
│       ├── Dockerfile
│       ├── main.py
│       ├── router.py
│       └── tests/
│
├── orchestrator/                   # AWS Strands orchestration
│   ├── main.py
│   ├── agents/
│   │   ├── retrieval_agent.py
│   │   ├── analysis_agent.py
│   │   ├── graphrag_agent.py
│   │   ├── forecast_agent.py
│   │   └── synthesis_agent.py
│   └── tests/
│
├── shared/                         # Shared utilities
│   ├── __init__.py
│   ├── models.py                  # Pydantic data models
│   ├── config.py                  # Configuration management
│   ├── logging.py                 # Structured logging
│   └── monitoring.py              # Metrics helpers
│
├── tests/                          # Integration tests
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   ├── test_accuracy.py
│   │   └── fixtures/
│   └── load/
│       └── locustfile.py          # Load testing
│
├── terraform/                      # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── ecs/
│   │   ├── networking/
│   │   └── monitoring/
│   └── environments/
│       ├── dev/
│       └── prod/
│
├── scripts/
│   ├── setup-local-dev.sh         # Local setup automation
│   ├── build-and-push.sh          # Docker build + ECR push
│   ├── run-accuracy-tests.sh      # Ground truth validation
│   └── deploy-prod.sh             # Production deployment
│
└── docs/
    ├── architecture.md            # This document
    ├── prd.md                     # Product requirements
    ├── api.md                     # MCP API documentation
    └── runbooks/
        ├── incident-response.md
        └── troubleshooting.md
```

## Local Development Setup

```bash