<div align="center">

# ⚡ Patchbay

### Universal LLM Gateway & Orchestration Platform

**Hiçbir uygulamanın tek bir LLM sağlayıcısına bağımlı kalmaması gereken bir dünyada, o bağımsızlığı veren altyapı katmanı.**

---

[![CI](https://github.com/Omerfaruk-aydn/Patchbay/actions/workflows/ci.yml/badge.svg)](https://github.com/Omerfaruk-aydn/Patchbay/actions)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?style=flat&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[🚀 Hızlı Başlangıç](#-hızlı-başlangıç) • [📖 API Referansı](#-api-referansı) • [🏗️ Mimari](#️-mimari) • [🎯 Demo](#-demo) • [ Roadmap](#-roadmap)

</div>

---

## 📋 İçindekiler

- [Proje Nedir?](#-proje-nedir)
- [Neden Bu Proje?](#-neden-bu-proje)
- [Özellikler](#-özellikler)
- [Rekabet Analizi](#-rekabet-analizi)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Kurulum](#-kurulum)
- [Mimari](#️-mimari)
- [Veritabanı Şeması](#-veritabanı-şeması)
- [API Referansı](#-api-referansı)
- [Provider Desteği](#-provider-desteği)
- [Routing Stratejileri](#-routing-stratejileri)
- [MCP Entegrasyonu](#-mcp-entegrasyonu)
- [Guardrails & Güvenlik](#-guardrails--güvenlik)
- [Dashboard](#-dashboard)
- [Deployment](#-deployment)
- [Testler](#-testler)
- [Roadmap](#-roadmap)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

---

## 🤔 Proje Nedir?

**Patchbay**, tek bir birleşik API ile 10+ LLM sağlayıcısına (OpenAI, Anthropic, Google, DeepSeek, AWS Bedrock, Azure, Vertex AI, OpenRouter, Ollama, vb.) erişim sağlayan **production-grade** LLM gateway platformudur.

### Tek Cümleyle

> Hiçbir uygulamanın tek bir LLM sağlayıcısına bağımlı kalmaması gereken bir dünyada, o bağımsızlığı veren altyapı katmanı.

### Ne Yapar?

```
Uygulamanız                    Patchbay Gateway                    LLM Sağlayıcıları
─────────────                  ─────────────────                   ──────────────────
OpenAI SDK ──────┐
                 │
Anthropic SDK ───┤             ┌─────────────────┐                ┌──────────────┐
                 ├────────────▶│  Tek API:        │───────────────▶│ OpenAI       │
Gemini SDK ──────┤             │  /v1/chat/       │                ├──────────────┤
                 │             │  completions     │───────────────▶│ Anthropic    │
Kendi SDK'ın ────┘             │                  │                ├──────────────┤
                               │  • Akıllı Routing │───────────────▶│ Google       │
                               │  • Fallback       │                ├──────────────┤
                               │  • Cache          │───────────────▶│ DeepSeek     │
                               │  • Guardrails     │                ├──────────────┤
                               │  • Bütçe Kontrolü │───────────────▶│ Bedrock      │
                               └─────────────────┘                ├──────────────┤
                                                                  │ + 5 daha... │
                                                                  └──────────────┘
```

---

## 🎯 Neden Bu Proje?

### Problem

2026 LLM pazarı parçalanmış durumda:

| Sorun | Detay |
|---|---|
| **10+ sağlayıcı** | Her biri farklı API şeması, farklı auth, farklı rate limit |
| **3 hyperscaler** | AWS Bedrock, Azure, Vertex — aynı modelleri farklı SDK'larla sunuyor |
| **8+ rakip gateway** | Hiçbiri hepsini aynı anda iyi yapmıyor |
| **MCP henüz entegre değil** | Hiçbir gateway MCP'yi birinci sınıf vatandaş olarak ele almıyor |

### Çözümümüz

Patchbay, rakiplerin **hiçbirinin tek başına kapatmadığı boşluğu** hedefliyor:

| Eksen | OpenRouter | LiteLLM | Portkey | Bifrost | **Patchbay** |
|---|---|---|---|---|---|
| Model genişliği | ✅✅✅ | ✅✅✅ | ✅✅ | ✅ | ✅✅✅ |
| Self-host | ❌ | ✅✅✅ | ✅✅ | ✅✅✅ | ✅✅✅ |
| Gözlemlenebilirlik | ✅ | ✅ | ✅✅✅ | ✅ | ✅✅✅ |
| Performans | ✅✅ | ✅✅ | ✅✅ | ✅✅✅ | ✅✅ |
| **MCP native** | ❌ | ❌ | ✅ | ❌ | ✅✅✅ |
| **Awwards seviye UI** | ✅✅ | ✅ | ✅✅ | ✅ | ✅✅✅ |

---

## ✨ Özellikler

### 🔌 10+ LLM Sağlayıcısı

| Sağlayıcı | Modeller | Auth Tipi | Streaming |
|---|---|---|---|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-5.x | API Key | ✅ SSE |
| **Anthropic** | Claude Opus, Sonnet, Haiku | API Key | ✅ SSE |
| **Google** | Gemini 2.5 Pro, Flash | API Key | ✅ SSE |
| **xAI** | Grok serisi | API Key | ✅ SSE |
| **DeepSeek** | Coder, Reasoner | API Key | ✅ SSE |
| **AWS Bedrock** | Claude, Llama, Mistral | IAM SigV4 | ✅ |
| **Azure OpenAI** | GPT-4o, GPT-4o-mini | API Key/Entra ID | ✅ SSE |
| **Vertex AI** | Gemini, Claude, Llama | GCP Service Account | ✅ |
| **OpenRouter** | 200+ model | API Key | ✅ SSE |
| **Local** | Ollama, vLLM, LM Studio | URL | ✅ SSE |

### 🧠 Akıllı Routing

| Strateji | Açıklama | Kullanım Senaryosu |
|---|---|---|
| **Cost-Based** | En ucuz route'u seçer (fallback rate dahil) | Maliyet duyarlı iş yükleri |
| **Latency-Based** | En hızlı route'u seçer (p95 gecikme) | Gerçek zamanlı uygulamalar |
| **Semantic** | Görev kategorisine göre model seçer | Kod üretimi, yaratıcı yazım |
| **Learned** | Geçmiş veriden öğrenir (Phase 2) | Otomatik optimizasyon |

### 🔧 MCP Orkestrasyon

- **Tek tool tanımı, her modelde çalışır** — MCP tools/List'ten OpenAI/Anthropic/Gemini formatına otomatik çeviri
- **Tool call lifecycle** — pending → running → completed/failed durum makinesi
- **Cross-provider** — Blender MCP'yi GPT-4o veya Claude ile kullanabilirsin
- **Schema Translator** — 6 farklı provider formatına çeviri

### 🛡️ Guardrails

- **PII Redaksiyonu** — E-posta, telefon, kredi kartı, SSN tespiti ve otomatik maskeleme
- **Jailbreak Tespiti** — 8 farklı kalıp ile pattern matching
- **Content Policy** — İçerik politikası ihlali tespiti
- **Pipeline** — Ardışık kontrol, block/redact/flag kararları

### 💰 Bütçe Yönetimi

- **Hard Budget Enforcement** — Bütçe aşıldığında istek 402 ile reddedilir
- **Token-Bucket Rate Limiting** — Redis Lua script ile atomik kontrol
- **Çoklu Seviye Hiyerarşisi** — Organization → Project → Virtual Key
- **Alert Manager** — %80 ve %100 eşiklerinde otomatik uyarı

### 📊 Gözlemlenebilirlik

- **8 Prometheus Metriği** — RPS, latency, cost, cache hits, circuit breaker, fallback, guardrails
- **OpenTelemetry Tracing** — Gateway → Routing → Provider → MCP zincirindeki her adım
- **Structured Logging** — JSON formatında, centralized logging uyumlu
- **Grafana Dashboard** — Hazır dashboard JSON export'u

### 🎨 Dashboard

- **Tokyo Night Teması** — Glassmorphism, 8pt grid, glass efektleri
- **Canlı İstek Akışı** — D3.js ile animasyonlu grafik
- **Komut Paleti** — Cmd+K ile hızlı gezinme
- **7 Sayfa** — Overview, Providers, Routing, MCP, Playground, Logs, Settings

---

## 🛠️ Teknoloji Yığını

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Next.js 15 · React 19 · TypeScript · Tailwind CSS v4          │
│  Framer Motion · D3.js · Recharts · TanStack Query · Zustand   │
│  shadcn/ui · Tokyo Night Theme · kbar (Cmd+K)                  │
├─────────────────────────────────────────────────────────────────┤
│                        BACKEND                                   │
│  Python 3.12+ · FastAPI · SQLAlchemy (async) · Alembic         │
│  Pydantic v2 · Celery · httpx · bcrypt · python-jose           │
├─────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                │
│  PostgreSQL 16+ (pgvector) · Redis 7+ · S3/MinIO               │
├─────────────────────────────────────────────────────────────────┤
│                        ALTYAPI                                   │
│  Docker · Docker Compose · K8s · Terraform                      │
│  OpenTelemetry · Grafana Tempo · Prometheus · Loki              │
│  GitHub Actions CI/CD                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Hızlı Başlangıç

### 1. Repo'yu klonla

```bash
git clone https://github.com/Omerfaruk-aydn/Patchbay.git
cd Patchbay
```

### 2. `.env` dosyası oluştur

```bash
cp infra/.env.example infra/.env
# Edit .env with your settings
```

### 3. Docker Compose ile başlat

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 4. Seed data yükle

```bash
curl -X POST http://localhost:8000/v1/seed
```

### 5. Dashboard'u aç

```
http://localhost:3000
```

### 6. İlk isteği gönder

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Merhaba, Patchbay!"}]
  }'
```

---

## 📦 Kurulum

### Ön Gereksinimler

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+ (veya Docker)
- Redis 7+ (veya Docker)

### Backend (Apps/Gateway)

```bash
cd apps/gateway

# Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Bağımlılıkları kur
pip install -e ".[dev]"

# Veritabanı migration'larını çalıştır
alembic upgrade head

# Seed data yükle
python -c "import asyncio; from patchbay_gateway.db.seed import run_seed; from patchbay_gateway.core.database import async_session_factory; asyncio.run(run_seed(async_session_factory()))"

# Geliştirme sunucusunu başlat
uvicorn patchbay_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Apps/Dashboard)

```bash
cd apps/dashboard

# Bağımlılıkları kur
npm ci

# Geliştirme sunucusunu başlat
npm run dev
```

### API Dokümantasyonu

Sunucu başladıktan sonra:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🏗️ Mimari

### Yüksek Seviye Bileşen Diyagramı

```
                              ┌─────────────────────────────────┐
                              │      ADMIN DASHBOARD (Next.js)   │
                              │  Tokyo Night UI · Komut Paleti   │
                              │  Canlı İstek Akışı · Maliyet     │
                              └────────────────┬──────────────────┘
                                               │ REST + WebSocket
                                               ▼
┌──────────────┐    ┌─────────────────────────────────────────────┐    ┌──────────────┐
│  İSTEMCİ      │    │              API GATEWAY (FastAPI)            │    │  3. PARTİ    │
│  SDK'lar       │───▶│  Auth · Rate Limit · Routing · Validation   │◀───│  APP'LER     │
│ (Python/TS)   │    │  Unified API: /v1/chat/completions           │    │              │
└──────────────┘    └───────────────────────┬─────────────────────┘    └──────────────┘
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
          ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
          │  ROUTING ENGINE   │  │ MCP ORCHESTRATION │  │   GUARDRAILS     │
          │  Cost/Latency/    │  │ Server Registry   │  │   PII Redact     │
          │  Semantic Routing │  │ Schema Translator │  │   Jailbreak Det  │
          │  Circuit Breaker  │  │ Task Manager      │  │   Content Filter │
          │  Fallback Chain   │  └─────────┬─────────┘  └────────┬─────────┘
          └────────┬─────────┘            │                      │
                   │                      ▼                      │
                   │            ┌──────────────────┐             │
                   │            │  MCP SERVER'LAR   │             │
                   │            │  Blender·GitHub    │             │
                   │            │  Slack·Özel        │             │
                   │            └──────────────────┘             │
                   ▼                                              ▼
          ┌─────────────────────────────────────────────────────────────┐
          │              PROVIDER ADAPTER KATMANI                        │
          │  OpenAI·Anthropic·Google·xAI·DeepSeek·Qwen·Mistral·Meta    │
          │  Bedrock·Azure·Vertex·OpenRouter·Groq·Together·Local       │
          └────────────────────────────┬────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │  PostgreSQL    │  │    Redis      │  │  OBSERVABILITY│
          │  Modeller      │  │  Cache        │  │  OpenTelemetry│
          │  Anahtarlar    │  │  Rate Limit   │  │  Prometheus   │
          │  İstek Logları │  │  Oturum       │  │  Grafana      │
          └──────────────┘  └──────────────┘  └──────────────┘
```

### Sorumluluk Sınırları

| Bileşen | Tek Sorumluluğu | ASLA Yapmaması Gereken |
|---|---|---|
| **API Gateway** | Kimlik doğrulama, hız sınırlama | İş mantığı (routing kararı) |
| **Routing Engine** | Hangi route'un seçileceği | HTTP isteğini göndermek |
| **Provider Adapter** | İsteği sağlayıcıya çevirip göndermek | Routing/maliyet kararı vermek |
| **MCP Orchestration** | Tool şemasını çevirmek | LLM'e doğrudan istek göndermek |
| **Guardrails** | Politika kontrolü | Yönlendirme veya cache kararı vermek |

### Monorepo Yapısı

```
Patchbay/
├── apps/
│   ├── gateway/                      # FastAPI backend
│   │   ├── src/
│   │   │   ├── api/                  # REST/WS endpoint'leri
│   │   │   │   ├── v1/              # /v1/chat, /v1/models, /v1/keys
│   │   │   │   └── ws/              # WebSocket (live metrics)
│   │   │   ├── core/                # Config, security, database, redis
│   │   │   ├── routing/             # Engine, strategies, circuit breaker
│   │   │   ├── providers/           # 9 provider adapter
│   │   │   ├── mcp_orchestration/   # MCP registry, translator, tasks
│   │   │   ├── guardrails/          # PII, jailbreak, content filter
│   │   │   ├── caching/             # Exact + semantic cache
│   │   │   ├── billing/             # Budget, rate limiter, cost calc
│   │   │   ├── observability/       # Tracing, metrics
│   │   │   ├── db/                  # Models, migrations, seed
│   │   │   └── tasks/               # Celery background tasks
│   │   ├── tests/                   # Unit + integration tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── dashboard/                    # Next.js admin paneli
│       ├── app/                      # Sayfa bazlı routing
│       │   ├── (auth)/              # Login
│       │   └── (dashboard)/         # Ana panel sayfaları
│       ├── components/              # UI bileşenleri
│       ├── lib/                     # API client, WebSocket
│       ├── styles/                  # Tokyo Night tokens
│       └── Dockerfile
│
├── packages/
│   ├── sdk-python/                   # Python SDK
│   └── sdk-typescript/               # TypeScript SDK
│
├── infra/
│   ├── docker-compose.yml           # Development
│   ├── docker-compose.prod.yml      # Production
│   ├── k8s/                         # Kubernetes manifests
│   ├── terraform/                   # Cloud IaC
│   └── grafana-dashboard.json       # Grafana dashboard
│
├── docs/
│   ├── architecture/                # ADR'lar
│   ├── api-reference/               # OpenAPI spec
│   └── adding-a-provider.md         # Yeni sağlayıcı ekleme rehberi
│
├── CLAUDE.md                        # AI kod asistanı kuralları
├── README.md                        # Bu dosya
└── LICENSE
```

---

## 🗃️ Veritabanı Şeması

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  organizations   │────▶│    projects      │────▶│  virtual_keys   │
│  ─────────────   │     │  ─────────────   │     │  ─────────────   │
│  id (UUID)       │     │  id (UUID)       │     │  id (UUID)       │
│  name            │     │  organization_id │     │  project_id      │
│  slug (unique)   │     │  name            │     │  key_hash        │
│  settings (JSONB)│     │  slug            │     │  scopes[]        │
└─────────────────┘     └─────────────────┘     │  rate_limit_rpm  │
                                                 │  budget_usd_cents│
                                                 └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────┘
                    ▼
          ┌─────────────────┐     ┌─────────────────┐
          │     models       │────▶│ provider_routes  │
          │  ─────────────   │     │  ─────────────   │
          │  canonical_name  │     │  provider_key    │
          │  family          │     │  provider_model  │
          │  capabilities    │     │  pricing (input) │
          └─────────────────┘     │  pricing (output)│
                                  │  is_healthy       │
                                  └─────────────────┘

          ┌─────────────────┐     ┌─────────────────┐
          │    requests      │     │  routing_policies│
          │  ─────────────   │     │  ─────────────   │
          │  model_requested │     │  strategy        │
          │  status          │     │  config (JSONB)  │
          │  cost_usd_cents  │     │  is_default      │
          │  latency_ms      │     └─────────────────┘
          │  trace_id        │
          └────────┬────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│tool_calls│ │guardrail │ │ semantic_    │
│          │ │_violations│ │ cache_entries│
│ status   │ │ rule_type│ │ embedding    │
│ input    │ │ severity │ │ similarity   │
│ output   │ │ detail   │ │ hit_count    │
└──────────┘ └──────────┘ └──────────────┘
```

**13 tablo** — organizations, projects, virtual_keys, models, provider_routes, routing_policies, requests, mcp_servers, mcp_tools, tool_calls, guardrail_violations, audit_log, semantic_cache_entries

---

## 📖 API Referansı

### Unified API (OpenAI-Uyumlu)

| Endpoint | Yöntem | Açıklama |
|---|---|---|
| `/v1/chat/completions` | POST | OpenAI-uyumlu chat completions (streaming dahil) |
| `/v1/messages` | POST | Anthropic Messages API passthrough |
| `/v1/responses` | POST | OpenAI Responses API passthrough |
| `/v1/models` | GET | Katalogdaki tüm aktif modeller |
| `/v1/embeddings` | POST | Embedding endpoint |
| `/v1/keys` | POST/GET/DELETE | Virtual key yönetimi |
| `/v1/keys/{id}/toggle` | PATCH | Key aktif/pasif toggle |
| `/v1/usage` | GET | Kullanım ve maliyet sorgulama |
| `/v1/mcp/servers` | POST/GET/DELETE | MCP server yönetimi |
| `/v1/seed` | POST | İlk verileri yükle |
| `/health` | GET | Sağlık kontrolü |
| `WS /v1/live` | WS | Gerçek zamanlı metrik akışı |

### Örnek İstek

```bash
# Basic chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4-7",
    "messages": [
      {"role": "system", "content": "Sen yardımcı bir asistansın."},
      {"role": "user", "content": "Python ile hızlı sıralama nasıl yazılır?"}
    ],
    "max_tokens": 1024,
    "temperature": 0.7
  }'
```

### Örnek Yanıt

```json
{
  "id": "chatcmpl-a1b2c3d4e5f6",
  "object": "chat.completion",
  "created": 1718976000,
  "model": "claude-opus-4-7",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Python'da hızlı sıralama için `sorted()` fonksiyonunu veya `list.sort()` metodunu kullanabilirsin..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 256,
    "total_tokens": 301
  },
  "gateway_metadata": {
    "selected_route": {
      "provider": "anthropic",
      "model": "claude-opus-4-20250514",
      "region": null
    },
    "routing_strategy": "cost_optimized",
    "fallback_chain": ["route-uuid-1"],
    "cache_hit": false,
    "cost_usd_cents": 0.0234,
    "latency_ms": 842,
    "guardrail_checks": {
      "pii": "passed",
      "jailbreak": "passed",
      "content_policy": "passed"
    }
  }
}
```

### Streaming

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Merhaba!"}],
    "stream": true
  }'
```

```text
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"Mer"},"finish_reason":null}]}
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"haba"},"finish_reason":null}]}
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"!"},"finish_reason":null}]}
data: {"id":"chatcmpl-...","choices":[{"delta":{},"finish_reason":"stop"}],"gateway_metadata":{...}}
data: [DONE]
```

---

## 🔌 Provider Desteği

### Provider Adapter Pattern

Her sağlayıcı kendi dosyasında, `ProviderAdapter` arayüzünü implement eder:

```
providers/
├── base.py                 # Soyut arayüz (6 metod)
├── registry.py             # Auto-discovery registry
├── schemas.py              # Normalized request/response
├── openai_adapter.py       # OpenAI (retry, streaming, tools)
├── anthropic_adapter.py    # Anthropic (extended thinking, cache)
├── google_adapter.py       # Google Gemini (function calling)
├── deepseek_adapter.py     # DeepSeek (reasoning content)
├── openrouter_adapter.py   # OpenRouter (200+ model)
├── bedrock_adapter.py      # AWS Bedrock (IAM SigV4)
├── azure_openai_adapter.py # Azure OpenAI (API versioning)
├── vertex_adapter.py       # Vertex AI (GCP OAuth)
└── local_adapter.py        # Ollama/vLLM/LM Studio
```

### Yeni Sağlayıcı Ekleme (5 Adım)

```python
# 1. providers/yeni_adapter.py oluştur
from patchbay_gateway.providers.base import ProviderAdapter
from patchbay_gateway.providers.registry import ProviderRegistry

@ProviderRegistry.register
class YeniAdapter(ProviderAdapter):
    provider_key = "yeni_saglayici"

    async def send(self, route, request): ...
    async def stream(self, route, request): ...
    async def health_check(self, route): ...
    def normalize_request(self, req): ...
    def normalize_response(self, resp): ...
    def count_tokens(self, text, model): ...
```

```python
# 2. seed.py'ye model + route ekle
# 3. Test yaz (tests/unit/test_yeni_adapter.py)
# 4. docs/adding-a-provider.md'yi güncelle
# 5. Push et — mevcut hiçbir dosya değişmez!
```

---

## 🧠 Routing Stratejileri

### Cost-Based Routing

```python
# En ucuz route'u seçer (fallback rate dahil)
effective_cost = raw_cost × (1 + fallback_rate)
# ucuz ama güvenilmez route cezalandırılır
```

### Latency-Based Routing

```python
# Redis'te tutulan p95 gecikmeye göre seçim
# Gerçek zamanlı uygulamalar için ideal
```

### Semantic Routing

```
Gelen istek → Görev kategorisi tespiti → Tercih edilen model seçimi

Kategoriler:
  code_generation    → DeepSeek Coder, Claude Opus
  creative_writing   → Claude Opus, GPT-4o
  reasoning_math     → Claude Opus, DeepSeek Reasoner
  simple_tasks       → GPT-4o-mini, Claude Haiku
  translation        → GPT-4o, Claude Sonnet
```

### Circuit Breaker

```
CLOSED (normal) ──5 hata──▶ OPEN (devre dışı) ──30sn──▶ HALF_OPEN (test)
    ▲                                                                    │
    └──────────────────────1 başarılı────────────────────────────────────┘
```

---

## 🔧 MCP Entegrasyonu

### Akış

```
1. Kullanıcı: "Blender'da kırmızı bir küp oluştur"
2. Gateway: MCP tool listesini çeker → Schema Translator → Anthropic formatı
3. Claude: create_object + rotate_object tool'larını çağırır
4. Gateway: Tool calls'ı MCP server'a iletir
5. Blender MCP: Gerçek 3D nesneyi oluşturur
6. Gateway: Sonucu Claude'a geri besler
7. Claude: Nihai doğal dil yanıtını üretir
```

### Schema Translation

```
MCP Format (kaynak):
  {"name": "create_object", "inputSchema": {...}}

    ↓ OpenAI          ↓ Anthropic          ↓ Gemini
    ┌─────────────┐   ┌─────────────┐     ┌─────────────────┐
    │ type:       │   │ name:       │     │ functionDecl:   │
    │  "function" │   │  "create.." │     │  [{name, params}]│
    │ function: { │   │ input_schema│     └─────────────────┘
    │  name,      │   │  {...}      │
    │  params}    │   └─────────────┘
    └─────────────┘
```

---

## 🛡️ Guardrails & Güvenlik

### Guardrail Pipeline

```
Input → PII Redaction → Jailbreak Detection → Content Filter → Output
         (regex+NER)    (8 pattern)           (NLP classifier)
```

### PII Detection Patterns

| Tip | Regex Deseni | Örnek |
|---|---|---|
| E-posta | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | john@example.com |
| Telefon | `\d{3}[-.]?\d{3}[-.]?\d{4}` | 555-123-4567 |
| Kredi Kartı | `\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}` | 4111-1111-1111-1111 |
| SSN | `\d{3}-\d{2}-\d{4}` | 123-45-6789 |

### Jailbreak Patterns

```python
"ignore (all )?(previous|prior|early) instructions"
"you are now (DAN|in developer mode)"
"pretend (you are|to be) (evil|unrestricted)"
"bypass (all )?(safety|content|security) filters"
"act as if (you have|there are) no (rules|restrictions)"
"do anything now|DAN mode|jailbreak"
"from now on you (will|must) (not )?(refuse|decline)"
"(system|developer) prompt (override|injection)"
```

---

## 🎨 Dashboard

### Sayfalar

| Sayfa | İçerik |
|---|---|
| **Overview** | Canlı istek akışı görselleştirmesi, toplam maliyet, cache hit oranı |
| **Providers** | Bağlı sağlayıcılar, sağlık durumu, model listesi |
| **Routing** | Routing politikaları editörü, strateji seçimi |
| **MCP Servers** | MCP server bağlantı yönetimi, tool listesi |
| **Playground** | Canlı model test alanı, mesaj gönderme |
| **Logs** | İstek log gezgini, filtreleme |
| **Settings** | Proje ayarları, API anahtarları |

### Tasarım Sistemi (Tokyo Night)

```css
:root {
  --bg-base:        #1a1b26;  /* Zemin */
  --bg-elevated-1:  #1f2335;  /* Kartlar */
  --bg-elevated-2:  #24283b;  /* Modal */
  --text-primary:   #c0caf5;  /* Ana metin */
  --text-secondary: #9aa5ce;  /* İkincil metin */
  --accent-blue:    #7aa2f7;  /* Birincil eylem */
  --accent-green:   #9ece6a;  /* Başarı */
  --accent-red:     #f7768e;  /* Hata */
  --accent-magenta: #bb9af7;  /* MCP/Araç */
  --accent-teal:    #73daca;  /* Cache hit */
}
```

---

## 🚢 Deployment

### Docker Compose (Tek Komut)

```bash
docker compose -f infra/docker-compose.yml up -d
```

**Servisler:**
- `postgres` — PostgreSQL 16 + pgvector
- `redis` — Redis 7
- `gateway` — FastAPI backend (port 8000)
- `dashboard` — Next.js frontend (port 3000)
- `otel-collector` — OpenTelemetry collector
- `prometheus` — Metrik depolama
- `grafana` — Dashboard görselleştirme
- `tempo` — Trace depolama

### Kubernetes

```bash
kubectl apply -f infra/k8s/gateway.yaml
kubectl apply -f infra/k8s/dashboard.yaml
```

### Production

```bash
docker compose -f infra/docker-compose.prod.yml up -d
```

---

## 🧪 Testler

### Test Piramidi

| Seviye | Kapsam | Araç |
|---|---|---|
| **Unit** | Routing, adapters, guardrails, billing, MCP translator | pytest |
| **Integration** | API endpoint'leri, DB interactions | pytest + testcontainers |
| **Contract** | Sağlayıcı API şeması doğrulama | pytest + VCR.py |
| **E2E** | Uçtan uca akışlar | pytest + gerçek API anahtarları |
| **Frontend** | Bileşen testleri, kritik akışlar | Vitest + Playwright |
| **Yük** | p95 gecikme bütçesi doğrulama | k6 / Locust |

### Çalıştırma

```bash
cd apps/gateway

# Tüm unit testler
pytest tests/unit/ -v

# Coverage ile
pytest tests/unit/ --cov=src --cov-report=html

# Specific test
pytest tests/unit/test_routing_engine.py -v
```

---

## 🗺️ Roadmap

### Faz 0 — Temel İskelet ✅
- [x] Monorepo yapısı
- [x] FastAPI + Next.js iskeletleri
- [x] PostgreSQL şeması (13 tablo)
- [x] Docker Compose

### Faz 1 — Çekirdek Routing ✅
- [x] Provider Adapter arayüzü
- [x] OpenAI, Anthropic, Google adapter'ları
- [x] Cost-Based ve Latency-Based routing
- [x] Circuit Breaker + Fallback
- [x] `/v1/chat/completions` (streaming dahil)

### Faz 2 — MCP Entegrasyonu ✅
- [x] MCP Server Registry
- [x] Client Connection Pool
- [x] Schema Translator (MCP ↔ 6 provider)
- [x] Task Manager (lifecycle)

### Faz 3 — Genişletilmiş Sağlayıcılar ✅
- [x] AWS Bedrock, Azure, Vertex AI
- [x] DeepSeek, OpenRouter, Local (Ollama/vLLM)
- [x] Semantic Routing

### Faz 4 — Guardrails & Cache ✅
- [x] PII redaksiyonu
- [x] Jailbreak tespiti
- [x] Exact + Semantic cache
- [x] Bütçe + Rate limiting

### Faz 5 — Dashboard ✅
- [x] Tokyo Night teması
- [x] Canlı istek akışı (D3.js)
- [x] Komut paleti (Cmd+K)
- [x] Tüm dashboard sayfaları

### Faz 6 — Gözlemlenebilirlik ✅
- [x] OpenTelemetry + Prometheus
- [x] Grafana dashboard
- [x] CI/CD pipeline

### Gelecek

- [ ] Learned Routing (multi-armed bandit)
- [ ] A2A (Agent-to-Agent) entegrasyonu
- [ ] ACP (Agent Communication Protocol)
- [ ] WebSocket streaming (dashboard)
- [ ] Mobil uygulama
- [ ] SaaS modu (multi-tenant billing)

---

## 🤝 Katkıda Bulunma

1. Fork repo
2. Branch oluştur (`git checkout -b feature/yeni-ozellik`)
3. Değişiklikleri commit et (`git commit -m 'feat: yeni özellik'`)
4. Push et (`git push origin feature/yeni-ozellik`)
5. PR aç

### Kod Kuralları

- `mypy --strict` CI'da kırmızı geçemez
- `ruff check` temiz olmalı
- Her modül için test zorunlu
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`
- Hiçbir API key/log'a yazılmamalı

---

## 📜 Lisans

MIT License — detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

<div aligncenter">

**Patchbay** — *Hiçbir uygulamanın tek bir LLM sağlayıcısına bağımlı kalmaması gereken bir dünyada, o bağımsızlığı veren altyapı katmanı.*

[⬆️ Sayfanın başına dön](#-patchbay)

</div>
