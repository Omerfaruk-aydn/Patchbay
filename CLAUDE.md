# CLAUDE.md — Patchbay Kod Kalite Kuralları

## Genel İlkeler
- Her yeni sağlayıcı adapter'ı ProviderAdapter arayüzünü EKSİKSİZ implement etmeli — kısmi implementasyon kabul edilmez.
- Routing/Provider/MCP/Guardrails katmanları birbirinin iç detayını BİLMEMELİ — sadece tanımlı arayüzler üzerinden konuşur.
- Hiçbir sağlayıcı kimlik bilgisi, log satırına veya hata mesajına yazılmamalı (otomatik secret-scanning pre-commit hook'u zorunlu).

## Python (Backend)
- Tip ipuçları zorunlu, `mypy --strict` CI'da kırmızı geçemez.
- Asenkron kod tabanında ASLA bloklayıcı (senkron) I/O kullanılmaz.
- Her yeni modül için ilgili `tests/unit/` dosyası AYNI PR'da gelir.
- Hata sınıfları `core/exceptions.py`'de merkezi tanımlanır, generic `Exception` fırlatılmaz.
- Conventional Commits formatı: `feat:`, `fix:`, `refactor:`, `docs:`.

## TypeScript (Frontend)
- `strict: true`, `any` kullanımı lint kuralıyla engellenir.
- Tüm API tipleri backend OpenAPI şemasından OTOMATİK üretilir, elle tip tanımlanmaz.
- Tasarım token'ları (tokyo-night-tokens.css) DIŞINDA hardcoded renk/spacing değeri kullanılmaz.

## Commit / PR Disiplini
- Conventional Commits formatı (`feat:`, `fix:`, `refactor:`, `docs:`).
- Her PR, ilgili faz/bölüm numarasına referans verir.
- Mimari etkisi olan her PR, `docs/architecture/`'a bir ADR ekler.
