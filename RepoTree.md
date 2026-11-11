docextract-ai/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # 4-job gate: secrets scan, ruff, mypy, pytest (+ auth env in Phase 4)
│   │   └── .gitkeep
│   ├── COMMIT_CONVENTION.md
│   ├── CONTRIBUTING.md
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   │   └── 0001_initial_schema.py
│   │   │   ├── env.py
│   │   │   └── script.py.mako
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── endpoints/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── auth.py          # NEW (Phase 4): GET /auth/me
│   │   │   │       │   └── health.py
│   │   │   │       ├── __init__.py
│   │   │   │       └── router.py           # mounts /auth router
│   │   │   ├── auth/                          # NEW (Phase 4): JWT validation + RBAC dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py          # get_current_user, require_roles, load_role_names
│   │   │   │   └── jwt_validator.py         # validate_supabase_jwt (HS256 + iss + exp)
│   │   │   ├── db/
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── core.py
│   │   │   │   │   ├── documents.py
│   │   │   │   │   ├── extraction.py
│   │   │   │   │   └── governance.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── seed.py
│   │   │   │   └── session.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── enums.py
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # + SUPABASE_URL, SUPABASE_JWT_SECRET, JWT_ISSUER, jwt_issuer
│   │   │   ├── errors.py
│   │   │   ├── logging_config.py
│   │   │   ├── main.py
│   │   │   └── middleware.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py              # + create_test_token, seed_test_user, supabase_jwt_secret
│   │   │   ├── test_auth.py             # NEW (Phase 4): 10 auth/RBAC tests
│   │   │   ├── test_error_format.py
│   │   │   ├── test_health.py
│   │   │   ├── test_schema.py
│   │   │   └── test_seed.py
│   │   ├── alembic.ini
│   │   └── pyproject.toml               # + PyJWT>=2.8
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
│   ├── phase-04-auth.md                # NEW (Phase 4): this learning pack
│   ├── phase-2.5-ci-gate.md
│   ├── phase-03-database.md
│   ├── phase-plan.md                   # Phase 04 → **Complete**
│   └── product-contract.md
├── scripts/
│   ├── init_project.ps1
│   └── init_project.sh
├── .editorconfig
├── .env.example                        # + JWT_ISSUER (+ Phase 3 Supabase keys)
├── .gitignore
├── LICENSE
├── Makefile
├── README.md
└── RepoTree.md
