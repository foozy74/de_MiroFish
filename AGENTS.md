# AGENTS.md - MiroFish Development Guide

## Build/Lint/Test Commands

### Root Level
```bash
npm run setup:all          # Install all dependencies (root + frontend + backend)
npm run dev                # Start both frontend + backend concurrently
npm run backend            # Start backend only (Flask on port 5001)
npm run frontend           # Start frontend only (Vite on port 3000)
npm run build              # Build frontend for production
```

### Backend (Python/Flask)
```bash
cd backend
uv sync                    # Install Python dependencies
uv run pytest              # Run all tests
uv run pytest tests/test_tenant.py  # Run specific test file
uv run pytest -k test_encrypt  # Run tests matching keyword
uv run python run.py       # Start Flask server
```

### Frontend (Vue 3 + Vite)
```bash
cd frontend
npm install                # Install dependencies
npm run dev                # Start dev server
npm run build              # Production build
npm run preview            # Preview production build
```

### Running a Single Test
```bash
# Run a specific test function
cd backend && uv run pytest tests/test_tenant.py::TestCrypto::test_encrypt_decrypt_roundtrip_with_master_key

# Run a specific test class
cd backend && uv run pytest tests/test_tenant.py::TestCrypto
```

## Code Style Guidelines

### Python (Backend)

**Imports:**
- Group imports: stdlib → third-party → local modules
- Use absolute imports from `app` package (e.g., `from app.utils.logger import get_logger`)
- Sort alphabetically within groups

**Naming Conventions:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants
- German comments/docstrings acceptable (existing codebase pattern)

**Type Hints:**
- Use type hints for function signatures: `def func(name: str) -> Optional[str]:`
- Import from `typing`: `Dict`, `List`, `Optional`, `Any`
- Use union types with `|`: `str | None`

**Error Handling:**
- Raise specific exceptions with descriptive messages
- Use `try/except` blocks for external API calls
- Log errors with `loguru` logger: `logger.error("message", exc_info=True)`

**Docstrings:**
- Use triple-quoted docstrings for modules, classes, and public functions
- Include Args/Returns sections for complex functions
- German or English acceptable (match surrounding code)

### JavaScript/Vue (Frontend)

**Imports:**
- Vue imports first: `import { ref, computed } from 'vue'`
- Then libraries: `import * as d3 from 'd3'`
- Then local modules: `import { getReport } from '../api/report'`
- Use `.js` extension only when necessary

**Naming Conventions:**
- `camelCase` for variables, functions
- `PascalCase` for Vue components
- `kebab-case` for file names (e.g., `Step1GraphBuild.vue`)
- Boolean variables: use `is`, `has`, `show` prefixes

**Vue 3 Composition API:**
- Use `<script setup>` syntax
- Import Vue APIs: `ref`, `computed`, `watch`, `onMounted`
- Use `const` for refs: `const count = ref(0)`
- Access refs with `.value` in script, direct in template

**Component Structure:**
```vue
<template>
  <!-- Template content -->
</template>

<script setup>
import { ref } from 'vue'
// Component logic
</script>

<style>
/* Scoped or global styles */
</style>
```

## Architecture Overview

**Backend Structure:**
```
backend/
├── app/
│   ├── api/          # REST API endpoints
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   ├── tenant/       # Multi-tenant module
│   ├── utils/        # Shared utilities
│   └── config.py     # Configuration
├── tests/
│   └── conftest.py   # Pytest fixtures/mocks
└── run.py            # Entry point
```

**Frontend Structure:**
```
frontend/src/
├── api/              # API client functions
├── components/       # Reusable Vue components
├── router/           # Vue Router config
├── store/            # State management
└── views/            # Page components
```

## Key Technologies

**Backend:** Flask, Pydantic, psycopg (PostgreSQL), PyJWT, cryptography, Flask-CORS
**Frontend:** Vue 3, Vue Router, D3.js, Axios, Vite
**Multi-Tenancy:** JWT validation via Clerk, PostgreSQL schemas, AES-256-GCM encryption

## Environment Variables

Required in `.env` (root directory):
```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
ZEP_API_KEY=your_zep_api_key
DATABASE_URL=postgresql://...
SECRET_KEY=your_secret_key
DERFISH_MASTER_KEY=base64_encoded_32_byte_key  # For API key encryption
CLERK_JWKS_URL=https://your-clerk-instance/.well-known/jwks.json
```

## Testing Patterns

**Backend Tests:**
- Use `unittest` framework (existing tests)
- Mock external dependencies in `conftest.py`
- Test setup/teardown with `setUp`/`tearDown` methods
- Use environment variables for test configuration

**Test File Structure:**
```python
class TestModule(unittest.TestCase):
    def setUp(self):
        # Reset state before each test
    
    def tearDown(self):
        # Clean up environment
    
    def test_feature(self):
        # Test implementation
```

## Git/Commit Conventions

- No specific commit message format enforced
- Keep commits atomic and descriptive
- Branch naming: feature/*, bugfix/*, hotfix/*
