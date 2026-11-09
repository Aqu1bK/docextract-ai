docextract-ai/
├── .github/
│   ├── workflows/
│   │   └── .gitkeep
│   ├── COMMIT_CONVENTION.md
│   ├── CONTRIBUTING.md
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   └── health.py
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py
│   │   │   ├── test_error_format.py
│   │   │   └── test_health.py
│   │   ├── .env
│   │   └── pyproject.toml
│   └── web/
│       └── .gitkeep
├── docker/
│   └── .gitkeep
├── docs/
│   ├── adr/
│   │   ├── ADR-001-public-demo-uses-mock-mode.md
│   │   ├── ADR-002-local-docker-uses-real-vision-llm.md
│   │   ├── ADR-003-use-pypdf-instead-of-pymupdf.md
│   │   └── ADR-004-postgres-queue-instead-of-redis.md
│   ├── architecture.md
│   ├── demo-mode-explanation.md
│   ├── local-docker-mode-explanation.md
│   ├── phase-plan.md
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   └── init_project.sh
├── .editorconfig
├── .env.example
├── .gitignore
├── LICENSE
├── Makefile
└── README.md