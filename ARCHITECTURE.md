|src/
├── .env                          # Ignored by git, contains real environment variables
├── .env.example                  # Template with empty keys for new environments
├── .gitignore                    # Excluded files and folders (pycache, node_modules, etc.)
├── docker-compose.yml            # Orchestrator for all services (DB, Redis, API, Bot, Frontend)
├── Dockerfile.backend            # Docker build script for Python/FastAPI/Aiogram (Moved to root)
├── Dockerfile.frontend           # Docker build script for Node.js/Nginx (Moved to root)
├── README.md                     # Deployment documentation
│
├── backend/                      # Python services (FastAPI + Aiogram)
│   ├── alembic/                  # Database migrations directory
│   ├── alembic.ini               # Alembic configuration
│   ├── pyproject.toml            # Poetry dependencies or requirements.txt
│   │
│   ├── app/                      # Main application module
│   │   ├── main_api.py           # Entry point for FastAPI (uvicorn)
│   │   ├── main_bot.py           # Entry point for Aiogram bot
│   │   │
│   │   ├── api/                  # FastAPI Endpoints
│   │   │   ├── routers/
│   │   │   │   ├── users.py
│   │   │   │   ├── strategies.py
│   │   │   │   └── webhooks.py   # SPECIFIC ENDPOINTS FOR PAYMENT WEBHOOKS (CryptoPay)
│   │   │   └── deps.py           # Dependencies (DB session injection, Telegram token validation)
│   │   │
│   │   ├── bot/                  # Telegram Bot Logic
│   │   │   ├── handlers/         # Message and command handlers (/start, /help)
│   │   │   ├── keyboards/        # Inline and Reply keyboards (e.g., "Launch App")
│   │   │   └── middlewares/      # Interceptors (Anti-spam, Auth checks)
│   │   │
│   │   ├── core/                 # System Core
│   │   │   ├── config.py         # Pydantic BaseSettings (reading from .env)
│   │   │   └── security.py       # Hashing, signature validation (Telegram InitData & Webhook signatures)
│   │   │
│   │   ├── db/                   # Database Layer
│   │   │   ├── database.py       # SQLAlchemy setup (Engine, SessionMaker)
│   │   │   └── models.py         # SQLAlchemy ORM models (UserModel, StrategyModel)
│   │   │
│   │   ├── schemas/              # Pydantic Schemas (Data validation)
│   │   │   ├── user.py
│   │   │   ├── strategy.py
│   │   │   └── payment.py        # SCHEMAS FOR VALIDATING INCOMING WEBHOOK PAYLOADS
│   │   │
│   │   └── services/             # Business Logic Layer
│   │       ├── crypto.py         # Outgoing requests to Crypto payment gateways
│   │       ├── payment_events.py # LOGIC FOR PROCESSING INCOMING WEBHOOKS (Updating balance/subs)
│   │       ├── referral.py       # MasterCoins logic, P2P transfers, discounts
│   │       └── strategy.py       # Complex queries for filtering strategies
│   │
│   └── tests/                    # Pytest Suite
│       ├── conftest.py           # Test fixtures (Test DB, Mocks)
│       ├── test_api/             # E2E tests for routers (including fake webhook simulation)
│       └── test_services/        # Unit tests for core logic
│
└── frontend/                     # Telegram Mini App (React / Vue / Vite)
    ├── package.json              # Node.js dependencies
    ├── vite.config.js            # Bundler configuration
    ├── public/                   # Static assets (Favicon, robots.txt)
    └── src/
        ├── assets/               # Images, fonts, global CSS/SCSS
        ├── components/           # Reusable UI elements (StrategyCard, GrenadeRow, PaymentModal)
        ├── pages/                # Main views (Home, StrategyDetail, AdminPanel)
        ├── api/                  # Axios clients mapped to FastAPI endpoints
        ├── store/                # Global state management (Zustand/Redux/Pinia)
        ├── App.jsx               # Root Component
        └── main.jsx              # React DOM render entry