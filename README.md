# Patchbay

**Universal LLM Gateway & Orchestration Platform**

Hiçbir uygulamanın tek bir LLM sağlayıcısına bağımlı kalmaması gereken bir dünyada, o bağımsızlığı veren altyapı katmanı.

## Özellikler

- **10+ LLM Sağlayıcısı** — OpenAI, Anthropic, Google, xAI, DeepSeek, Qwen, Mistral, Meta, AWS Bedrock, Azure OpenAI, Vertex AI, OpenRouter, Groq, Together, Ollama/vLLM
- **Akıllı Yönlendirme** — Maliyet-tabanlı, gecikme-tabanlı, semantic ve öğrenen yönlendirme stratejileri
- **MCP Entegrasyonu** — Model Context Protocol ile araç/veri orkestrasyonu, cross-protokol şema çevirisi
- **Devre Kesici + Fallback** — Sağlayıcı hatalarında otomatik geçiş, circuit breaker deseni
- **Guardrails** — PII redaksiyonu, jailbreak tespiti, içerik politikası
- **Semantic Cache** — pgvector ile anlam bazlı önbellekleme
- **Bütçe Yönetimi** — Token-bucket rate limiting, hard budget enforcement
- **Gerçek Zamanlı Dashboard** — Tokyo Night temalı command center, canlı istek akışı görselleştirmesi

## Hızlı Başlangıç

```bash
git clone https://github.com/omerfaruk-aydn/patchbay.git
cd patchbay
docker compose up -d
```

Dashboard: http://localhost:3000
API: http://localhost:8000/docs

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12+ / FastAPI / SQLAlchemy async / Alembic |
| Veritabanı | PostgreSQL 16+ (pgvector) / Redis 7+ |
| Frontend | Next.js 15 / React 19 / TypeScript / Tailwind CSS v4 |
| Tasarım | Tokyo Night / shadcn/ui / Framer Motion / D3.js |
| Altyapı | Docker / OpenTelemetry / Grafana / Prometheus |
| CI/CD | GitHub Actions |

## Mimari

```
İstemci → API Gateway → Routing Engine → Provider Adapter → LLM Sağlayıcı
                         ↓
                    MCP Orchestration → Dış MCP Server'lar
                         ↓
                    Guardrails → Cache → Billing
```

## Lisans

MIT
