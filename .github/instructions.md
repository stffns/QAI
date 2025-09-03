# agent.md – Backend Instructions (Python API for React Chat)

> Place this file at the repo root so Copilot (and contributors) align with our backend standards. This project is **Python (FastAPI + Pydantic v2)** serving a React chat frontend.

## 1) Purpose & Scope

* Align Copilot with our **Python backend** conventions.
* Ensure predictable behavior: **no hard‑coded secrets**, **no silent fallbacks**, and **errors must be explicit** (propagated with proper HTTP status and structured payloads).
* Provide build/test/run commands and guardrails for security, logging, and performance.

## 2) Project Snapshot

* **Runtime:** Python 3.11+
* **Framework:** FastAPI (async)
* **Models/Validation:** Pydantic v2 (+ pydantic‑settings)
* **Server:** Uvicorn
* **HTTP Client (tests):** `httpx`
* **Test Framework:** `pytest`, `pytest‑asyncio`, `pytest‑cov`
* **Lint/Format:** Ruff + Black + isort (use repo configs)
* **Structure (convention):**

```
repo/
├─ src/app/
│  ├─ main.py                # FastAPI app factory
│  ├─ api/                   # routers (v1/*)
│  ├─ schemas/               # Pydantic models (request/response)
│  ├─ services/              # domain services (pure logic)
│  ├─ repositories/          # DB/external adapters
│  ├─ core/
│  │   ├─ config.py          # settings via pydantic-settings
│  │   ├─ logging.py         # struct logging config
│  │   └─ errors.py          # exceptions & error model
│  └─ __init__.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ api/
│  └─ e2e/
├─ pyproject.toml
├─ README.md
└─ agent.md (this file)
```

## 3) How to Build, Run & Test (Copilot, follow exactly)

```bash
# 0) create & activate venv (example)
python -m venv .venv && source .venv/bin/activate

# 1) install deps
pip install -U pip wheel
pip install -e .[dev]

# 2) lint & format (check only)
ruff check src tests
black --check src tests
isort --check-only src tests

# 3) run tests with coverage
pytest -q --asyncio-mode=auto --maxfail=1 --disable-warnings \
  --cov=src/app --cov-report=term-missing

# 4) run locally
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

* If any command fails, **stop** and propose a minimal fix before continuing.
* Prefer **small diffs** that keep the app runnable.

## 4) WebSocket vs HTTP (and SSE) for Chat

* **HTTP (POST + long‑polling)**: simplest; good for request/response; no live tokens.
* **SSE (Server‑Sent Events)**: one‑way streaming from server → browser; ideal for token‑streaming chat **without bidirectional control**; simpler than WS; works well with React and proxies.
* **WebSocket**: full duplex (client ↔ server); choose when you need **bi‑directional** features (interrupt, tool calls, presence, typing events) or very low‑latency interactions.

**Guidance:**

* If the chat solo **streaming de texto** → **SSE**.
* Si habrá **acciones del cliente en tiempo real** (cancelar, editar, tool‑calls) → **WebSocket**.
* Implementa una sola capa de transporte y **no mezcles** SSE y WS para el mismo flujo.

## 5) Pydantic & Schemas (v2)

```python
# src/app/schemas/chat.py
from pydantic import BaseModel, Field

class ChatMessageIn(BaseModel):
    session_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)

class ChatMessageOut(BaseModel):
    session_id: str
    reply: str
    tokens_used: int
```

* **Never** accept raw dicts in endpoints; always validate with Pydantic models.
* Keep **request** and **response** schemas separados; no mezclar modelos de dominio con transporte.

## 6) App Factory & Routing

```python
# src/app/main.py
from fastapi import FastAPI
from app.core.config import Settings, get_settings
from app.api.v1 import router as v1_router

def create_app() -> FastAPI:
    app = FastAPI(title="Chat API")
    app.include_router(v1_router, prefix="/v1")
    return app
```

```python
# src/app/api/v1/__init__.py
from fastapi import APIRouter
from .chat import router as chat_router

router = APIRouter()
router.include_router(chat_router, prefix="/chat", tags=["chat"])
```

```python
# src/app/api/v1/chat.py
from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatMessageIn, ChatMessageOut

router = APIRouter()

@router.post("/message", response_model=ChatMessageOut, status_code=200)
async def send_message(body: ChatMessageIn) -> ChatMessageOut:
    # call service; *do not* swallow exceptions
    try:
        reply, tokens = await process_message(body.session_id, body.text)
        return ChatMessageOut(session_id=body.session_id, reply=reply, tokens_used=tokens)
    except KnownDomainError as exc:
        # Map domain errors to precise HTTP codes
        raise HTTPException(status_code=422, detail={"code": exc.code, "msg": str(exc)})
```

## 7) Errors: No silencios, no fallbacks

* **Prohibido**: capturar excepciones y devolver valores por defecto "silenciosos".
* **Obligatorio**: mapear errores a **HTTP 4xx/5xx** con un **payload estructurado**.
* Incluye un **modelo de error** común:

```python
# src/app/core/errors.py
from pydantic import BaseModel

class ErrorModel(BaseModel):
    code: str
    message: str
    details: dict | None = None
```

## 8) Settings & Secrets

* Usa **pydantic‑settings** con `.env` y variables de entorno, nunca hardcodees secretos.
* Los defaults deben ser **seguros**, no “mágicos”. Si falta algo crítico, **falla temprano** con un error claro.

```python
# src/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DB_URL: str | None = None
    class Config:
        env_file = ".env"

def get_settings() -> Settings:
    return Settings()  # will raise validation error if required vars missing
```

## 9) Logging (estructurado)

* Configura logging en arranque; usa niveles (INFO por defecto; DEBUG solo en dev).
* **No** loguees PII o secretos. Registra ids de sesión y latencias.

## 10) Streaming Options

* **SSE** ejemplo (FastAPI): usa `EventSourceResponse` (via `sse-starlette`) para token‑streaming; mantén eventos `data:` con JSON.
* **WebSocket** ejemplo (FastAPI): valida el handshake; autentica por token; controla `disconnect` y `backpressure`.

## 11) Testing Policy

* Todos los tests en `tests/` (no mezclar con `src/`).
* **Unit**: servicios puros; **Integration**: routers con app de test (`from fastapi.testclient import TestClient` o `httpx.AsyncClient`).
* **No mocks de más**: sólo en límites externos (DB, APIs).
* Cada bug corregido → **regresión test**.

```python
# tests/api/test_chat.py
import pytest
from httpx import AsyncClient
from app.main import create_app

@pytest.mark.asyncio
async def test_send_message_ok():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/v1/chat/message", json={"session_id":"s1","text":"hola"})
    assert res.status_code == 200
    payload = res.json()
    assert set(payload) >= {"session_id","reply","tokens_used"}
```

## 12) Dependencies Policy

* Antes de añadir una nueva librería, preferir stdlib o deps ya presentes.
* Documenta el motivo y el alcance en el PR.

## 13) Security & Privacy Guardrails

* **Nunca** imprimir ni persistir secretos.
* Sanitiza inputs; limita tamaño de payloads; timeouts en llamadas externas.
* Deshabilita CORS amplio en prod; define orígenes explícitos.

## 14) CI/CD Requirements

* Jobs mínimos: lint → typecheck → tests (coverage) → security scan.
* Bloquear merge si falla cualquier check.

## 15) Copilot: Cómo pedirle cosas

* “Genera un endpoint `POST /v1/chat/message` usando `ChatMessageIn/Out`, sin hardcodear secretos, con manejo de errores 4xx/5xx explícito.”
* “Crea tests en `tests/api/` para casos OK y de validación 422.”
* “Refactoriza `services/chat_service.py` para separar IO de lógica pura; no cambies las firmas públicas.”

## 16) Content Exclusions para Copilot

* Ignorar: `secrets/**`, `.env*`, `**/*.pem`, `**/*.key`, `dist/**`, `build/**`, `coverage/**`, `**/generated/**`, `vendor/**`.

## 17) PR Policy

* PR pequeño y runnable. Incluye: rationale, riesgos, cómo probar (pasos), y evidencia de tests.

## 18) Mantenimiento

* Actualiza este archivo cuando cambie el stack.
* Revisa trimestralmente dependencias y linters.
