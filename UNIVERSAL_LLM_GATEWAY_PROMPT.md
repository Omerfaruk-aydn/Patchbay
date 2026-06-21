# UNIVERSAL LLM GATEWAY & ORCHESTRATION PLATFORM
## Tam Kapsamlı Mühendislik Spesifikasyonu ve Yapay Zeka Kod Üretim Prompt'u

> **Doküman amacı:** Bu doküman, bir AI kod üretim aracına (Claude Code, Cursor, Codex CLI, Windsurf vb.) doğrudan yapıştırılıp sıfırdan production-grade bir sistem inşa ettirmek için tasarlanmış bir **mühendislik spesifikasyon promptudur**. Yarışmaya/portfolyoya çıkacak bir ürün için yazılmıştır; bu yüzden hedef sadece "çalışan kod" değil, **jüri karşısında savunulabilir, mimari olarak savunulabilir, görsel olarak ödül alabilir bir sistem**dir.
>
> **Son güncelleme bağlamı:** Haziran 2026 LLM pazarı, sağlayıcı kataloğu ve router/gateway rekabet analizi baz alınarak hazırlanmıştır. Proje adı kasıtlı olarak boş bırakılmıştır — `[PROJE_ADI]` placeholder'ını kendi marka ismin ile değiştir (dokümanın sonunda öneriler var).

---

## İÇİNDEKİLER

- **Bölüm 0** — AI Ajanına Rol Ataması
- **Bölüm 1** — Proje Vizyonu ve Konumlandırma
- **Bölüm 2** — Pazar Araştırması: Güncel LLM Sağlayıcı Haritası
- **Bölüm 3** — Pazar Araştırması: LLM Router/Gateway Rekabet Analizi
- **Bölüm 4** — Protokol Katmanı: MCP, A2A, ACP Konumlandırması
- **Bölüm 5** — Ürün Vizyonu ve Farklılaşma Stratejisi (Awwards + Yarışma Kriterleri)
- **Bölüm 6** — Sistem Mimarisi
- **Bölüm 7** — Teknoloji Yığını (Tech Stack)
- **Bölüm 8** — Monorepo / Klasör Yapısı
- **Bölüm 9** — Veritabanı Şeması
- **Bölüm 10** — Çekirdek Routing Engine Tasarımı
- **Bölüm 11** — Provider Adapter Pattern
- **Bölüm 12** — Unified API Tasarımı
- **Bölüm 13** — MCP Entegrasyon Katmanı
- **Bölüm 14** — Authentication & Key Management
- **Bölüm 15** — Observability & Cost Tracking
- **Bölüm 16** — Caching Katmanı
- **Bölüm 17** — Rate Limiting & Bütçe Yönetimi
- **Bölüm 18** — Guardrails & Güvenlik
- **Bölüm 19** — Admin Dashboard / Frontend Tasarım Sistemi (Tokyo Night)
- **Bölüm 20** — Deployment Mimarisi
- **Bölüm 21** — Test Stratejisi
- **Bölüm 22** — Dokümantasyon Gereksinimleri
- **Bölüm 23** — Faz Bazlı Yol Haritası
- **Bölüm 24** — Ödül / Yarışma Kriterleri Kontrol Listesi
- **Bölüm 25** — Kod Kalite Standartları (CLAUDE.md İçeriği)
- **Bölüm 26** — Son Talimat ve Proje İsmi Önerileri

---

## 0. AI AJANINA ROL ATAMASI (Bu bloğu olduğu gibi kopyala)

```
Sen, dünya çapında bir yazılım yarışmasında jüri karşısına çıkacak, Awwards
seviyesinde görsel kaliteye sahip, production-grade bir "Universal LLM
Gateway & Orchestration Platform" inşa eden kıdemli bir mühendislik
ekibisin. Rolün: Principal Backend Architect + Staff Frontend Engineer +
DevOps/SRE Lead + Product Designer rollerinin birleşimi.

Bu doküman senin TEK kaynağın. Aşağıdaki her bölüm bağlayıcıdır:
mimari kararları sorgulamadan uygula, ancak teknik olarak imkansız veya
çelişkili bir nokta görürsen bunu açıkça belirt ve alternatif öner.

Çıktı kalitesi standardı: Bu kod bir hackathon demo'su değil. Her modül
test edilebilir, her API endpoint dokümante, her UI ekranı erişilebilir
(WCAG 2.1 AA) ve her mimari karar bir ADR (Architecture Decision Record)
ile gerekçelendirilmiş olmalı.

Çalışma şeklin: Bu dokümanı baştan sona oku, sonra "13. Faz Bazlı Yol
Haritası" bölümündeki sıraya göre inşa et. Her fazın sonunda çalışan,
test edilmiş bir checkpoint bırak. Asla bir fazı yarım bırakıp diğerine
geçme.
```

---

## 1. PROJE VİZYONU VE KONUMLANDIRMA

### 1.1 Tek Cümlelik Vizyon

**[PROJE_ADI]**, herhangi bir LLM sağlayıcısına (OpenAI, Anthropic, Google, AWS Bedrock, Azure OpenAI, OpenRouter, açık kaynak modeller, yerel modeller) **tek bir birleşik API** üzerinden, **akıllı maliyet/performans yönlendirmesi**, **gerçek zamanlı gözlemlenebilirlik** ve **yerel MCP (Model Context Protocol) orkestrasyon** ile erişim sağlayan, kendi kendine barındırılabilir (self-hostable) ve bulutta yönetilebilir (managed) bir AI altyapı katmanıdır.

Tek cümleyle: **"Hiçbir uygulamanın tek bir LLM sağlayıcısına bağımlı kalmaması gereken bir dünyada, o bağımsızlığı veren altyapı katmanı."**

### 1.2 Bu Proje Neden Var? (Problem Tanımı)

2026 itibarıyla LLM pazarı parçalanmış durumda:

- **10+ büyük sağlayıcı markası** (OpenAI, Anthropic, Google, xAI, Meta, Mistral, DeepSeek, Alibaba/Qwen, Cohere, Moonshot/Kimi), her biri farklı API şeması, farklı kimlik doğrulama, farklı rate limit politikası ile.
- **3 büyük bulut hyperscaler'ı** (AWS Bedrock, Azure OpenAI/AI Foundry, Google Vertex AI) aynı modelleri farklı SDK'lar ve farklı fiyatlandırma katmanlarıyla sunuyor.
- **8+ ciddi router/gateway rakibi** (OpenRouter, LiteLLM, Portkey, Cloudflare AI Gateway, Vercel AI Gateway, TrueFoundry, Helicone, Bifrost) farklı felsefelerle aynı problemi çözmeye çalışıyor — hiçbiri hepsini aynı anda iyi yapmıyor.
- **Yeni nesil protokoller** (MCP, A2A, ACP) araç/ajan entegrasyonunu standartlaştırıyor ama hiçbir gateway bunları **birinci sınıf vatandaş** olarak ele almıyor; çoğu MCP'yi sonradan eklenmiş bir özellik gibi davranıyor.

Bu proje, mevcut rakiplerin **hiçbirinin tek başına kapatmadığı boşluğu** hedefliyor: aynı anda (a) OpenRouter'ın model genişliği, (b) LiteLLM'in self-host kontrolü, (c) Portkey'nin enterprise gözlemlenebilirliği/guardrail'leri, (d) Bifrost'un düşük gecikmeli mimarisi VE (e) MCP/A2A'nın native, ikinci sınıf değil birinci sınıf desteğini tek bir üründe birleştirmek.

### 1.3 Neden "Dünya Birincisi" Olabilir? (Farklılaştırıcı Tez)

Yarışma jürileri ve Awwards değerlendirmesi şu üç ekseni arar: **teknik derinlik**, **görsel/UX zanaatkarlığı**, ve **gerçek dünya faydası**. Bu proje üçünü de şu şekilde karşılar:

1. **Teknik derinlik:** Naif bir "proxy" değil; öğrenen (adaptive) yönlendirme motoru, semantic cache, devre kesici (circuit breaker) desenleri, çok kiracılı (multi-tenant) bütçe yönetimi, MCP tool-translation katmanı.
2. **Görsel zanaatkarlık:** Tokyo Night temalı, gerçek zamanlı veri akışı olan, glassmorphism + mikro-etkileşimlerle donatılmış bir command-center dashboard — "demo görünümlü admin paneli" değil, "bu bir ürün" hissi veren bir arayüz.
3. **Gerçek dünya faydası:** Bu, senin kendi tüm diğer projelerinin (otomasyon ajanları, video pipeline'ları, oyun geliştirme asistanları) arkasındaki **ortak altyapı** olabilir — yani demo değil, gerçekten kullanılan bir sistem.

### 1.4 Bu Doküman Neyi KAPSAMAZ

Netlik için: Bu proje bir "yeni LLM eğitmek" projesi değil. Bir "AI agent framework'ü" (LangChain/CrewAI benzeri) de değil — onların ÜZERİNDE çalışacak altyapı katmanı. Kapsam sınırı net tutulmalı, yoksa proje asla bitmez.

---
## 2. PAZAR ARAŞTIRMASI — GÜNCEL LLM SAĞLAYICI HARİTASI (Haziran 2026)

> Bu bölüm, sistemin "kaç tane ve hangi sağlayıcıyı destekleyeceğinin" referans kataloğudur. AI ajanı, Provider Adapter katmanını (Bölüm 11) bu listeye göre inşa etmelidir. Liste canlıdır — kod, yeni sağlayıcı eklemeyi bir config dosyası değişikliği kadar kolay yapacak şekilde tasarlanmalıdır (bkz. Bölüm 11.4 Plugin Mimarisi).

### 2.1 Birinci Sınıf (Frontier) Kapalı Kaynak Sağlayıcılar

| Marka | API Tipi | Kimlik Doğrulama | Özel Notlar |
|---|---|---|---|
| **OpenAI** | REST + SSE streaming | Bearer API key | Responses API + Chat Completions API ikisi de destekli olmalı; GPT-5.x serisi 1M+ context, native tool/computer-use desteği var. |
| **Anthropic** | REST + SSE streaming | `x-api-key` header | Messages API; prompt caching, extended thinking, MCP connector desteği native. Claude Opus/Sonnet/Haiku üçlü katman. |
| **Google (Gemini)** | REST + gRPC | API key veya OAuth | Gemini API (AI Studio) ve Vertex AI olarak iki ayrı giriş noktası var — ikisi de adapter'da ayrı ele alınmalı, kimlik doğrulama şeması farklı. |
| **xAI (Grok)** | OpenAI-uyumlu REST | Bearer API key | Grok serisi; büyük context pencereleri (1M-2M token aralığına yaklaşıyor), gerçek zamanlı arama entegrasyonu güçlü. |

### 2.2 Açık Ağırlık (Open-Weight) ve Çin Menşeli Laboratuvarlar

| Marka | Dağıtım Şekli | Özel Notlar |
|---|---|---|
| **DeepSeek** | Kendi API'si + açık ağırlık (Hugging Face) | Çok düşük token maliyeti (rakiplerine göre kayda değer ucuz), agentic coding benchmark'larında frontier modellere yakın performans. MIT lisanslı sürümler var. |
| **Alibaba (Qwen)** | Kendi API'si + açık ağırlık | Güçlü agentic coding ve uzun-bağlam performansı; "extended thinking" modu native. |
| **Moonshot AI (Kimi)** | Açık ağırlık + barındırılan API | Açık ağırlıklı modeller arasında en güçlü "Intelligence Index" skorlarından birine sahip. |
| **Z.ai (GLM serisi)** | Açık ağırlık + API | Maliyet/performans dengesinde güçlü, agentic coding'de tercih ediliyor. |
| **Meta (Llama)** | Açık ağırlık | Llama 4 ailesi (Scout/Maverick); çok uzun context (10M token'a kadar uzanan varyantlar) — büyük doküman/kod tabanı işleri için. |
| **Mistral AI** | Kendi API'si + açık ağırlık | Avrupa merkezli, Apache 2.0 lisanslı modeller; sliding-window attention ile verimli uzun context. |

### 2.3 Bulut Hyperscaler'ları (Çoklu Model Barındıran)

Bu üçü "tek bir sağlayıcı" değil, **çoklu sağlayıcı barındıran platformlar** — adapter mimarisinde özel olarak ele alınmalı çünkü hem kendi kimlik doğrulamaları hem de "hangi modeli barındırdıkları" zamanla değişiyor.

- **AWS Bedrock**: Anthropic, Meta, Mistral, Cohere, Amazon'un kendi Titan/Nova modelleri dahil çoklu sağlayıcıyı tek IAM kimlik doğrulama ve tek faturalama altında sunar. Adapter, `model_id` + `region` + IAM SigV4 imzalama gerektirir — diğer sağlayıcılardan farklı bir auth akışı.
- **Azure OpenAI / Azure AI Foundry**: OpenAI modellerini + giderek artan şekilde üçüncü parti modelleri (Mistral, Llama, DeepSeek dahil "Models as a Service" kataloğu üzerinden) Azure kimlik doğrulaması (Entra ID / API key) ile sunar. Kurumsal SLA, veri ikametgahı (data residency) ve uyumluluk sertifikaları (HIPAA/SOC2/ISO) açısından kritik.
- **Google Vertex AI**: Gemini ailesinin yanı sıra Anthropic, Mistral, Llama gibi üçüncü parti modelleri de "Model Garden" üzerinden sunar; GCP IAM ile kimlik doğrulama.
- *(Genişletilebilir referans: Oracle OCI Generative AI, IBM watsonx — düşük öncelikli ama adapter mimarisi bunları da kapsayacak şekilde genel tutulmalı.)*

### 2.4 Niş / Hız ve Maliyet Odaklı Sağlayıcılar

| Marka | Konumlandırma |
|---|---|
| **Cohere** | RAG ve enterprise arama odaklı, Command R+ ailesi, büyük context. |
| **Perplexity** | Arama-entegre (sonar) modeller, gerçek zamanlı web bilgisiyle yanıt üretimi. |
| **Together AI** | 200+ açık kaynak/partner modelini serverless endpoint olarak sunan agregatör. |
| **Fireworks AI** | Düşük gecikme odaklı, açık kaynak model hosting. |
| **Groq** | LPU donanımıyla aşırı yüksek throughput/düşük gecikme (özellikle açık ağırlıklı modellerde). |
| **Cerebras / SambaNova** | Donanım-hızlandırmalı çıkarım, çok yüksek token/sn. |
| **Hugging Face Inference Endpoints** | Self-host ile yönetilen barındırma arası; binlerce açık modele erişim. |
| **Replicate** | Konteynerleştirilmiş model çalıştırma, çok modaliteli (görsel/video/ses) modeller dahil. |
| **Local / Self-hosted (Ollama, vLLM, LM Studio, llama.cpp server)** | Veri egemenliği (data sovereignty) gereken senaryolar ve maliyet sıfırlama için zorunlu destek — adapter bunu "yerel sağlayıcı" olarak ele almalı, OpenAI-uyumlu local server'lar (Ollama, vLLM) zaten REST şeması paylaştığı için entegrasyonu nispeten düşük maliyetli. |

### 2.5 Adapter Mimarisi İçin Çıkarılan Tasarım Kuralları

Yukarıdaki tablodan çıkan kritik mimari gereksinim: **sağlayıcılar üç farklı kimlik doğrulama modeli kullanıyor** (basit API key / OAuth-Entra ID / IAM SigV4 imzalama), **iki farklı istek şeması ailesi** kullanıyor (OpenAI-uyumlu Chat Completions tarzı vs. kendine özgü — Anthropic Messages API, Gemini generateContent) ve **bazıları aynı modeli birden fazla "yol" üzerinden sunuyor** (örn. Claude Opus hem doğrudan Anthropic'ten hem Bedrock'tan hem Vertex AI'dan erişilebilir — bu üç yol farklı fiyatlandırma, farklı rate limit, farklı gecikme profiline sahip).

→ **Sonuç:** Provider Adapter katmanı (Bölüm 11), "model" ve "sağlayıcı yolu" kavramlarını **ayrı varlıklar** olarak modellemelidir. Aynı mantıksal model (`claude-opus-4-7`) birden fazla `provider_route` kaydına sahip olabilmeli ve yönlendirme motoru bunlar arasında maliyet/gecikme/kullanılabilirliğe göre seçim yapabilmelidir. Bu, Bölüm 9'daki veritabanı şemasında `models` ve `provider_routes` tablolarının neden ayrı olduğunun gerekçesidir.

---
## 3. PAZAR ARAŞTIRMASI — LLM ROUTER / GATEWAY REKABET ANALİZİ (Haziran 2026)

> Bu bölümün amacı: AI ajanının "tekerleği yeniden icat etmesini" değil, **mevcut en iyi pratiklerin sentezini + rakiplerin boşluklarını dolduran** bir ürün inşa etmesini sağlamak. Her rakip için güçlü yön, zayıf yön ve "bizim ondan ne çalacağımız / nerede onu geçeceğimiz" belirtilmiştir.

### 3.1 OpenRouter — Pazar Lideri (Marketplace Modeli)

- **Model:** Tam yönetilen (managed) SaaS; tek API key ile 300+ modele erişim, kendi altyapısı yok.
- **Güçlü yönler:** Sıfır kurulum, çok geniş model kataloğu, `openrouter/auto` ile otomatik model seçimi, sağlayıcılar arası otomatik failover (özellikle Llama gibi çoklu sağlayıcılı modellerde).
- **Zayıf yönler:** Self-host edilemez (veri egemenliği yok), işlem başına ~%5.5 komisyon, kurumsal guardrail/observability seti zayıf.
- **Bizim için çıkarım:** `auto` model seçimi UX'i kopyalanmaya değer — kullanıcı "en iyi modeli seç" diyebilmeli. Ama biz self-host + managed hibrit olacağız, bu onun en büyük zaafını gideriyor.

### 3.2 LiteLLM — Açık Kaynak Self-Host Standardı

- **Model:** Açık kaynak Python proxy; OpenAI-uyumlu tek endpoint arkasında 100+ sağlayıcı.
- **Güçlü yönler:** Sıfır marj (provider fiyatına ek komisyon yok), virtual key + bütçe sistemi, Docker ile her yerde çalışır, Langfuse/Datadog gibi gözlemlenebilirlik araçlarıyla native entegrasyon.
- **Zayıf yönler:** Gözlemlenebilirlik arayüzü "ham" — iş gücü gerektiriyor; UI/UX rakiplerine göre geride; operasyonel yük (DevOps) gerektiriyor.
- **Bizim için çıkarım:** Sıfır-marj felsefesini ve virtual key/bütçe sistemini doğrudan benimsiyoruz (Bölüm 14, 17) — ama bunu **production-grade, görsel olarak güçlü bir dashboard'la** birleştirerek LiteLLM'in en büyük zaafını (zayıf UI) gideriyoruz.

### 3.3 Portkey — Enterprise Kontrol Düzlemi

- **Model:** "AI için kontrol düzlemi" — yönetilen + (Mart 2026'dan beri) tamamen açık kaynak (Apache 2.0) gateway çekirdeği.
- **Güçlü yönler:** 50+ guardrail (PII redaksiyonu, jailbreak tespiti), denetim (audit) izleri, semantic caching, A2A protokolü desteği, MCP araç entegrasyonu, çoklu kiracı (multi-tenant) yetkilendirme.
- **Zayıf yönler:** Maliyet modeli "kaydedilen log" sayısına dayalı — yüksek hacimde pahalılaşabiliyor; öğrenme eğrisi diğerlerine göre daha dik.
- **Bizim için çıkarım:** Guardrail seti (Bölüm 18) ve audit trail mimarisi doğrudan bu seviyeyi hedef almalı — bu, "enterprise-ready" görünmenin jüri/kullanıcı nezdinde en somut kanıtı.

### 3.4 Bifrost — Performans Şampiyonu (Go Mimarisi)

- **Model:** Go ile yazılmış, son derece düşük gecikmeli self-host gateway.
- **Güçlü yönler:** 5000+ RPS üzerinde sadece tek haneli mikrosaniye (µs) ek gecikme — pazardaki en hızlı proxy katmanlarından biri.
- **Zayıf yönler:** Ekosistem/entegrasyon genişliği LiteLLM kadar olgun değil.
- **Bizim için çıkarım:** Eğer ana dil Python/Node seçilirse (Bölüm 7), kritik yol (hot path — istek yönlendirme ve streaming proxy) için performans bütçesi belirlenmeli; gerekirse bu katman Rust/Go'da ayrı bir mikroservis olarak izole edilebilir (bkz. Bölüm 6.3 Performans Kritik Yol Notu).

### 3.5 Cloudflare AI Gateway / Vercel AI Gateway — Platform-Kilitli Gateway'ler

- **Model:** İlgili bulut/edge platformuna gömülü gateway katmanları.
- **Güçlü yönler:** Sürtünmesiz kurulum, platformun geri kalanıyla (CDN, edge functions, AI SDK) sıkı entegrasyon.
- **Zayıf yönler:** Platform kilidi (lock-in); kendi altyapın dışında yaşayamaz; yönlendirme kuralları daha basit.
- **Bizim için çıkarım:** Platform-agnostik kalmak rekabet avantajı — herhangi bir Docker ortamında (kendi VPS'in, Kubernetes, hatta tek bir Raspberry Pi) çalışabilmeli.

### 3.6 Diğer Dikkate Değer Oyuncular

- **TrueFoundry:** Kurumsal LLMOps platformu; RBAC, bütçe, kendi VPC'inde self-host — Gartner Hype Cycle'da yer alıyor, kurumsal satış odaklı.
- **Helicone:** Gözlemlenebilirlik-öncelikli, hafif proxy katmanı.
- **Eden AI:** LLM'lerin ötesinde OCR/konuşma/çeviri gibi uzman modelleri de kapsayan geniş "AI API agregatörü".
- **Lynkr:** Anthropic wire-protokolünü (`ANTHROPIC_BASE_URL`) native konuşan, Claude Code/Cursor/Codex CLI için "drop-in" self-host proxy — coding-agent kullanım senaryosuna özel optimize.

### 3.7 Sentez — Rekabetçi Konumlandırma Matrisi

| Eksen | OpenRouter | LiteLLM | Portkey | Bifrost | **[PROJE_ADI] (hedef)** |
|---|---|---|---|---|---|
| Model genişliği | ✅✅✅ | ✅✅✅ | ✅✅ | ✅ | ✅✅✅ |
| Self-host kontrolü | ❌ | ✅✅✅ | ✅✅ (kısmi) | ✅✅✅ | ✅✅✅ |
| Gözlemlenebilirlik/guardrail | ✅ | ✅ | ✅✅✅ | ✅ | ✅✅✅ |
| Gecikme/performans | ✅✅ | ✅✅ | ✅✅ | ✅✅✅ | ✅✅ (hedef ✅✅✅) |
| MCP/A2A native desteği | ❌/zayıf | ❌/zayıf | ✅ (kısmi) | ❌ | ✅✅✅ (birinci sınıf) |
| Görsel/UX zanaatkarlığı | ✅✅ | ✅ | ✅✅ | ✅ | ✅✅✅ (Awwards hedefi) |

**Stratejik sonuç:** Hiçbir rakip MCP/A2A'yı birinci sınıf vatandaş olarak ele almıyor ve hiçbiri görsel/UX zanaatkarlığında Awwards seviyesine oynamıyor. Bu projenin **kazanan farklılaştırıcı ekseni budur** — teknik tablo üstünlüğü değil (orada "iyi" olmak yeterli), bu iki eksende **kategori lideri** olmak.

---
## 4. PROTOKOL KATMANI — MCP, A2A, ACP KONUMLANDIRMASI

> Bu bölüm, sistemin "neyi ne zaman konuşacağını" netleştirir. Üç protokol birbirinin **yerine** değil, birbirinin **üstüne** çalışır — bu ayrımı yanlış kuran projeler gereksiz karmaşıklığa düşer.

### 4.1 Üç Protokolün Net Ayrımı

| Protokol | Sahibi / Yönetişim | Çözdüğü Problem | Bizim Sistemdeki Rolü |
|---|---|---|---|
| **MCP (Model Context Protocol)** | Anthropic tarafından açıldı, şu an Linux Foundation altında Agentic AI Foundation (AAIF) yönetişiminde | Bir AI ajanının **araçlara/verilere dikey erişimi**: dosya sistemi, veritabanı, Blender, GitHub, Slack vb. | Sistemin **MCP Orchestration katmanı** (Bölüm 13) — tüm tool-calling bunun üzerinden akar. |
| **A2A (Agent-to-Agent)** | Google tarafından açıldı, Linux Foundation'a bağışlandı | Farklı sağlayıcılardan **ajanların birbirini keşfetmesi ve iş devretmesi** (yatay iletişim) | Faz 2+ için planlanan **çoklu-ajan orkestrasyon** özelliği (Bölüm 13.5) — MVP kapsamı dışında ama mimari buna kapalı kapı bırakmamalı. |
| **ACP (Agent Communication Protocol)** | IBM öncülüğünde, Linux Foundation şemsiyesi altında A2A ile yönetişim yakınsaması sürüyor | REST-native, yerel-öncelikli ajan iletişimi | Düşük öncelik; mimaride yer tutucu olarak bırak, MVP'de implement etme. |

### 4.2 Neden MCP "Birinci Sınıf Vatandaş" Olmalı?

Rakiplerin çoğu (Bölüm 3) MCP'yi ya hiç desteklemiyor ya da "bir entegrasyon" gibi ele alıyor. Bizim tezimiz: **MCP, LLM yönlendirmesi kadar merkezi bir birincil kavram olmalı.** Pratik anlamı:

1. Sistemin veritabanı şeması, bir "konuşma"yı sadece mesajlardan değil, **kullanılan MCP araçlarından** da oluşan bir varlık olarak modellemeli (Bölüm 9 `tool_calls` tablosu).
2. Hangi LLM kullanılırsa kullanılsın (GPT, Claude, Gemini, yerel model), aynı MCP server seti **şeffaf şekilde** kullanılabilmeli — yani bir MCP server'ı bir kere bağla, hangi modeli seçersen seç çalışsın.
3. Sistem, farklı sağlayıcıların **farklı function-calling şemalarını** (OpenAI tools, Anthropic tool_use, Gemini functionDeclarations) MCP'nin tek tip `tools/list` ve `tools/call` şemasından **otomatik çevirmeli** — bu çeviri katmanı (Bölüm 13.3) projenin en yüksek teknik-derinlik puanı alacak parçalarından biri.

### 4.3 MCP'nin 2026 Yol Haritasındaki Gelişmeler (Mimariye Yansıması)

Güncel MCP yönetişim yol haritası şu önceliklere odaklanıyor — sistem bunlara **gelecek-uyumlu (forward-compatible)** olacak şekilde tasarlanmalı:

- **Stateless HTTP transport:** MCP server'ların yatay ölçeklenebilmesi için durumsuz (stateless) çalışabilmesi hedefleniyor. → Bizim MCP Gateway katmanımız, oturum (session) durumunu MCP server'da değil **kendi Redis katmanımızda** tutmalı; böylece hangi transport modeli MCP server tarafında kullanılırsa kullanılsın bizim tarafımız etkilenmez.
- **Tasks primitive (uzun süren işlemler):** "Şimdi çağır, sonra sonucu al" deseni. → Tool-call kayıtları (Bölüm 9) baştan `pending/running/completed/failed` durum makinesiyle modellenmeli, sadece senkron request/response varsayılmamalı.
- **MCP Server Cards (`.well-known` üzerinden keşif):** Merkezi olmayan, otomatik server keşfi. → MCP Registry katmanımız (Bölüm 13.1), hem manuel eklenen hem `.well-known/mcp-server-card.json` üzerinden otomatik keşfedilen server kayıtlarını desteklemeli.

### 4.4 Pratik Sonuç: "Bir App, Üç Bağlantı Türü"

Kullanıcı senaryosu netlik için: Sen bir uygulama kurarsın → (1) LLM bağlantıların (Gemini, ChatGPT, Claude, DeepSeek...) Gateway katmanından geçer, (2) Tool bağlantıların (Blender MCP, GitHub MCP, kendi yazdığın özel MCP server'lar) MCP Orchestration katmanından geçer, (3) İleride başka ajanlarla konuşman gerekirse (örn. kendi otonom oyun geliştirme ajanın bu sisteme bir görev devretmek isterse) bu A2A katmanından geçer. Üçü de aynı uygulamanın parçası ama üç ayrı sorumluluk sınırı (bounded context) olarak kodlanmalı — asla birbirine sızdırılmamalı.

---
## 5. ÜRÜN VİZYONU VE FARKLILAŞMA STRATEJİSİ (Awwards + Yarışma Kriterleri)

### 5.1 Awwards Değerlendirme Eksenleri ve Bu Projeye Yansıması

Awwards jürisi dört eksende puanlar: **Design, Usability, Creativity, Content.** Her biri için somut, kontrol edilebilir gereksinim:

| Eksen | Awwards Beklentisi | Bu Projede Somut Karşılığı |
|---|---|---|
| **Design** | Tutarlı bir tasarım dili, özenli tipografi, anlamlı boşluk (whitespace) kullanımı | Bölüm 19'daki Tokyo Night Design System — sabit bir 8pt grid, iki yazı tipi eşleşmesi (display + mono), tutarlı elevation/gölge sistemi |
| **Usability** | Sezgisel gezinme, hızlı yüklenme, erişilebilirlik | Komut paleti (Cmd+K), klavye-öncelikli gezinme, WCAG 2.1 AA kontrast oranları, <1.5s ilk anlamlı boyama (FCP) |
| **Creativity** | Beklenmedik ama işlevsel etkileşimler | Gerçek zamanlı "istek akışı" görselleştirmesi (canlı bir ağ grafiği üzerinde isteklerin sağlayıcılara akışını animasyonla gösteren dashboard — bkz. 19.4) |
| **Content** | Net metin, anlamlı boş-durum (empty state) tasarımları, hata mesajlarının kalitesi | Her API hatası insan-okunur + makine-okunur (kod) ikilisiyle döner; boş durumlar asla "No data" değil, bağlamsal yönlendirme içerir |

### 5.2 Yazılım Yarışması Jürisi İçin Somut Kanıt Noktaları

Tipik bir uluslararası yazılım yarışması (örn. devpost-tarzı hackathon finalleri, üniversite kapsamlı bitirme yarışmaları, büyük bulut sağlayıcı "build" yarışmaları) şu rubrik eksenlerini kullanır — her biri için projede **somut, gösterilebilir bir artefakt** olmalı:

1. **Teknik karmaşıklık ve özgünlük** → Adaptive routing motoru (Bölüm 10.3) + MCP çapraz-protokol çeviri katmanı (Bölüm 13.3), demo sırasında canlı gösterilebilir olmalı ("şimdi OpenAI'ı kapatıyorum, sistem otomatik DeepSeek'e geçiyor, izleyin" demosu).
2. **Bitmişlik (Completeness)** → Yarım bırakılmış özellik olmamalı; MVP kapsamı net çizilmeli (Bölüm 23) ve o kapsamın **tamamı** uçtan uca çalışmalı.
3. **Gerçek dünya etkisi** → README'de somut bir "bunu gerçekten kendi projelerimde kullanıyorum" anlatısı + canlı bir maliyet tasarrufu metriği ("X projesinde aylık LLM maliyetini %Y azalttı" gibi gerçek/simüle edilmiş veriyle).
4. **Sunum kalitesi** → 90 saniyelik demo videosu senaryosu, mimari diyagram (Bölüm 6), canlı dashboard ekran görüntüleri — bunlar README ve sunum materyali olarak en başından planlanmalı, sona bırakılmamalı.

### 5.3 "Demo Hilesi" Değil, Gerçek Mühendislik — Kırmızı Çizgiler

Jüri/değerlendirici gözünden en çok puan kaybettiren şey, "harika görünen ama kırılgan" sistemlerdir. Bu yüzden şu kırmızı çizgiler bağlayıcıdır:

- Hardcoded API key'ler veya demo'ya özel "mış gibi yapma" kodu **yasak** — her entegrasyon gerçek, çalışan bir entegrasyon olmalı (en azından bir sandbox/test ortamında doğrulanabilir).
- Hata durumları (sağlayıcı 500 döndürürse, rate limit'e takılırsa, timeout olursa) UI'da **sessizce yutulmamalı** — kullanıcıya ne olduğu ve sistemin ne yaptığı (fallback'e geçti mi, yeniden mi denedi) gösterilmeli.
- "Çalışıyor" demek yetmez; **otomatik test kapsamı** (Bölüm 21) olmadan hiçbir modül "tamamlandı" sayılmaz.

---
## 6. SİSTEM MİMARİSİ

### 6.1 Yüksek Seviye Bileşen Diyagramı

```
                                   ┌─────────────────────────────────┐
                                   │      ADMIN DASHBOARD (Next.js)   │
                                   │  Tokyo Night UI · Komut Paleti   │
                                   │  Canlı İstek Akışı · Maliyet     │
                                   └────────────────┬──────────────────┘
                                                    │ REST + WebSocket (gerçek zamanlı metrik)
                                                    ▼
┌──────────────┐      ┌─────────────────────────────────────────────────┐      ┌──────────────────┐
│  İSTEMCİ      │      │              API GATEWAY (FastAPI / Nginx)        │      │  3. PARTI APP'LER │
│  SDK'lar       │─────▶│  Auth · Rate Limit · İstek Doğrulama · Routing   │◀─────│  (senin diğer      │
│ (Python/TS)   │      │  Unified API: /v1/chat/completions (OpenAI-uyumlu)│      │  projelerin)        │
└──────────────┘      └───────────────────────┬─────────────────────────┘      └──────────────────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
            ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐
            │   ROUTING ENGINE     │  │  MCP ORCHESTRATION    │  │   GUARDRAILS KATMANI     │
            │  Cost/Latency/       │  │  Server Registry       │  │  PII Redaksiyon          │
            │  Semantic Routing    │  │  Tool Schema Çeviri    │  │  Jailbreak Tespiti       │
            │  Fallback Zincirleri │  │  Tasks (async) Yönetimi│  │  İçerik Filtreleme       │
            │  Devre Kesici        │  └───────────┬─────────────┘  └─────────────┬─────────────┘
            └──────────┬───────────┘              │                              │
                       │                          ▼                              │
                       │              ┌─────────────────────────┐                │
                       │              │   MCP SERVER'LAR (dış)    │                │
                       │              │  Blender · GitHub · FS     │                │
                       │              │  Slack · Özel server'lar    │                │
                       │              └─────────────────────────┘                │
                       ▼                                                          ▼
            ┌─────────────────────────────────────────────────────────────────────────┐
            │                     PROVIDER ADAPTER KATMANI                               │
            │  OpenAI · Anthropic · Google · xAI · DeepSeek · Qwen · Mistral · Meta        │
            │  AWS Bedrock · Azure OpenAI · Vertex AI · OpenRouter · Groq · Together · ... │
            │  Yerel: Ollama / vLLM / LM Studio                                            │
            └──────────────────────────────────┬──────────────────────────────────────────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       ▼                        ▼                        ▼
            ┌─────────────────┐    ┌─────────────────────┐   ┌─────────────────────┐
            │   POSTGRESQL      │    │       REDIS           │   │   GÖZLEMLENEBİLİRLİK  │
            │ Modeller·Anahtarlar│    │  Önbellek·Rate Limit  │   │  OpenTelemetry → Tempo │
            │ Kullanım·Faturalama│    │  Oturum Durumu         │   │  Prometheus → Grafana  │
            └─────────────────┘    └─────────────────────┘   └─────────────────────┘
```

### 6.2 Çekirdek Bileşenlerin Sorumluluk Sınırları

| Bileşen | Tek Sorumluluğu | Asla Yapmaması Gereken |
|---|---|---|
| **API Gateway** | Kimlik doğrulama, istek şeması doğrulama, hız sınırlama uygulaması | İş mantığı (routing kararı) vermemeli — bunu Routing Engine'e devreder |
| **Routing Engine** | Hangi `provider_route`'un kullanılacağına karar vermek | HTTP isteğini kendisi göndermemeli — bunu Provider Adapter'a devreder |
| **Provider Adapter** | Normalize edilmiş isteği sağlayıcıya özgü şemaya çevirip göndermek, yanıtı geri normalize etmek | Routing/maliyet kararı vermemeli — sadece "söyleneni yap" |
| **MCP Orchestration** | MCP server'larla JSON-RPC konuşmak, tool şemalarını normalize etmek | LLM'e doğrudan istek göndermemeli — sadece tool tanımlarını/sonuçlarını Routing Engine'e sağlar |
| **Guardrails** | İstek/yanıtı politika kurallarına göre denetlemek | Yönlendirme veya önbellekleme kararı vermemeli |

Bu net ayrım, hem test edilebilirliği (her bileşen izole test edilebilir) hem de "neden burada bu var" sorusuna jüri karşısında net cevap verebilmeyi sağlar.

### 6.3 Performans-Kritik Yol Notu

İstek-yönlendirme "hot path"i (gelen istek → routing kararı → sağlayıcıya proxy) gecikme bütçesi açısından kritik. Hedef: gateway'in eklediği ek gecikme **p95'te 15ms'in altında** olmalı (Bifrost referans alınarak, Bölüm 3.4). Eğer ana uygulama dili (Bölüm 7) Python/FastAPI seçilirse, bu hot path'in `asyncio` ile tam asenkron yazılması ve senkron/bloklayıcı hiçbir I/O içermemesi **zorunludur**. Eğer ölçümlerde bu bütçe aşılırsa, hot path tek başına Rust (Axum) veya Go'da ayrı bir mikroservis olarak izole edilip geri kalan sistemle gRPC üzerinden konuşacak şekilde yeniden yazılabilir — bu, mimarinin "performans bilinciyle tasarlandığının" jüri karşısında somut kanıtıdır; ön planda zorunlu değil ama mimari buna izin verecek şekilde modüler tutulmalı.

### 6.4 Çok Kiracılılık (Multi-Tenancy) Modeli

Sistem baştan **çok kiracılı** tasarlanmalı (tek kullanıcı varsayımıyla yazılıp sonra eklenmemeli):

```
Organization (1) ──< Project (N) ──< Virtual API Key (N) ──< Request Log (N)
                            │
                            └──< Budget Policy (1) ──< Alert Rule (N)
```

Bu hiyerarşi, hem "kendi tüm projelerin için tek bir gateway" senaryosunu (her projen ayrı bir `Project` kaydı) hem de gelecekte bunu bir SaaS ürününe dönüştürme senaryosunu (her `Organization` ayrı bir müşteri) aynı veri modeliyle destekler.

---
## 7. TEKNOLOJİ YIĞINI (TECH STACK) — KESİN KARARLAR

> AI ajanı bu kararları **sorgulamadan** uygulamalı. Her karar için gerekçe verilmiştir; bu gerekçeleri README'nin "Architecture Decisions" bölümüne ADR (Architecture Decision Record) formatında işle.

### 7.1 Backend

| Katman | Seçim | Gerekçe |
|---|---|---|
| Ana dil/framework | **Python 3.12+ / FastAPI** | Async-native, Pydantic ile şema doğrulama, AI ekosistemiyle (SDK'lar, MCP Python SDK) doğal uyum |
| Tip güvenliği | **Pydantic v2 + mypy strict mode** | Sağlayıcı şemaları arası normalize ederken çalışma zamanı hatalarını derleme/lint aşamasında yakalamak kritik |
| Asenkron görev kuyruğu | **Celery + Redis (broker)** | Uzun süren MCP Tasks, toplu (batch) işlemler, webhook teslimleri için |
| Gerçek zamanlı katman | **WebSocket (FastAPI native) + Server-Sent Events (streaming completions için)** | LLM streaming yanıtları SSE ile, dashboard canlı metrikleri WebSocket ile |
| Performans-kritik opsiyonel mikroservis | **Rust (Axum) — sadece Bölüm 6.3'teki bütçe aşılırsa** | Hot path izolasyonu |

### 7.2 Veri Katmanı

| Bileşen | Seçim | Gerekçe |
|---|---|---|
| Birincil veritabanı | **PostgreSQL 16+** | İlişkisel bütünlük (organizasyon/proje/anahtar hiyerarşisi), JSONB ile esnek metadata, `pgvector` eklentisiyle semantic cache embedding desteği |
| Önbellek / hız sınırlama / oturum | **Redis 7+** | Token-bucket rate limiting, semantic cache sonuç önbelleği, MCP oturum durumu |
| Vektör arama (semantic cache + semantic routing) | **pgvector (PostgreSQL eklentisi)** | Ayrı bir vektör veritabanı (Qdrant/Pinecone) yerine PostgreSQL içinde tutmak — operasyonel karmaşıklığı azaltır, MVP için yeterli ölçek sağlar |
| Nesne depolama (loglar, büyük payload arşivi) | **S3-uyumlu (MinIO self-host veya AWS S3)** | Büyük request/response gövdelerini veritabanı dışında tutmak |

### 7.3 Frontend

| Katman | Seçim | Gerekçe |
|---|---|---|
| Framework | **Next.js 15 (App Router) + React 19** | Server Components ile dashboard'un ilk yük performansı, streaming UI |
| Tip güvenliği | **TypeScript strict mode** | Backend Pydantic şemalarından OpenAPI → TS tipleri otomatik üretilmeli (`openapi-typescript`) |
| Stil | **Tailwind CSS v4 + CSS değişkenleriyle Tokyo Night tema token'ları** | Bölüm 19'daki tasarım sistemiyle birebir eşleşir |
| Animasyon | **Framer Motion** | Mikro-etkileşimler, sayfa geçişleri, canlı veri görselleştirme animasyonları |
| Veri görselleştirme | **D3.js (özel ağ grafiği için) + Recharts (standart metrik grafikleri için)** | İstek-akışı görselleştirmesi gibi özel gereksinimler D3 gerektirir; standart çizgi/bar grafikler için Recharts yeterli ve hızlı |
| Durum yönetimi | **TanStack Query (sunucu durumu) + Zustand (istemci durumu)** | Sunucu/istemci durum ayrımını net tutmak, gereksiz Redux karmaşıklığından kaçınmak |

### 7.4 Altyapı / DevOps

| Katman | Seçim | Gerekçe |
|---|---|---|
| Konteynerleştirme | **Docker + Docker Compose (geliştirme) / Kubernetes (production, opsiyonel)** | Self-host edilebilirlik vaadi için Docker zorunlu; K8s büyük ölçek için opsiyonel katman |
| Gözlemlenebilirlik | **OpenTelemetry (izleme) → Grafana Tempo (trace) + Prometheus (metrik) + Grafana (dashboard) + Loki (log)** | Tek bir vendor'a kilitlenmeyen, açık standart gözlemlenebilirlik yığını |
| CI/CD | **GitHub Actions** | Mevcut GitHub workflow'unla doğal uyum |
| Sır yönetimi | **Doppler veya HashiCorp Vault (production) / `.env` + `direnv` (geliştirme)** | Sağlayıcı API anahtarlarının güvenli yönetimi kritik |

### 7.5 Neden Bu Kombinasyon (Tek Cümlelik Özet)

Python/FastAPI + Next.js/React kombinasyonu, hem AI/MCP ekosistemiyle (Python SDK'lar) doğal uyum sağlar hem de senin mevcut tech stack geçmişinle (TypeScript, Python, React, Next.js, FastAPI, PostgreSQL, Redis, Docker) birebir örtüşür — yani yeni bir öğrenme eğrisi dayatmaz, doğrudan üretkenliğe geçilebilir.

---
## 8. MONOREPO / KLASÖR YAPISI

> AI ajanı projeyi **birebir bu yapıda** oluşturmalı. Klasör isimleri ve sorumlulukları sabittir; bu, hem jüri/kod-inceleyici için okunabilirlik sağlar hem de Bölüm 6.2'deki sorumluluk sınırlarını dosya sistemi seviyesinde zorlar.

```
[proje-adi]/
├── apps/
│   ├── gateway/                      # FastAPI backend — çekirdek servis
│   │   ├── src/
│   │   │   ├── api/                  # REST/WS endpoint tanımları (router'lar)
│   │   │   │   ├── v1/
│   │   │   │   │   ├── chat.py       # /v1/chat/completions (OpenAI-uyumlu)
│   │   │   │   │   ├── messages.py   # /v1/messages (Anthropic-uyumlu passthrough)
│   │   │   │   │   ├── models.py     # /v1/models (katalog)
│   │   │   │   │   ├── keys.py       # virtual key yönetimi
│   │   │   │   │   ├── usage.py      # kullanım/maliyet sorgulama
│   │   │   │   │   └── mcp.py        # MCP server yönetim endpoint'leri
│   │   │   │   └── ws/
│   │   │   │       └── live_metrics.py
│   │   │   ├── core/
│   │   │   │   ├── config.py         # Pydantic Settings
│   │   │   │   ├── security.py       # auth, key hashleme
│   │   │   │   └── logging.py        # yapılandırılmış (structured) log kurulumu
│   │   │   ├── routing/              # BÖLÜM 10 — Routing Engine
│   │   │   │   ├── engine.py
│   │   │   │   ├── strategies/
│   │   │   │   │   ├── cost_based.py
│   │   │   │   │   ├── latency_based.py
│   │   │   │   │   ├── semantic.py
│   │   │   │   │   └── learned.py
│   │   │   │   ├── circuit_breaker.py
│   │   │   │   └── fallback_chain.py
│   │   │   ├── providers/            # BÖLÜM 11 — Provider Adapter katmanı
│   │   │   │   ├── base.py           # soyut adapter arayüzü
│   │   │   │   ├── registry.py       # plugin keşif/kayıt mekanizması
│   │   │   │   ├── openai_adapter.py
│   │   │   │   ├── anthropic_adapter.py
│   │   │   │   ├── google_adapter.py
│   │   │   │   ├── bedrock_adapter.py
│   │   │   │   ├── azure_openai_adapter.py
│   │   │   │   ├── vertex_adapter.py
│   │   │   │   ├── openrouter_adapter.py
│   │   │   │   ├── deepseek_adapter.py
│   │   │   │   ├── local_adapter.py  # Ollama/vLLM
│   │   │   │   └── ...               # diğer her sağlayıcı kendi dosyası
│   │   │   ├── mcp_orchestration/    # BÖLÜM 13 — MCP katmanı
│   │   │   │   ├── registry.py       # MCP server kayıt/keşif
│   │   │   │   ├── client_pool.py    # MCP client bağlantı havuzu
│   │   │   │   ├── schema_translator.py  # MCP↔provider tool şeması çevirisi
│   │   │   │   └── task_manager.py   # async Tasks primitive yönetimi
│   │   │   ├── guardrails/           # BÖLÜM 18
│   │   │   │   ├── pii_redaction.py
│   │   │   │   ├── jailbreak_detector.py
│   │   │   │   └── content_filter.py
│   │   │   ├── caching/              # BÖLÜM 16
│   │   │   │   ├── semantic_cache.py
│   │   │   │   └── exact_cache.py
│   │   │   ├── billing/              # BÖLÜM 17
│   │   │   │   ├── budget_enforcer.py
│   │   │   │   └── cost_calculator.py
│   │   │   ├── observability/        # BÖLÜM 15
│   │   │   │   ├── tracing.py
│   │   │   │   └── metrics.py
│   │   │   ├── db/
│   │   │   │   ├── models/           # SQLAlchemy modelleri (BÖLÜM 9 şemasıyla birebir)
│   │   │   │   └── migrations/       # Alembic migration'ları
│   │   │   └── main.py               # FastAPI app giriş noktası
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── e2e/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── dashboard/                    # Next.js admin paneli
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── overview/         # canlı istek akışı, maliyet özeti
│   │   │   │   ├── providers/        # sağlayıcı/route yönetimi
│   │   │   │   ├── routing-rules/    # yönlendirme kuralı editörü
│   │   │   │   ├── mcp-servers/      # MCP server bağlama/yönetim UI
│   │   │   │   ├── playground/       # canlı model test alanı
│   │   │   │   ├── logs/             # istek log gezgini
│   │   │   │   └── settings/
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui temelli, Tokyo Night token'larıyla özelleştirilmiş
│   │   │   ├── charts/
│   │   │   └── flow-visualization/   # D3 tabanlı canlı istek-akışı bileşeni
│   │   ├── lib/
│   │   │   ├── api-client.ts         # openapi-typescript'ten üretilen tipli client
│   │   │   └── ws-client.ts
│   │   ├── styles/
│   │   │   └── tokyo-night-tokens.css
│   │   └── package.json
│   │
│   └── cli/                          # Opsiyonel: terminal üzerinden yönetim (Faz 3)
│       └── src/
│
├── packages/                         # Paylaşılan kod (monorepo workspace)
│   ├── sdk-python/                   # Diğer projelerinin (Anka, ReelMind vb.) kullanacağı istemci SDK
│   ├── sdk-typescript/
│   └── shared-types/                 # OpenAPI'den üretilen ortak tip tanımları
│
├── infra/
│   ├── docker-compose.yml            # tek komutla yerel kalkış
│   ├── docker-compose.prod.yml
│   ├── k8s/                          # opsiyonel Kubernetes manifest'leri
│   └── terraform/                    # opsiyonel IaC (bulut dağıtımı için)
│
├── docs/
│   ├── architecture/                 # ADR'lar (Architecture Decision Records)
│   ├── api-reference/
│   └── adding-a-provider.md          # yeni sağlayıcı ekleme rehberi (Bölüm 11.4)
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── CLAUDE.md                         # AI kod asistanları için proje-spesifik kurallar (Bölüm 25)
├── README.md
└── LICENSE
```

### 8.1 Bu Yapının Gerekçesi

`apps/gateway` içindeki klasörleme **doğrudan Bölüm 6.2'deki sorumluluk tablosunu** yansıtır — `routing/`, `providers/`, `mcp_orchestration/`, `guardrails/` birbirinden bağımsız, ayrı test edilebilir paketlerdir. Bu, hem kod incelemesinde ("bu PR hangi sorumluluğu değiştiriyor?") hem de jüri sunumunda ("işte mimarinin kod karşılığı, bire bir") netlik sağlar.

---
## 9. VERİTABANI ŞEMASI (PostgreSQL)

> Aşağıdaki şema, Alembic migration'larının ilk sürümü olarak birebir uygulanmalı. Her tablo için neden var olduğu açıklanmıştır — AI ajanı gereksiz alan eklemekten veya şemayı "basitleştirmekten" kaçınmalı, bu şema Bölüm 6.4'teki çok-kiracılı modeli ve Bölüm 4.3'teki MCP Tasks durum makinesini doğrudan destekleyecek şekilde tasarlanmıştır.

```sql
-- ══════════════════════════════════════════════════════════════
-- 9.1 KİMLİK / ÇOK KİRACILILIK
-- ══════════════════════════════════════════════════════════════

CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    settings        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, slug)
);

CREATE TABLE virtual_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    key_hash        TEXT NOT NULL UNIQUE,         -- ham anahtar asla saklanmaz, sadece hash
    key_prefix      TEXT NOT NULL,                -- UI'da gösterilen "pk_live_ab12..." önizleme
    scopes          TEXT[] NOT NULL DEFAULT '{}', -- ['chat:write', 'admin:read', ...]
    rate_limit_rpm  INTEGER,                      -- dakikada istek limiti (null = sınırsız)
    budget_usd_cents BIGINT,                      -- aylık bütçe (null = sınırsız)
    is_active       BOOLEAN NOT NULL DEFAULT true,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ
);
CREATE INDEX idx_virtual_keys_project ON virtual_keys(project_id);

-- ══════════════════════════════════════════════════════════════
-- 9.2 MODEL KATALOĞU VE SAĞLAYICI YOLLARI
-- (Bölüm 2.5'teki "model ≠ sağlayıcı yolu" ayrımının veritabanı karşılığı)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE models (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name      TEXT NOT NULL UNIQUE,     -- örn. 'claude-opus-4-7' (mantıksal model)
    family              TEXT NOT NULL,            -- 'claude', 'gpt', 'gemini', 'deepseek' ...
    capabilities        JSONB NOT NULL DEFAULT '{}'::jsonb,
                                                   -- {"vision": true, "tool_use": true,
                                                   --  "context_window": 1000000,
                                                   --  "max_output_tokens": 64000,
                                                   --  "supports_streaming": true}
    is_active           BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE provider_routes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id            UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    provider_key        TEXT NOT NULL,            -- 'anthropic_direct' | 'aws_bedrock' | 'vertex_ai' ...
    provider_model_id   TEXT NOT NULL,            -- sağlayıcının kendi model adlandırması
    auth_credential_ref TEXT NOT NULL,             -- sır yöneticisindeki referans, ham sır DEĞİL
    region              TEXT,                       -- Bedrock/Vertex için bölge
    pricing_input_per_million_cents   NUMERIC(10,4) NOT NULL,
    pricing_output_per_million_cents  NUMERIC(10,4) NOT NULL,
    priority            INTEGER NOT NULL DEFAULT 100,  -- düşük sayı = yönlendirmede öncelik
    avg_latency_ms      INTEGER,                   -- hareketli ortalama, routing motorunca güncellenir
    is_healthy          BOOLEAN NOT NULL DEFAULT true, -- circuit breaker tarafından yönetilir
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_provider_routes_model ON provider_routes(model_id);

-- ══════════════════════════════════════════════════════════════
-- 9.3 YÖNLENDİRME KURALLARI (kullanıcı tanımlı politikalar)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE routing_policies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    strategy        TEXT NOT NULL,            -- 'cost_optimized' | 'latency_optimized' |
                                               -- 'semantic' | 'fallback_chain' | 'manual'
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
                                               -- strateji-spesifik parametreler, örn.
                                               -- {"fallback_order": ["uuid1","uuid2"],
                                               --  "max_cost_per_request_cents": 5}
    is_default      BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════
-- 9.4 İSTEK GEÇMİŞİ / GÖZLEMLENEBİLİRLİK
-- ══════════════════════════════════════════════════════════════

CREATE TABLE requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    virtual_key_id      UUID NOT NULL REFERENCES virtual_keys(id),
    model_requested     TEXT NOT NULL,         -- istemcinin istediği mantıksal model
    provider_route_id   UUID REFERENCES provider_routes(id), -- gerçekte kullanılan yol
    status              TEXT NOT NULL,         -- 'success' | 'error' | 'fallback_used' | 'cached'
    fallback_chain      JSONB,                 -- denenen route'ların sıralı listesi (varsa)
    input_tokens        INTEGER,
    output_tokens        INTEGER,
    cost_usd_cents       NUMERIC(10,4),
    latency_ms           INTEGER,
    cache_hit            BOOLEAN NOT NULL DEFAULT false,
    error_code           TEXT,
    trace_id              TEXT,                 -- OpenTelemetry trace ID, Grafana Tempo ile çapraz referans
    request_body_ref      TEXT,                 -- büyük gövdeler S3/MinIO'da, burada sadece referans
    response_body_ref      TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_requests_key_time ON requests(virtual_key_id, created_at DESC);
CREATE INDEX idx_requests_status ON requests(status);

-- ══════════════════════════════════════════════════════════════
-- 9.5 MCP KATMANI (Bölüm 4.3'teki Tasks durum makinesi)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE mcp_servers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,             -- örn. 'blender-mcp', 'github-mcp'
    transport       TEXT NOT NULL,             -- 'stdio' | 'streamable_http' | 'sse'
    connection_uri  TEXT NOT NULL,
    auth_credential_ref TEXT,
    discovered_via  TEXT NOT NULL DEFAULT 'manual', -- 'manual' | 'well_known_card' | 'registry'
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mcp_tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mcp_server_id   UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    tool_name       TEXT NOT NULL,
    input_schema    JSONB NOT NULL,            -- MCP'nin kendi JSON Schema tanımı
    description     TEXT,
    last_synced_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mcp_server_id, tool_name)
);

CREATE TABLE tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    mcp_tool_id     UUID NOT NULL REFERENCES mcp_tools(id),
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|running|completed|failed
    input_payload   JSONB NOT NULL,
    output_payload  JSONB,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX idx_tool_calls_request ON tool_calls(request_id);
CREATE INDEX idx_tool_calls_status ON tool_calls(status) WHERE status IN ('pending','running');

-- ══════════════════════════════════════════════════════════════
-- 9.6 GUARDRAILS / DENETİM İZLERİ
-- ══════════════════════════════════════════════════════════════

CREATE TABLE guardrail_violations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    rule_type       TEXT NOT NULL,             -- 'pii' | 'jailbreak' | 'content_policy'
    severity        TEXT NOT NULL,             -- 'blocked' | 'flagged' | 'redacted'
    detail          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    actor           TEXT NOT NULL,             -- kullanıcı e-postası veya 'system'
    action          TEXT NOT NULL,             -- 'key.created' | 'route.disabled' | ...
    target          TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ══════════════════════════════════════════════════════════════
-- 9.7 SEMANTIC CACHE (pgvector)
-- ══════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE semantic_cache_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    prompt_embedding vector(1536),             -- embedding boyutu kullanılan embed modeline göre ayarlanır
    prompt_text_hash TEXT NOT NULL,
    response_payload JSONB NOT NULL,
    similarity_threshold NUMERIC(3,2) NOT NULL DEFAULT 0.95,
    hit_count        INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_semantic_cache_embedding ON semantic_cache_entries
    USING ivfflat (prompt_embedding vector_cosine_ops) WITH (lists = 100);
```

### 9.1 Şema Tasarım Kararlarının Gerekçesi

- **`requests.request_body_ref` / `response_body_ref` neden referans, neden doğrudan JSONB değil:** Büyük context pencereli (1M+ token) isteklerin ham gövdesini PostgreSQL satırında tutmak, tablo şişmesine ve yedekleme sürelerinin patlamasına yol açar. Bunun yerine S3/MinIO'da saklanıp burada sadece referans tutulur (Bölüm 7.2).
- **`tool_calls` neden ayrı bir tablo, `requests` içine gömülü JSONB değil:** Bölüm 4.3'teki MCP Tasks durum makinesi (pending→running→completed/failed) **sorgulanabilir** olmalı — "şu an çalışan tüm tool çağrılarını göster" gibi bir sorgu, JSONB içine gömülü veriyle verimsiz olurdu.
- **`provider_routes.is_healthy` neden var:** Bölüm 10.4'teki devre kesici (circuit breaker) deseni, bir sağlayıcı yolunun art arda hata vermesi durumunda bu alanı `false` yapar ve yönlendirme motoru bu yolu otomatik olarak fallback zincirinden çıkarır — manuel müdahale gerekmeden.

---
## 10. ÇEKİRDEK ROUTING ENGINE TASARIMI

> Bu, sistemin **teknik derinlik puanını en çok belirleyecek** bölümdür. Naif bir "if/else sağlayıcı seç" mantığı yarışma jürisinde puan getirmez — aşağıdaki dört stratejinin **gerçekten çalışan, ölçülebilir** implementasyonları gerekir.

### 10.1 Routing Engine'in Genel Akışı

```
İstek geldi
    │
    ▼
1. İstemcinin istediği mantıksal modeli çöz (örn. "claude-opus-4-7")
    │
    ▼
2. O modele ait tüm aktif provider_routes'ları getir (Bölüm 9.2)
    │
    ▼
3. Projenin routing_policy'sine göre stratejiyi uygula (10.2-10.5)
    │
    ▼
4. Devre kesici durumu sağlıklı olmayan route'ları ele (10.4)
    │
    ▼
5. Seçilen route'a Provider Adapter üzerinden gönder
    │
    ▼
6. Hata/timeout → fallback zincirindeki sıradaki route'u dene (10.5)
    │
    ▼
7. Sonucu logla (requests tablosu), gecikme/sağlık metriklerini güncelle
```

### 10.2 Strateji: Maliyet-Optimize Yönlendirme (Cost-Based)

```python
# apps/gateway/src/routing/strategies/cost_based.py

class CostBasedStrategy(RoutingStrategy):
    """
    Verilen kalite eşiğini (min_capability_score) karşılayan route'lar
    arasından, beklenen toplam maliyeti (input+output token tahminine göre)
    en düşük olanı seçer.

    Önemli nüans: Sadece "en ucuz model"i seçmek yanlış sonuç verir —
    ucuz ama yetersiz bir model fazla retry/fallback'e yol açıp net
    maliyeti artırabilir. Bu yüzden strateji, geçmiş `requests` verisinden
    her route için 'fallback_rate' (o route seçildiğinde fallback'e düşme
    oranı) hesaba katar.
    """

    async def select(
        self,
        candidates: list[ProviderRoute],
        request_context: RequestContext,
    ) -> ProviderRoute:
        estimated_input_tokens = estimate_tokens(request_context.messages)
        estimated_output_tokens = request_context.max_tokens or DEFAULT_OUTPUT_ESTIMATE

        scored = []
        for route in candidates:
            if not route.is_healthy:
                continue
            raw_cost = (
                (estimated_input_tokens / 1_000_000) * route.pricing_input_per_million_cents
                + (estimated_output_tokens / 1_000_000) * route.pricing_output_per_million_cents
            )
            fallback_rate = await self._get_recent_fallback_rate(route.id)
            # Fallback olasılığı yüksekse efektif maliyeti cezalandır
            effective_cost = raw_cost * (1 + fallback_rate)
            scored.append((effective_cost, route))

        if not scored:
            raise NoHealthyRouteError(request_context.requested_model)

        scored.sort(key=lambda x: x[0])
        return scored[0][1]
```

### 10.3 Strateji: Gecikme-Optimize Yönlendirme (Latency-Based)

```python
# apps/gateway/src/routing/strategies/latency_based.py

class LatencyBasedStrategy(RoutingStrategy):
    """
    Her route için Redis'te tutulan kayan pencereli (sliding window)
    p50/p95 gecikme değerlerine göre en hızlı sağlıklı route'u seçer.
    Gerçek zamanlı uygulamalar (sesli asistan, canlı kod tamamlama) için
    varsayılan strateji.
    """

    async def select(
        self, candidates: list[ProviderRoute], request_context: RequestContext
    ) -> ProviderRoute:
        latencies = await asyncio.gather(*[
            self._redis_get_p95_latency(route.id) for route in candidates
            if route.is_healthy
        ])
        healthy = [r for r in candidates if r.is_healthy]
        ranked = sorted(zip(healthy, latencies), key=lambda x: x[1] or float("inf"))
        return ranked[0][0]
```

### 10.4 Strateji: Semantic Routing (Görev Tipine Göre Model Seçimi)

```python
# apps/gateway/src/routing/strategies/semantic.py

class SemanticRoutingStrategy(RoutingStrategy):
    """
    Bu strateji 'hangi sağlayıcı en ucuz' sorusunu değil, 'bu görev tipi
    için hangi MODEL EN UYGUN' sorusunu çözer. Gelen isteğin embedding'i
    çıkarılır ve önceden etiketlenmiş görev-kategorisi prototiplerine
    (kod üretimi, yaratıcı yazım, matematik/akıl yürütme, basit
    sınıflandırma, çok-dilli çeviri) kosinüs benzerliğiyle eşlenir.
    Her kategori için Bölüm 2'deki katalogdan önerilen model eşlemesi
    config dosyasında tutulur (örn. "kod üretimi" → önce DeepSeek V4 Pro,
    fallback Claude Opus; "basit sınıflandırma" → küçük/ucuz bir model).

    Bu, OpenRouter'ın 'auto' seçimi gibi davranır ama AÇIKÇA AÇIKLANABİLİR
    (explainable) olmalı: seçilen route ile birlikte "neden bu seçildi"
    bilgisi (similarity_score, matched_category) response metadata'sına
    eklenmeli — kara kutu olmamalı.
    """

    async def select(
        self, candidates: list[ProviderRoute], request_context: RequestContext
    ) -> tuple[ProviderRoute, dict]:
        embedding = await embed_text(request_context.last_user_message)
        category, score = await self._match_category(embedding)
        preferred_model_ids = ROUTING_CONFIG["semantic_categories"][category]["preferred_models"]

        for model_id in preferred_model_ids:
            match = next((c for c in candidates if c.model_id == model_id and c.is_healthy), None)
            if match:
                return match, {"matched_category": category, "similarity_score": score}

        # Eşleşme yoksa maliyet stratejisine düş
        fallback = CostBasedStrategy()
        return await fallback.select(candidates, request_context), {"matched_category": "fallback"}
```

### 10.5 Strateji: Öğrenen Yönlendirme (Learned Routing) — İleri Seviye / Faz 2

```python
# apps/gateway/src/routing/strategies/learned.py

class LearnedRoutingStrategy(RoutingStrategy):
    """
    FAZ 2 ÖZELLİĞİ — MVP'de uygulanmaz, ama mimari arayüz buna izin
    verecek şekilde tasarlanmalı (RoutingStrategy soyut sınıfı sabit
    kalmalı).

    Fikir: Geçmiş `requests` tablosundaki (görev kategorisi, seçilen
    route, gerçekleşen maliyet, gerçekleşen kalite-sinyali [kullanıcı
    geri bildirimi veya otomatik değerlendirme skoru]) üçlülerinden
    hafif bir öğrenen model (örn. küçük bir gradient boosting modeli
    veya çok-kollu haydut/multi-armed bandit algoritması — epsilon-greedy
    veya Thompson Sampling) eğitilip, zamanla "bu tip istek için hangi
    route'un gerçekten en iyi maliyet/kalite dengesini verdiği" otomatik
    öğrenilir. Bu, dokümanda bahsedilen rakiplerin (Bölüm 3) HİÇBİRİNDE
    olmayan, jüri karşısında en çok puan getirecek farklılaştırıcı.
    """
    pass  # Faz 2'de implement edilecek — arayüz tanımı yeterli MVP için
```

### 10.6 Devre Kesici (Circuit Breaker) Deseni

```python
# apps/gateway/src/routing/circuit_breaker.py

class CircuitBreaker:
    """
    Klasik üç-durumlu devre kesici: CLOSED (normal) → OPEN (route'u
    devre dışı bırak) → HALF_OPEN (tek bir test isteğiyle kontrol et).

    Eşikler config'den okunur, örnek varsayılan:
      - 5 ardışık hata → OPEN
      - OPEN durumunda 30 saniye bekle → HALF_OPEN
      - HALF_OPEN'da 1 başarılı istek → CLOSED, sayaç sıfırla
      - HALF_OPEN'da 1 başarısız istek → tekrar OPEN, bekleme süresi
        üstel olarak artar (exponential backoff, max 5 dakika)
    """

    async def record_success(self, route_id: UUID) -> None: ...
    async def record_failure(self, route_id: UUID) -> None: ...
    async def is_available(self, route_id: UUID) -> bool: ...
```

Devre kesici durumu Redis'te tutulur (`circuit:{route_id}` anahtarı altında state + sayaçlar) — bu sayede çoklu gateway instance'ı arasında **paylaşılan** durum olur, her instance kendi izole görüşüne sahip olmaz.

### 10.7 Fallback Zinciri Yürütücüsü

```python
# apps/gateway/src/routing/fallback_chain.py

async def execute_with_fallback(
    primary_route: ProviderRoute,
    fallback_routes: list[ProviderRoute],
    request_context: RequestContext,
) -> ProviderResponse:
    attempted: list[UUID] = []
    for route in [primary_route, *fallback_routes]:
        if not await circuit_breaker.is_available(route.id):
            continue
        attempted.append(route.id)
        try:
            response = await provider_registry.get_adapter(route.provider_key).send(
                route, request_context
            )
            await circuit_breaker.record_success(route.id)
            response.metadata["fallback_chain"] = attempted
            return response
        except (ProviderTimeoutError, ProviderRateLimitError, ProviderServerError) as e:
            await circuit_breaker.record_failure(route.id)
            logger.warning("route_failed", route_id=route.id, error=str(e))
            continue
    raise AllRoutesExhaustedError(attempted)
```

**Kritik tasarım kuralı:** Fallback sadece **geçici/altyapısal hatalarda** (timeout, 429, 5xx) tetiklenmeli — istemcinin kendi hatalı isteğinden (400 Bad Request, içerik politikası reddi) kaynaklanan hatalarda fallback denenmemeli, çünkü bu durumda diğer sağlayıcı da aynı sebeple reddedecektir; bu durum hata response'unda **açıkça ayırt edilmeli**.

---
## 11. PROVIDER ADAPTER PATTERN

> Bu katman, Bölüm 2'deki onlarca farklı sağlayıcıyı **tek bir arayüz** arkasında normalize eder. Tasarım deseni: **Adapter + Plugin Registry**, böylece yeni bir sağlayıcı eklemek mevcut kodu değiştirmeden, sadece yeni bir dosya eklemekle mümkün olur (Open/Closed Principle).

### 11.1 Soyut Adapter Arayüzü

```python
# apps/gateway/src/providers/base.py

from abc import ABC, abstractmethod
from typing import AsyncIterator

class ProviderAdapter(ABC):
    """
    Her sağlayıcı adapter'ı bu arayüzü implement eder. Routing Engine ve
    API Gateway, ASLA bir sağlayıcıya özgü detay bilmez — sadece bu
    arayüzle konuşur.
    """

    provider_key: str  # 'openai', 'anthropic', 'aws_bedrock', ...

    @abstractmethod
    async def send(
        self, route: ProviderRoute, request: NormalizedRequest
    ) -> NormalizedResponse:
        """Senkron (non-streaming) tamamlama isteği."""
        ...

    @abstractmethod
    async def stream(
        self, route: ProviderRoute, request: NormalizedRequest
    ) -> AsyncIterator[NormalizedStreamChunk]:
        """SSE/streaming tamamlama isteği."""
        ...

    @abstractmethod
    async def health_check(self, route: ProviderRoute) -> bool:
        """Devre kesici tarafından periyodik çağrılan hafif sağlık kontrolü."""
        ...

    @abstractmethod
    def normalize_request(self, openai_format_request: dict) -> NormalizedRequest:
        """OpenAI-uyumlu giriş şemasını sağlayıcıya özgü şemaya çevirir."""
        ...

    @abstractmethod
    def normalize_response(self, provider_response: dict) -> NormalizedResponse:
        """Sağlayıcıya özgü çıkış şemasını birleşik (unified) şemaya çevirir."""
        ...

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int:
        """Maliyet tahmini için sağlayıcıya özgü tokenizer kullanır
        (örn. tiktoken OpenAI için, Anthropic'in kendi token sayacı vb.)."""
        ...
```

### 11.2 Neden "Unified Schema" Şart — Sağlayıcılar Arası Şema Farkları

Adapter'ların çözmesi gereken somut farklar (AI ajanının her adapter'da özellikle dikkat etmesi gereken noktalar):

| Konsept | OpenAI Şeması | Anthropic Şeması | Gemini Şeması |
|---|---|---|---|
| Mesaj rolleri | `system` ayrı mesaj olabilir | `system` üst seviye ayrı alan, mesaj listesinde değil | `systemInstruction` üst seviye ayrı alan |
| Araç tanımı | `tools: [{type:"function", function:{...}}]` | `tools: [{name, description, input_schema}]` | `tools: [{functionDeclarations:[...]}]` |
| Araç çağrısı yanıtı | `tool_calls` mesaj alanında | `content` içinde `tool_use` bloğu | `functionCall` parçası |
| Streaming formatı | `data: {...}\n\n` SSE, `delta.content` | SSE, `content_block_delta` event'leri | gRPC streaming veya SSE, farklı chunk şeması |
| Maks. çıktı token parametresi | `max_tokens` (bazı modellerde `max_completion_tokens`) | `max_tokens` (zorunlu alan) | `maxOutputTokens` |

**Tasarım kuralı:** `NormalizedRequest`/`NormalizedResponse` Pydantic modelleri OpenAI Chat Completions şemasına en yakın ortak payda olarak tasarlanır (çünkü pazar standardı budur — Bölüm 3'teki tüm rakipler de bunu yapıyor), ama **kayıpsız** olmalı: Anthropic'e özgü `extended_thinking` veya Gemini'ye özgü `groundingMetadata` gibi alanlar `provider_specific` adlı bir genişletme alanında kaybolmadan taşınmalı — bu, "lowest common denominator'a indirgeyip değer kaybeden" rakiplerden ayrışan bir nokta.

### 11.3 Örnek Adapter İmplementasyonu (Anthropic)

```python
# apps/gateway/src/providers/anthropic_adapter.py

class AnthropicAdapter(ProviderAdapter):
    provider_key = "anthropic"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        system_msg = next((m["content"] for m in req["messages"] if m["role"] == "system"), None)
        non_system = [m for m in req["messages"] if m["role"] != "system"]
        return NormalizedRequest(
            messages=non_system,
            system=system_msg,
            max_tokens=req.get("max_tokens", 4096),  # Anthropic'te zorunlu, varsayılan ata
            tools=self._translate_tools(req.get("tools", [])),
            stream=req.get("stream", False),
        )

    def _translate_tools(self, openai_tools: list[dict]) -> list[dict]:
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"]["parameters"],
            }
            for t in openai_tools
        ]

    async def send(self, route: ProviderRoute, request: NormalizedRequest) -> NormalizedResponse:
        client = await self._get_client(route)
        response = await client.messages.create(
            model=route.provider_model_id,
            system=request.system,
            messages=request.messages,
            max_tokens=request.max_tokens,
            tools=request.tools or NOT_GIVEN,
        )
        return self.normalize_response(response)

    def normalize_response(self, response) -> NormalizedResponse:
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=b.input)
            for b in response.content if b.type == "tool_use"
        ]
        text = "".join(b.text for b in response.content if b.type == "text")
        return NormalizedResponse(
            text=text,
            tool_calls=tool_calls,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason,
            provider_specific={"extended_thinking": getattr(response, "thinking", None)},
        )
```

### 11.4 Plugin Mimarisi — Yeni Sağlayıcı Ekleme Süreci

```python
# apps/gateway/src/providers/registry.py

class ProviderRegistry:
    """
    Tüm adapter'lar uygulama başlangıcında otomatik keşfedilir
    (importlib ile providers/ klasörü taranır, ProviderAdapter alt
    sınıfları otomatik kaydedilir). Yeni bir sağlayıcı eklemek için
    geliştirici SADECE şunu yapar:

      1. providers/yeni_saglayici_adapter.py dosyası oluştur
      2. ProviderAdapter'ı implement et (11.1'deki 6 metod)
      3. docs/adding-a-provider.md'deki checklist'i takip et
      4. provider_routes tablosuna seed migration ekle

    Mevcut hiçbir dosya değiştirilmez — registry kodu, routing engine,
    API katmanı SIFIR değişiklik gerektirir. Bu, projenin "30 saniyede
    yeni model eklenebilir" iddiasının somut kanıtıdır (demo'da canlı
    gösterilebilir).
    """

    _adapters: dict[str, type[ProviderAdapter]] = {}

    @classmethod
    def register(cls, adapter_cls: type[ProviderAdapter]) -> type[ProviderAdapter]:
        cls._adapters[adapter_cls.provider_key] = adapter_cls
        return adapter_cls

    def get_adapter(self, provider_key: str) -> ProviderAdapter:
        if provider_key not in self._adapters:
            raise UnknownProviderError(provider_key)
        return self._adapters[provider_key]()
```

### 11.5 Özellikle Dikkat Edilmesi Gereken Üç Sağlayıcı (Standart-Dışı Auth)

- **AWS Bedrock:** IAM SigV4 imza zorunlu — `boto3` veya manuel SigV4 imzalama gerekir, basit Bearer token DEĞİL. Adapter, `aws_access_key_id`/`aws_secret_access_key`/`session_token` üçlüsünü sır yöneticisinden çekmeli.
- **Azure OpenAI:** Hem API key hem Entra ID (OAuth2 client credentials) destekleyebilmeli; endpoint URL'i sağlayıcıya özgü (`{resource}.openai.azure.com`) ve `api-version` query parametresi zorunlu.
- **Google Vertex AI:** GCP service account JSON anahtarı ile OAuth2 token üretimi gerekir; Gemini API (AI Studio) basit API key kullanırken Vertex AI tamamen farklı bir kimlik doğrulama akışına sahiptir — bu ikisi **aynı model ailesi olsa da iki ayrı adapter** olarak yazılmalı (`gemini_direct_adapter.py` ve `vertex_ai_adapter.py`).

---
## 12. UNIFIED API TASARIMI

### 12.1 Tasarım Felsefesi: "OpenAI-Uyumlu, Ama Kilitli Değil"

Pazar standardı (Bölüm 3'teki tüm rakipler) OpenAI'nin Chat Completions şemasını ortak payda olarak benimsemiş durumda — bu, mevcut SDK'ların (`openai` Python/Node paketi) sadece `base_url` değiştirilerek doğrudan kullanılabilmesini sağlıyor. Bu projede de birincil giriş noktası bu olmalı, ama Bölüm 11.2'de bahsedilen "kayıpsızlık" ilkesi gereği **native passthrough endpoint'leri** de sunulmalı.

### 12.2 Endpoint Haritası

| Endpoint | Davranış |
|---|---|
| `POST /v1/chat/completions` | OpenAI-uyumlu birincil giriş noktası. `model` alanı mantıksal model adı (`canonical_name`) olabileceği gibi, `provider:model` formatıyla (örn. `bedrock:claude-opus-4-7`) açıkça bir route da zorlanabilir. |
| `POST /v1/messages` | Anthropic Messages API şemasını **birebir** kabul eder ve birebir döner — Anthropic SDK'sını değiştirmeden kullanmak isteyenler için native passthrough. |
| `POST /v1/responses` | OpenAI'nin yeni nesil Responses API şeması için native passthrough (computer-use, built-in tool çağırma senaryoları). |
| `GET /v1/models` | Katalogdaki tüm aktif mantıksal modelleri, kapasitelerini ve (varsa) gerçek zamanlı fiyatlandırmasını döner. |
| `POST /v1/embeddings` | Embedding modelleri için ayrı, hafif endpoint (semantic cache/routing'in kendi iç kullanımıyla aynı altyapıyı paylaşır). |
| `POST /v1/keys`, `GET /v1/keys`, `DELETE /v1/keys/{id}` | Virtual key yönetimi (Bölüm 14). |
| `GET /v1/usage` | Proje/anahtar bazlı kullanım ve maliyet sorgulama, zaman aralığı filtresiyle. |
| `POST /v1/mcp/servers`, `GET /v1/mcp/servers` | MCP server bağlama/listeleme (Bölüm 13). |
| `WS /v1/live` | Dashboard için gerçek zamanlı istek akışı, maliyet sayaçları, sağlık durumu. |

### 12.3 İstek/Yanıt Meta Verisi — Şeffaflık İlkesi

Her yanıt, standart OpenAI alanlarına ek olarak **bu projeye özgü bir `gateway_metadata` bloğu** içermeli — bu, Bölüm 10.4'teki "kara kutu olmama" ilkesinin API sözleşmesindeki karşılığı:

```json
{
  "id": "chatcmpl-...",
  "choices": [ ... ],
  "usage": { "prompt_tokens": 120, "completion_tokens": 340, "total_tokens": 460 },
  "gateway_metadata": {
    "selected_route": {
      "provider": "anthropic_direct",
      "model": "claude-opus-4-7",
      "region": null
    },
    "routing_strategy": "semantic",
    "matched_category": "code_generation",
    "fallback_chain": ["route_id_1"],
    "cache_hit": false,
    "cost_usd_cents": 0.0234,
    "latency_ms": 842,
    "guardrail_checks": { "pii": "passed", "jailbreak": "passed" }
  }
}
```

### 12.4 Streaming Sözleşmesi

Tüm streaming yanıtlar SSE üzerinden, OpenAI'nin `delta` chunk formatında akar — sağlayıcı tarafı ne olursa olsun (Anthropic `content_block_delta`, Gemini chunk'ları) adapter katmanı bunu **istemciye ulaşmadan önce** normalize eder. Stream'in son chunk'ında (`finish_reason` dolu olduğunda) `gateway_metadata` bloğu da SSE event'i olarak eklenir, böylece streaming istemciler de maliyet/route bilgisine erişebilir.

### 12.5 SDK Katmanı (packages/sdk-python, packages/sdk-typescript)

Senin diğer projelerinin (otomasyon ajanları, video pipeline, oyun geliştirme asistanı) bu sistemi kullanması için ince (thin) bir SDK katmanı sağlanmalı — altta düz HTTP istekleri, üstte ergonomik bir arayüz:

```python
from gateway_sdk import GatewayClient

client = GatewayClient(api_key="pk_live_...", base_url="https://gateway.local")

response = await client.chat(
    model="claude-opus-4-7",          # veya "auto" → semantic routing devreye girer
    messages=[{"role": "user", "content": "..."}],
    routing_policy="cost_optimized",  # opsiyonel override
    mcp_servers=["blender-mcp"],      # bu istekte hangi MCP araçlarının erişilebilir olacağı
)
```

---
## 13. MCP ENTEGRASYON KATMANI

> Bölüm 4'te konumlandırılan MCP'nin **somut implementasyonu**. Bu bölüm, "Blender MCP'yi bağlayıp Gemini/ChatGPT/Claude ile kullanabilir miyim" sorusunun teknik cevabıdır.

### 13.1 MCP Server Registry

```python
# apps/gateway/src/mcp_orchestration/registry.py

class MCPServerRegistry:
    """
    Bir projeye bağlanan tüm MCP server'ları (Blender MCP, GitHub MCP,
    özel server'lar) yönetir. Üç bağlanma yolu destekler:

      1. Manuel: kullanıcı dashboard'dan connection_uri + transport girer
      2. .well-known keşif: Bölüm 4.3'teki MCP Server Cards standardı
         üzerinden otomatik metadata çekme
      3. Resmi MCP Registry: registry.modelcontextprotocol.io üzerinden
         arama/kurulum (Faz 2)

    Bağlantı kurulduğunda `tools/list` JSON-RPC çağrısı yapılıp
    mcp_tools tablosuna senkronize edilir (Bölüm 9.5).
    """

    async def connect(self, server_config: MCPServerConfig) -> MCPServer:
        client = await self._create_client(server_config)  # stdio/streamable_http/sse
        tools = await client.list_tools()
        await self._sync_tools_to_db(server_config.id, tools)
        return MCPServer(client=client, tools=tools)

    async def sync_all(self, project_id: UUID) -> None:
        """Periyodik arka plan görevi (Celery) — tüm bağlı server'ların
        tool listesini tazeler, yeni eklenen/kaldırılan araçları
        algılar."""
        ...
```

### 13.2 MCP Client Connection Pool

MCP bağlantıları (özellikle `stdio` transport — yerel süreç olarak çalışan server'lar, tipik olarak Blender MCP gibi) her istek için yeniden kurulmamalı; bağlantı havuzu (connection pool) ile yönetilmeli:

```python
# apps/gateway/src/mcp_orchestration/client_pool.py

class MCPClientPool:
    """
    Her mcp_server_id için tek bir kalıcı bağlantı tutar (stdio için
    bir alt-süreç, HTTP/SSE için bir kalıcı session). Bağlantı koptuğunda
    otomatik yeniden bağlanma (exponential backoff ile), sağlık kontrolü
    Routing Engine'deki devre kesiciyle AYNI deseni kullanır — kod
    tekrarını önlemek için circuit_breaker.py paylaşılan modül olarak
    kullanılır.
    """
    _pool: dict[UUID, MCPClientSession] = {}

    async def get_or_create(self, server_id: UUID) -> MCPClientSession: ...
    async def close_idle(self, idle_threshold_seconds: int = 300) -> None: ...
```

### 13.3 Şema Çeviri Katmanı — "Tek Tool Tanımı, Her Modelde Çalışır"

Bu, **projenin en yüksek özgünlük puanı alacak parçası**: MCP'nin tek tip `tools/list` JSON Schema çıktısını, hangi LLM seçilirse seçilsin o sağlayıcının kendi function-calling şemasına otomatik çevirir.

```python
# apps/gateway/src/mcp_orchestration/schema_translator.py

class MCPSchemaTranslator:
    """
    MCP Tool tanımı → sağlayıcıya özgü tool şeması.

    MCP formatı (kaynak, her zaman aynı):
      {"name": "...", "description": "...", "inputSchema": {JSON Schema}}

    Hedefler:
      - OpenAI:    {"type": "function", "function": {"name", "description", "parameters"}}
      - Anthropic: {"name", "description", "input_schema"}
      - Gemini:    {"functionDeclarations": [{"name", "description", "parameters"}]}

    Ve TERS yönde: model bir tool çağırdığında (her sağlayıcının kendi
    "tool_calls" / "tool_use" / "functionCall" formatında döndüğü yanıtı)
    tek tip bir ToolInvocation nesnesine normalize edip MCP'nin
    `tools/call` JSON-RPC isteğine çevirir, sonucu tekrar modele
    sağlayıcıya özgü "tool result" formatında geri besler.
    """

    def to_openai_format(self, mcp_tool: MCPTool) -> dict: ...
    def to_anthropic_format(self, mcp_tool: MCPTool) -> dict: ...
    def to_gemini_format(self, mcp_tool: MCPTool) -> dict: ...

    def parse_tool_invocation(
        self, provider_key: str, raw_tool_call: dict
    ) -> ToolInvocation:
        """Sağlayıcı yanıtındaki tool çağrısını normalize eder."""
        ...

    async def execute_via_mcp(self, invocation: ToolInvocation) -> ToolResult:
        """tool_calls tablosuna pending kaydı atar (Bölüm 9.5), MCP
        server'a tools/call gönderir, sonucu completed/failed olarak
        günceller ve ToolResult döner."""
        ...
```

### 13.4 Uçtan Uca Akış — "Blender'da Bir Sahne Oluştur" Örneği

Bu akış, demo videosunda **canlı gösterilecek** referans senaryodur:

```
1. Kullanıcı dashboard'daki Playground'dan Claude Opus seçer, mesaj yazar:
   "Blender'da kırmızı bir küp oluştur ve 45 derece döndür"
   Bu istekte mcp_servers=["blender-mcp"] belirtilmiştir.

2. API Gateway isteği alır → Routing Engine claude-opus-4-7 route'unu seçer.

3. İstek Provider Adapter'a gitmeden ÖNCE, MCP Orchestration katmanı
   blender-mcp'nin tool listesini çeker (mcp_tools tablosundan, cache'li)
   ve Schema Translator ile Anthropic formatına çevirip isteğe ekler.

4. Anthropic Adapter isteği Claude'a gönderir. Claude "bu görev için
   create_object ve rotate_object tool'larını çağırmam gerekiyor" diye
   karar verir ve tool_use bloklarıyla yanıt döner.

5. Gateway, tool_use bloklarını yakalar → Schema Translator bunları
   ToolInvocation'a çevirir → MCP Client Pool üzerinden Blender MCP
   server'a tools/call JSON-RPC isteği gönderilir (tool_calls tablosuna
   pending kaydı düşer).

6. Blender MCP, gerçek Blender uygulamasında küpü oluşturur, sonucu
   döner → tool_calls kaydı completed olur.

7. Sonuç tekrar Claude'a "tool result" formatında geri beslenir, Claude
   nihai doğal dil yanıtını üretir → kullanıcıya döner.

8. Dashboard'daki canlı istek-akışı görselleştirmesi (Bölüm 19.4) bu
   tüm zinciri gerçek zamanlı, animasyonlu bir graf olarak gösterir:
   Kullanıcı → Gateway → Claude → [tool call] → Blender MCP → Claude → Kullanıcı.
```

**Kritik nokta:** Bu akış GPT-4o veya Gemini seçilseydi de **birebir aynı** olurdu — sadece adım 3-4'teki şema çevirisi farklı sağlayıcı formatına giderdi. Kullanıcı/uygulama tarafında hiçbir kod değişikliği gerekmez. Bu, sorunun orijinal cevabıdır: **evet, tek bir app kurup Blender MCP'yi istediğin herhangi bir LLM ile (Gemini, ChatGPT, Claude, hatta yerel bir model) kullanabilirsin.**

### 13.5 A2A Hazırlığı (Faz 2+, Şimdi Sadece Mimari Yer Tutucu)

`apps/gateway/src/a2a/` klasörü MVP'de boş bırakılabilir ama `ProviderAdapter`'a benzer bir `AgentAdapter` soyut arayüzü tanımlanmalı — gelecekte bu sistemin kendisi bir A2A "Agent Card" yayınlayıp (`/.well-known/agent-card.json`), başka bir ajana (örn. senin otonom oyun geliştirme ajanın) görev devredebilmesi (task delegation) için. Bunu şimdiden implement etme — sadece arayüz/klasör iskeletini bırak.

---
## 14. AUTHENTICATION & KEY MANAGEMENT

### 14.1 Virtual Key Sistemi

Sistem, kullanıcının gerçek sağlayıcı API anahtarlarını (OpenAI key, Anthropic key vb.) **asla istemciye sızdırmaz**. Bunun yerine `virtual_keys` tablosunda tanımlı kendi anahtarlarını üretir (`pk_live_...` formatında), gerçek sağlayıcı kimlik bilgileri sadece sır yöneticisinde (Bölüm 7.4) ve backend'de yaşar.

```python
# apps/gateway/src/core/security.py

def generate_virtual_key() -> tuple[str, str, str]:
    """Döner: (ham_anahtar_kullanıcıya_gösterilecek, hash_db'ye_yazılacak, prefix_ui_önizleme)"""
    raw = f"pk_live_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    prefix = raw[:12] + "..."
    return raw, key_hash, prefix
```

**Kritik kural:** Ham anahtar sadece **oluşturulduğu anda bir kez** kullanıcıya gösterilir, bir daha asla geri çağrılamaz (GitHub Personal Access Token deseni). Veritabanında sadece hash tutulur.

### 14.2 Yetkilendirme Kapsamları (Scopes)

```
chat:write        → /v1/chat/completions, /v1/messages çağırabilir
embeddings:write   → /v1/embeddings çağırabilir
mcp:invoke         → MCP tool çağırabilir
admin:keys         → diğer virtual key'leri yönetebilir
admin:routing       → routing_policies değiştirebilir
admin:billing        → bütçe/fatura bilgisine erişebilir
```

### 14.3 Sağlayıcı Kimlik Bilgisi Yönetimi (BYOK Modeli)

Sistem "Bring Your Own Key" (BYOK) modeliyle çalışır — her organizasyon kendi sağlayıcı anahtarlarını ekler, sistem üzerinden geçen trafiğe komisyon almaz (Bölüm 3.2'deki LiteLLM'in "sıfır marj" felsefesinin benimsenmesi). Sağlayıcı kimlik bilgileri:

1. Dashboard'dan girilir → backend'e gönderilmeden önce TLS üzerinden iletilir
2. Backend, sır yöneticisine (Vault/Doppler) yazar, veritabanına sadece **referans** (`auth_credential_ref`) yazılır
3. Her sağlayıcı isteğinde, adapter bu referansı kullanarak çalışma zamanında sırrı çeker — sır asla log'lanmaz, asla `requests` tablosuna yazılmaz

---

## 15. OBSERVABILITY & COST TRACKING

### 15.1 Üç Sinyal Türü (OpenTelemetry Standardı)

| Sinyal | Araç | Ne İçin |
|---|---|---|
| **Traces** | OpenTelemetry SDK → Grafana Tempo | Bir isteğin Gateway→Routing→Provider→(varsa)MCP zincirindeki her adımın süresi; `requests.trace_id` ile veritabanı kaydından Tempo'daki tam trace'e tek tıkla gidilebilmeli |
| **Metrics** | Prometheus | RPS, p50/p95/p99 gecikme, route bazlı hata oranı, devre kesici durumları, aktif MCP bağlantı sayısı |
| **Logs** | Structured JSON logging → Loki | Hata detayları, guardrail ihlalleri, audit olayları |

### 15.2 Her İsteğin Trace Yapısı

```
span: gateway.request
 ├─ span: routing.select_route (strategy=semantic, duration=4ms)
 ├─ span: guardrails.check_input (duration=12ms)
 ├─ span: provider.anthropic.send (duration=780ms)
 │   └─ span: mcp.tool_call (server=blender-mcp, tool=create_object, duration=210ms)
 └─ span: billing.calculate_cost (duration=1ms)
```

### 15.3 Maliyet Hesaplama Doğruluğu

Maliyet (`requests.cost_usd_cents`), sağlayıcının yanıtında dönen **gerçek** `usage` bilgisine göre hesaplanır (tahmine göre değil — Bölüm 10.2'deki tahmin sadece routing kararı içindir). Hesaplama:

```python
def calculate_cost(route: ProviderRoute, input_tokens: int, output_tokens: int) -> Decimal:
    return (
        (Decimal(input_tokens) / 1_000_000) * route.pricing_input_per_million_cents
        + (Decimal(output_tokens) / 1_000_000) * route.pricing_output_per_million_cents
    )
```

Fiyatlandırma tablosu (`provider_routes.pricing_*`) statik değil — Faz 2'de sağlayıcıların resmi fiyatlandırma sayfalarını periyodik tarayan bir Celery görevi (`pricing_sync.py`) ile güncel tutulmalı; MVP'de manuel/seed migration yeterli.

---
## 16. CACHING KATMANI

### 16.1 İki Seviyeli Önbellekleme

| Seviye | Mekanizma | Kullanım Senaryosu |
|---|---|---|
| **Exact Cache** | Redis, `hash(normalized_request)` anahtarıyla tam eşleşme | Aynı prompt+parametre kombinasyonu tekrar geldiğinde (örn. test/CI ortamlarında) anında, sıfır maliyetli yanıt |
| **Semantic Cache** | `pgvector` (Bölüm 9.7), embedding kosinüs benzerliği | Anlamca aynı ama kelimesi kelimesine farklı promptlar için ("Python'da liste nasıl sıralanır" ≈ "Python'da bir listeyi nasıl sort ederim") |

### 16.2 Semantic Cache Akışı

```python
# apps/gateway/src/caching/semantic_cache.py

class SemanticCache:
    async def lookup(self, project_id: UUID, prompt: str) -> NormalizedResponse | None:
        embedding = await embed_text(prompt)
        # pgvector kosinüs mesafesi sorgusu, eşik altındaki en yakın kaydı bul
        result = await db.fetch_one("""
            SELECT response_payload, 1 - (prompt_embedding <=> :embedding) AS similarity
            FROM semantic_cache_entries
            WHERE project_id = :project_id AND expires_at > now()
            ORDER BY prompt_embedding <=> :embedding
            LIMIT 1
        """, {"embedding": embedding, "project_id": project_id})

        if result and result["similarity"] >= SIMILARITY_THRESHOLD:
            await self._increment_hit_count(result.id)
            return NormalizedResponse(**result["response_payload"], cache_hit=True)
        return None

    async def store(self, project_id: UUID, prompt: str, response: NormalizedResponse) -> None: ...
```

**Önemli güvenlik notu:** Semantic cache, kullanıcıya özel/hassas içerik barındıran promptlar için **proje bazında kapatılabilir** olmalı (`routing_policies.config.semantic_cache_enabled = false`) — özellikle PII içeren veya tek-seferlik (non-deterministic gereksinimli, örn. yaratıcı yazım) istekler için yanlış pozitif eşleşme riski vardır.

### 16.3 Önbellek Geçersizleştirme

`expires_at` alanı varsayılan olarak proje bazlı TTL ile ayarlanır (örn. 24 saat); ayrıca bir route'un fiyatlandırması veya model versiyonu değiştiğinde ilgili tüm cache kayıtları proaktif olarak temizlenmelidir (stale-data riski).

---

## 17. RATE LIMITING & BÜTÇE YÖNETİMİ

### 17.1 Token-Bucket Hız Sınırlama

```python
# Redis tabanlı token-bucket, virtual_keys.rate_limit_rpm alanına göre
# Lua script ile atomik kontrol (race condition'ı önlemek için)

RATE_LIMIT_LUA_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current > limit then return 0 else return 1 end
"""
```

### 17.2 Bütçe Uygulayıcı (Budget Enforcer)

```python
# apps/gateway/src/billing/budget_enforcer.py

class BudgetEnforcer:
    """
    Her istek ÖNCESİ (Routing Engine'den önce, API Gateway katmanında)
    çalışır: ay-içi toplam harcamayı Redis sayaçtan okur, budget_usd_cents
    aşılmışsa istek 402 Payment Required ile reddedilir, AŞILMADAN ÖNCE
    (örn. %80, %100 eşiklerinde) webhook/e-posta uyarısı tetiklenir.

    Tasarım kararı: Bütçe kontrolü "soft" (istek sonrası loglama) değil
    "hard" (istek öncesi engelleme) olmalı — aksi halde bir uygulama
    hatası gece yarısı binlerce dolarlık faturaya yol açabilir. Bu,
    Bölüm 5.3'teki "demo hilesi değil gerçek mühendislik" ilkesinin
    somut bir uygulamasıdır.
    """

    async def check_and_reserve(self, virtual_key: VirtualKey, estimated_cost: Decimal) -> None:
        current_spend = await self._get_month_to_date_spend(virtual_key.id)
        if virtual_key.budget_usd_cents and (current_spend + estimated_cost) > virtual_key.budget_usd_cents:
            raise BudgetExceededError(virtual_key.id, current_spend, virtual_key.budget_usd_cents)
```

### 17.3 Çoklu Seviye Limit Hiyerarşisi

Limitler hem `virtual_key` hem `project` hem `organization` seviyesinde tanımlanabilmeli ve **en kısıtlayıcı olan** geçerli olmalı — bu, Bölüm 6.4'teki çok-kiracılı modelin doğal bir uzantısıdır (örn. bir organizasyon aylık $500 tavanı koyarken, içindeki bir proje kendi içinde $50 ile sınırlandırılabilir).

---
## 18. GUARDRAILS & GÜVENLİK

> Bölüm 3.3'te belirtildiği gibi, Portkey'nin en güçlü farklılaştırıcısı 50+ guardrail seti. Bu projenin bu eksende **rakip seviyesine** ulaşması, "enterprise-ready" algısının en somut kanıtı.

### 18.1 Guardrail Pipeline Mimarisi

```python
# apps/gateway/src/guardrails/__init__.py

class GuardrailPipeline:
    """
    İstek hem GİRİŞTE (kullanıcı promptu modele gitmeden önce) hem
    ÇIKIŞTA (model yanıtı kullanıcıya dönmeden önce) bu pipeline'dan
    geçer. Her guardrail bağımsız bir modül, sırayla çalıştırılır,
    biri 'block' kararı verirse zincir durur.
    """

    stages: list[GuardrailCheck] = [
        PIIRedactionCheck(),
        JailbreakDetectionCheck(),
        ContentPolicyCheck(),
    ]

    async def run_input_checks(self, request: NormalizedRequest, policy: GuardrailPolicy) -> GuardrailResult:
        for check in self.stages:
            if not policy.is_enabled(check.name):
                continue
            result = await check.evaluate(request.last_user_message)
            await self._log_violation_if_any(result)
            if result.action == "block":
                raise GuardrailBlockedError(check.name, result.detail)
            if result.action == "redact":
                request = check.apply_redaction(request, result)
        return GuardrailResult.passed()
```

### 18.2 PII Redaksiyonu

```python
# apps/gateway/src/guardrails/pii_redaction.py

class PIIRedactionCheck(GuardrailCheck):
    """
    Regex + adlandırılmış varlık tanıma (NER) hibrit yaklaşımı:
      - Yüksek güvenilirlikli desenler (e-posta, kredi kartı, TC kimlik
        no, telefon) için regex — hızlı, deterministik
      - Daha belirsiz varlıklar (kişi adı, adres) için hafif bir NER
        modeli (örn. spaCy küçük model, çıkarım maliyeti düşük tutulmalı)
    Tespit edilen PII, modele gitmeden ÖNCE [REDACTED:EMAIL] gibi
    placeholder'larla değiştirilir; orijinal değer-placeholder eşlemesi
    geçici olarak Redis'te (kısa TTL ile) tutulur, böylece model yanıtı
    döndüğünde placeholder'lar GERİ orijinal değerlere çevrilebilir
    (kullanıcı deneyimi bozulmaz, ama sağlayıcıya asla ham PII gitmez).
    """
    name = "pii"
    async def evaluate(self, text: str) -> GuardrailCheckResult: ...
```

### 18.3 Jailbreak Tespiti

```python
# apps/gateway/src/guardrails/jailbreak_detector.py

class JailbreakDetectionCheck(GuardrailCheck):
    """
    Bilinen jailbreak kalıplarına (rol-yapma istismarı, "önceki
    talimatları yok say" türü promptlar, karakter-kaçışlı encoding
    saldırıları) karşı imza-tabanlı + embedding-benzerlik-tabanlı hibrit
    tespit. Tespit edilirse 'flag' (loglanır, izin verilir) veya 'block'
    (politikaya göre) kararı verir — varsayılan politika 'flag', kurumsal
    kullanım için 'block' önerilir.
    """
    name = "jailbreak"
```

### 18.4 Diğer Güvenlik Gereksinimleri (Checklist)

- **Sır yönetimi:** Hiçbir API anahtarı/sağlayıcı kimlik bilgisi kod tabanında, log'larda veya veritabanında düz metin olarak bulunmamalı (Bölüm 14.3).
- **Transport güvenliği:** Tüm dış iletişim TLS 1.3; iç servisler arası iletişim (gateway↔Redis, gateway↔PostgreSQL) mTLS ile (production profilinde).
- **Girdi doğrulama:** Her endpoint Pydantic şemasıyla sıkı doğrulama; rastgele büyük payload'lara karşı boyut limiti (örn. 10MB).
- **Bağımlılık güvenliği:** `pip-audit` / `npm audit` CI pipeline'ında zorunlu adım (Bölüm 20.3).
- **MCP server güveni:** Bölüm 13'teki MCP server bağlantıları, varsayılan olarak **izin listesi (allowlist)** prensibiyle çalışmalı — bilinmeyen/doğrulanmamış bir MCP server'a otomatik güvenilmemeli; dashboard'da her yeni server bağlantısı için açık onay istenmeli (tool poisoning saldırılarına karşı temel savunma).
- **Audit trail:** Bölüm 9.6'daki `audit_log` tablosu, kim/ne zaman/hangi anahtarı oluşturdu, hangi route'u devre dışı bıraktı gibi her yönetimsel eylemi değişmez (immutable) şekilde kaydetmeli.

---
## 19. ADMIN DASHBOARD / FRONTEND TASARIM SİSTEMİ

> Bu bölüm Awwards "Design" ve "Creativity" eksenlerinin doğrudan karşılığıdır (Bölüm 5.1). Hedef: "yönetici paneli" değil, **command-center** hissi veren bir ürün.

### 19.1 Tokyo Night Renk Token Sistemi

```css
/* apps/dashboard/styles/tokyo-night-tokens.css */

:root {
  /* Zemin katmanları — düz siyah DEĞİL, mor-mavi tonlu derinlik */
  --bg-base:        #1a1b26;
  --bg-elevated-1:  #1f2335;   /* kartlar */
  --bg-elevated-2:  #24283b;   /* modal/popover */
  --bg-elevated-3:  #2a2e42;   /* hover durumları */
  --border-subtle:  #2f3549;
  --border-strong:  #3b4261;

  /* Metin */
  --text-primary:    #c0caf5;
  --text-secondary:  #9aa5ce;
  --text-muted:      #565f89;

  /* Vurgu renkleri — her biri bir ANLAM taşır, rastgele dekoratif değil */
  --accent-blue:    #7aa2f7;  /* birincil eylemler, bağlantılar */
  --accent-cyan:    #7dcfff;  /* bilgi/canlı veri akışı */
  --accent-green:   #9ece6a;  /* başarı, sağlıklı route */
  --accent-yellow:  #e0af68;  /* uyarı, %80 bütçe eşiği */
  --accent-orange:  #ff9e64;  /* fallback tetiklendi */
  --accent-red:     #f7768e;  /* hata, devre kesici OPEN */
  --accent-magenta: #bb9af7;  /* MCP/araç çağrıları (kendine özgü kategori) */
  --accent-teal:    #73daca;  /* önbellek isabeti (cache hit) */

  /* Glassmorphism katmanı */
  --glass-bg:       rgba(36, 40, 59, 0.65);
  --glass-border:   rgba(122, 162, 247, 0.12);
  --glass-blur:     16px;

  /* Gölge/elevation — Tokyo Night'ta gölgeler mor-tonlu olmalı, siyah değil */
  --shadow-sm: 0 2px 8px rgba(26, 27, 38, 0.4);
  --shadow-md: 0 8px 24px rgba(26, 27, 38, 0.5), 0 0 0 1px var(--glass-border);
  --shadow-glow-blue: 0 0 24px rgba(122, 162, 247, 0.25);
}
```

### 19.2 Tipografi

| Kullanım | Yazı Tipi | Gerekçe |
|---|---|---|
| Başlıklar / UI metni | **Geist Sans** veya **Inter** (variable font) | Yüksek okunabilirlik, geniş ağırlık aralığı |
| Sayısal veri (maliyet, gecikme, token sayıları) | **JetBrains Mono** veya **Geist Mono** | Tabular figures — sayılar hizalı dizilir, dashboard'da kritik |
| Kod blokları (request/response gövdeleri) | **JetBrains Mono** | Syntax highlighting ile Tokyo Night renk paletinin orijinal kaynağı |

**Kural:** Tüm sayısal metrikler (maliyet, ms, token) **mono font + tabular-nums** ile render edilmeli — bu, "demo görünümlü" ile "ürün görünümlü" dashboard arasındaki en hızlı fark edilen detaylardan biridir.

### 19.3 8pt Grid ve Bileşen Tutarlılığı

Tüm spacing değerleri 8'in katları olmalı (4px sadece ikon-içi mikro boşluklar için istisna). Bileşen kütüphanesi `shadcn/ui` temelinde inşa edilip yukarıdaki token'larla **tamamen** override edilmeli — varsayılan shadcn açık/koyu temasının "demo görünümü" asla kalmamalı.

### 19.4 İmza Özellik: Canlı İstek-Akışı Görselleştirmesi

Bu, Bölüm 5.1'deki "Creativity" ekseninin somut karşılığı ve demo videosunun merkez sahnesi:

```
apps/dashboard/components/flow-visualization/RequestFlowGraph.tsx
```

**Tasarım:** D3.js force-directed graph veya özel SVG path animasyonu ile, ekranda şu düğümler sabit konumlandırılır: `[İstemci] → [Gateway] → [Routing Engine] → [Sağlayıcılar (çoklu düğüm)] → (varsa) [MCP Server'lar]`. Her gerçek istek geldiğinde (`WS /v1/live` üzerinden), bu yol boyunca **akan bir parçacık animasyonu** (Framer Motion `animate` + SVG `<motion.circle>` path takibi) gerçek zamanlı oynatılır:

- Parçacığın rengi, kullanılan route'un sağlayıcısına göre değişir (Bölüm 19.1 vurgu renkleri)
- Fallback tetiklenirse parçacık turuncu yanıp söner ve alternatif yola sapar (görsel olarak "neden fallback oldu" anlaşılır)
- Cache hit ise parçacık Gateway'den hiç ötesine geçmez, teal renginde "sektirerek" geri döner — bunun maliyet tasarrufu olduğu görsel olarak hemen anlaşılır
- MCP tool çağrısı varsa, ana yoldan sapan magenta renkli ikincil bir dal animasyonla gösterilir (Bölüm 13.4'teki Blender örneği canlı izlenebilir)

Bu bileşen, jüri sunumunda **30 saniyede sistemin ne yaptığını anlatan** en güçlü tek görsel olacaktır.

### 19.5 Komut Paleti (Cmd+K)

`kbar` veya benzeri bir kütüphane ile her yönetimsel eylem (yeni virtual key oluştur, route'u devre dışı bırak, MCP server bağla, playground'a git) klavye-öncelikli komut paletinden erişilebilir olmalı — Awwards "Usability" ekseni için somut, hızlı fark edilen bir detay.

### 19.6 Boş Durumlar ve Hata Mesajları (Content Ekseni)

Her boş durum bağlamsal bir eylem önerir, asla düz "veri yok" demez:

- Hiç MCP server bağlanmamışsa: "Henüz bir araç bağlamadın. Blender, GitHub veya kendi özel MCP server'ını bağlayarak başla →"
- Hiç istek atılmamışsa: "İlk isteğini Playground'dan gönder veya SDK ile entegre et →"

Her hata mesajı üç parçalıdır: **ne oldu** (insan dilinde), **neden oldu** (teknik kök neden), **şimdi ne yapmalısın** (somut sonraki adım) — generic "Bir hata oluştu" asla kabul edilmez.

---
## 20. DEPLOYMENT MİMARİSİ

### 20.1 Tek Komutla Yerel Kalkış

```yaml
# infra/docker-compose.yml — geliştirme ortamı, tek komutla ayağa kalkmalı: `docker compose up`
services:
  postgres:
    image: pgvector/pgvector:pg16   # pgvector eklentisi önceden gömülü imaj
    environment:
      POSTGRES_DB: gateway
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  gateway:
    build: ../apps/gateway
    depends_on: [postgres, redis]
    env_file: .env
    ports: ["8000:8000"]

  dashboard:
    build: ../apps/dashboard
    depends_on: [gateway]
    ports: ["3000:3000"]

  otel-collector:
    image: otel/opentelemetry-collector-contrib
  prometheus:
    image: prom/prometheus
  grafana:
    image: grafana/grafana
  tempo:
    image: grafana/tempo

volumes:
  pgdata:
```

### 20.2 Production Dağıtım Seçenekleri (Esneklik = Farklılaştırıcı)

Bölüm 3.5'teki "platform kilidi" zaafından kaçınmak için sistem üç bağımsız dağıtım yolunu desteklemeli, hepsi aynı Docker imajlarından türetilmeli:

1. **Tek VPS/Docker Compose** — bireysel geliştirici/küçük proje kullanımı (senin diğer projelerin için birincil senaryo)
2. **Kubernetes (Helm chart)** — `infra/k8s/` altında, yatay ölçeklenebilirlik gereken senaryolar için (Gateway servisi stateless tasarlandığı için — Bölüm 6.3 — yatay ölçekleme sorunsuz olmalı)
3. **Managed bulut (opsiyonel SaaS modu)** — gelecekte bunu bir ürüne dönüştürme senaryosu için Terraform modülleri (`infra/terraform/`)

### 20.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml — sıralı zorunlu adımlar
# 1. lint (ruff + eslint)            5. integration test (gerçek Postgres/Redis container'larıyla)
# 2. type-check (mypy + tsc)         6. pip-audit / npm audit (güvenlik taraması)
# 3. unit test (pytest + vitest)     7. Docker imaj build + boyut/güvenlik taraması (trivy)
# 4. OpenAPI şema → TS tip üretimi    8. (main branch'e merge'de) otomatik deploy
```

Her PR, yukarıdaki sekiz adımdan **hepsini** geçmeden merge edilemez (branch protection rule) — bu, Bölüm 5.3'teki "bitmişlik" iddiasının CI'da zorunlu kılınmış halidir.

---

## 21. TEST STRATEJİSİ

### 21.1 Test Piramidi

| Seviye | Kapsam | Araç |
|---|---|---|
| **Unit** | Her routing stratejisi, her adapter'ın `normalize_request`/`normalize_response` metodu, guardrail kontrolleri — sağlayıcılara gerçek ağ çağrısı YAPILMADAN, mock yanıtlarla | pytest + pytest-asyncio |
| **Integration** | Routing Engine + Provider Registry + gerçek PostgreSQL/Redis (test container'ları) birlikte; sağlayıcı API'leri yine mock (VCR.py kayıt/oynatma deseni ile gerçekçi yanıt fixture'ları) | pytest + testcontainers + VCR.py |
| **Contract** | Her adapter için, sağlayıcının gerçek API şemasıyla **kayıt edilmiş** (cassette) gerçek yanıt örnekleri üzerinden şema doğrulama — sağlayıcı API'si değiştiğinde bu testler kırılarak erken uyarı verir | pytest + Pydantic doğrulama |
| **E2E** | Bölüm 13.4'teki Blender senaryosu gibi tam uçtan uca akışlar, gerçek (veya sandbox) sağlayıcı çağrılarıyla, CI'da sadece nightly/manuel tetiklenir (maliyet nedeniyle her PR'da değil) | pytest + gerçek test API anahtarları (CI secret) |
| **Frontend** | Bileşen testleri + kritik kullanıcı akışları (key oluşturma, MCP server bağlama, playground mesaj gönderme) | Vitest + Playwright |
| **Yük testi** | Bölüm 6.3'teki p95 < 15ms gateway ek-gecikme hedefinin doğrulanması | k6 veya Locust |

### 21.2 Minimum Kabul Kriteri

Hiçbir modül, ilgili `tests/unit/` dosyası **olmadan** "tamamlandı" sayılamaz. Routing Engine ve Provider Adapter katmanı için kod kapsamı (coverage) hedefi **%85+** olmalı — bu, jüri/kod-inceleyici için `pytest --cov` çıktısının README'de gösterilebilir bir kanıt olmasını sağlar.

---

## 22. DOKÜMANTASYON GEREKSİNİMLERİ

| Doküman | İçerik |
|---|---|
| `README.md` | Vizyon (Bölüm 1), mimari diyagram (Bölüm 6.1), 5 dakikada kurulum, demo GIF/video bağlantısı, lisans |
| `docs/architecture/*.md` | Her büyük mimari karar için ADR formatı: **Bağlam → Karar → Sonuçlar → Alternatifler** (örn. "Neden PostgreSQL+pgvector, neden ayrı bir vektör DB değil") |
| `docs/api-reference/` | OpenAPI spec'ten otomatik üretilen (Redoc veya Scalar ile render edilen) interaktif API dokümantasyonu |
| `docs/adding-a-provider.md` | Bölüm 11.4'teki checklist'in genişletilmiş, adım adım rehberi — yeni katkıda bulunanlar için |
| `CLAUDE.md` | Bölüm 25'teki kod kalite kuralları, AI kod asistanlarının projeye katkı yaparken uyacağı kurallar |

---
## 23. FAZ BAZLI YOL HARİTASI

> AI ajanı bu sırayı **değiştirmeden** takip etmeli. Her faz sonunda "Checkpoint Kriteri" karşılanmadan bir sonraki faza geçilmez.

### FAZ 0 — Temel İskelet (1. hafta)
- Monorepo yapısı (Bölüm 8) oluşturulur, boş ama çalışan FastAPI + Next.js iskeletleri
- PostgreSQL şeması (Bölüm 9) migration olarak yazılır, Docker Compose ile yerel kalkış çalışır
- CI pipeline'ın lint/type-check/unit-test adımları (henüz testsiz de olsa) çalışır durumda
- **Checkpoint:** `docker compose up` tek komutla tüm servisler ayağa kalkar, `/health` endpoint'i 200 döner

### FAZ 1 — Çekirdek Routing + 3 Sağlayıcı (2-3. hafta)
- Provider Adapter arayüzü (Bölüm 11.1) + OpenAI, Anthropic, Google adapter'ları
- Routing Engine: sadece Cost-Based ve Latency-Based stratejiler (10.2, 10.3)
- Devre kesici + fallback zinciri (10.6, 10.7)
- `/v1/chat/completions` endpoint'i uçtan uca çalışır, streaming dahil
- Unit + integration testler bu üç adapter için %85+ kapsamla
- **Checkpoint:** Aynı isteği üç farklı sağlayıcıya, tek bir API çağrısıyla, fallback ile gönderebiliyorsun — canlı demo edilebilir

### FAZ 2 — MCP Entegrasyonu (4-5. hafta)
- MCP Server Registry + Client Pool (13.1, 13.2)
- Schema Translator (13.3) — en az iki sağlayıcı formatına çeviri (OpenAI + Anthropic)
- Blender MCP ile uçtan uca entegrasyon testi (13.4 senaryosu canlı çalışır halde)
- `tool_calls` tablosu ve durum makinesi tam işlevsel
- **Checkpoint:** Bölüm 13.4'teki "Blender'da küp oluştur" senaryosu, dashboard'da canlı izlenebilir şekilde çalışır

### FAZ 3 — Genişletilmiş Sağlayıcı Kataloğu + Bulut Hyperscaler'lar (6-7. hafta)
- AWS Bedrock, Azure OpenAI, Vertex AI adapter'ları (11.5'teki özel auth akışlarıyla)
- DeepSeek, OpenRouter, en az bir yerel (Ollama) adapter
- Semantic Routing stratejisi (10.4)
- **Checkpoint:** En az 10 farklı `provider_key` aktif ve test edilmiş durumda

### FAZ 4 — Guardrails, Caching, Bütçe (8. hafta)
- PII redaksiyonu, jailbreak tespiti (Bölüm 18)
- Semantic + exact cache (Bölüm 16)
- Bütçe uygulayıcı + rate limiting (Bölüm 17)
- **Checkpoint:** Bütçe aşıldığında istek gerçekten 402 ile reddediliyor, cache hit oranı dashboard'da görünür

### FAZ 5 — Dashboard Cilası ve Awwards Hazırlığı (9-10. hafta)
- Tokyo Night tasarım sistemi tam uygulanır (Bölüm 19)
- Canlı istek-akışı görselleştirmesi (19.4) — bu fazın en kritik teslimat kalemi
- Komut paleti, boş durumlar, hata mesajları cilası
- Erişilebilirlik denetimi (axe-core ile otomatik tarama + manuel klavye gezinme testi)
- **Checkpoint:** Lighthouse skorları Performance/Accessibility/Best Practices üçünde 90+

### FAZ 6 — Gözlemlenebilirlik, Yük Testi, Belgeleme (11-12. hafta)
- OpenTelemetry + Grafana yığını tam entegre
- k6 ile yük testi, p95 gecikme bütçesi (Bölüm 6.3) doğrulanır
- Tüm dokümantasyon (Bölüm 22) tamamlanır
- Demo videosu senaryosu çekilir (90 saniye, Bölüm 5.2)
- **Checkpoint:** README'deki kurulum adımlarını sıfırdan, hiç yardım almadan takip eden biri 10 dakikada sistemi ayağa kaldırabiliyor

### MVP Kapsam Sınırı (Net Çizgi)

MVP = Faz 0 → Faz 5 tamamlandığında biter. Faz 2'deki Learned Routing (10.5) ve A2A entegrasyonu (13.5) **MVP kapsamı DIŞINDADIR** — bunlar "gelecek vizyonu" olarak README'de "Roadmap" başlığı altında belirtilir, jüriye "bunun ötesini de düşündük ama kapsamı bilinçli sınırladık" mesajı verir; bu, kapsam disiplininin kendisi bir olgunluk göstergesidir.

---
## 24. ÖDÜL / YARIŞMA KRİTERLERİ — SON KONTROL LİSTESİ

> Teslimattan önce bu listenin **her maddesi** işaretlenebilir olmalı. Bu liste hem Awwards başvurusu hem yazılım yarışması başvurusu için ortak kontrol noktasıdır.

**Teknik Derinlik**
- [ ] En az 10 farklı LLM sağlayıcısı/yolu gerçekten çalışır durumda (mock değil)
- [ ] En az 3 farklı routing stratejisi canlı demo edilebilir
- [ ] Devre kesici + fallback zinciri, bir sağlayıcı kasıtlı kapatıldığında canlı gösterilebilir
- [ ] MCP entegrasyonu en az bir gerçek dış araçla (Blender veya GitHub) uçtan uca çalışır
- [ ] Kod kapsamı (coverage) raporu README'de görünür ve %85+

**Görsel / UX Zanaatkarlığı**
- [ ] Tokyo Night tasarım sistemi tutarlı şekilde tüm ekranlarda uygulanmış
- [ ] Canlı istek-akışı görselleştirmesi sorunsuz, gerçek veriyle çalışıyor
- [ ] Lighthouse Performance/Accessibility/Best Practices skorları 90+
- [ ] Klavye-öncelikli gezinme (komut paleti) tam işlevsel
- [ ] Mobil/tablet genişliklerinde dashboard kırılmıyor (en azından salt-okunur görünüm)

**Bitmişlik ve Güvenilirlik**
- [ ] Hiçbir "TODO" veya placeholder kod ana akışta (happy path) kalmamış
- [ ] Hata durumları UI'da sessizce yutulmuyor, anlamlı mesajlarla gösteriliyor
- [ ] `docker compose up` sıfırdan, dokümantasyon dışında yardım almadan çalışıyor
- [ ] CI pipeline'ın tüm adımları yeşil

**Sunum Materyali**
- [ ] 90 saniyelik demo videosu (Bölüm 13.4 senaryosu merkezde)
- [ ] Mimari diyagram (Bölüm 6.1'in cilalı/tasarlanmış versiyonu — Figma/Excalidraw çıktısı)
- [ ] README'de somut "gerçek kullanım" anlatısı (kendi diğer projelerinde nasıl kullanıldığı)
- [ ] Awwards başvuru formatına uygun ekran görüntüleri (1920x1080, retina)

**Anlatı / Konumlandırma**
- [ ] Bölüm 3.7'deki rekabet matrisinin güncellenmiş, gerçek veriyle desteklenmiş hali sunum materyalinde var
- [ ] "Neden bu proje var" sorusu tek cümlede (Bölüm 1.1) net şekilde iletilebiliyor

---

## 25. KOD KALİTE STANDARTLARI (CLAUDE.md İçeriği)

> Bu bölümün içeriği, proje kök dizinindeki `CLAUDE.md` dosyasına **birebir** yazılmalı — gelecekte bu projeye herhangi bir AI kod asistanıyla (Claude Code, Cursor vb.) katkı yapıldığında bu kurallar otomatik uygulanır.

```markdown
# CLAUDE.md — [PROJE_ADI] Kod Kalite Kuralları

## Genel İlkeler
- Her yeni sağlayıcı adapter'ı Bölüm 11.1'deki ProviderAdapter arayüzünü
  EKSİKSİZ implement etmeli — kısmi implementasyon kabul edilmez.
- Routing/Provider/MCP/Guardrails katmanları birbirinin iç detayını
  BİLMEMELİ — sadece tanımlı arayüzler üzerinden konuşur (Bölüm 6.2).
- Hiçbir sağlayıcı kimlik bilgisi, log satırına veya hata mesajına
  yazılmamalı (otomatik secret-scanning pre-commit hook'u zorunlu).

## Python (Backend)
- Tip ipuçları zorunlu, `mypy --strict` CI'da kırmızı geçemez.
- Asenkron kod tabanında ASLA bloklayıcı (senkron) I/O kullanılmaz
  (Bölüm 6.3'teki gecikme bütçesi nedeniyle).
- Her yeni modül için ilgili `tests/unit/` dosyası AYNI PR'da gelir.
- Hata sınıfları `core/exceptions.py`'de merkezi tanımlanır, generic
  `Exception` fırlatılmaz.

## TypeScript (Frontend)
- `strict: true`, `any` kullanımı lint kuralıyla engellenir.
- Tüm API tipleri backend OpenAPI şemasından OTOMATİK üretilir, elle
  tip tanımlanmaz (tek doğruluk kaynağı backend Pydantic modelleri).
- Tasarım token'ları (Bölüm 19.1) DIŞINDA hardcoded renk/spacing değeri
  kullanılmaz.

## Commit / PR Disiplini
- Conventional Commits formatı (`feat:`, `fix:`, `refactor:`, `docs:`).
- Her PR, ilgili Bölüm numarasına referans verir (örn. "Bölüm 10.4
  devre kesici implementasyonu").
- Mimari etkisi olan her PR, `docs/architecture/`'a bir ADR ekler.
```

---
## 26. SON TALİMAT — BU PROMPT'U AI KOD ÜRETİM ARACINA NASIL VERMELİSİN

### 26.1 Kullanım Talimatı

1. Bu dokümanın tamamını (Bölüm 0'dan buraya kadar) tek seferde AI kod üretim aracına yapıştır (Claude Code, Cursor, Windsurf, Codex CLI — hepsi büyük context pencereli, tamamı sığar).
2. İlk mesajında şunu ekle: *"Bu dokümanı oku, Bölüm 23'teki Faz 0'dan başla, her checkpoint'i benimle paylaş, onay almadan bir sonraki faza geçme."*
3. `[PROJE_ADI]` placeholder'ını dokümanın TAMAMINDA (find&replace) gerçek proje adınla değiştir — aşağıda öneriler var.
4. Her faz bitiminde, ilgili Checkpoint Kriteri'ni (Bölüm 23) sen doğrula, sonra "devam et" de.

### 26.2 AI Ajanına Ek Davranış Kuralları

```
- Eğer bu dokümanda bir çelişki veya teknik olarak uygulanamaz bir nokta
  bulursan, sessizce kendi yorumunla devam ETME — açıkça belirt ve
  alternatif öner, sonra onay bekle.
- Eğer bir fazı bitirmeden context penceren dolmaya yaklaşırsa, o ana
  kadar yapılanların özetini ve kaldığın noktayı net şekilde yaz, ki
  yeni bir oturumda kaldığın yerden devam edilebilsin.
- "Çalışıyor görünüyor" ile "test edilmiş ve çalışıyor" arasındaki farkı
  asla bulanıklaştırma — bir özelliği test etmeden "tamamlandı" deme.
- Sahte/mock veri içeren hiçbir ekran görüntüsünü veya demoyu "gerçek"
  olarak sunma; mock kullanıyorsan bunu açıkça belirt.
```

### 26.3 Proje İsmi Önerileri (Placeholder İçin)

Senin marka dilin (Pulse, Forge, Aether, Senfoni, Whirl tarzı — tek kelime, çağrışımlı, telaffuzu kolay) ile uyumlu, bu projenin "evrensel bağlantı/yönlendirme" temasına oturan öneriler — zorunlu değil, kendi seçimin esas:

| Öneri | Çağrışım |
|---|---|
| **Nexus** *(dikkat: bu isim senin Nexus AI UE5 projende zaten kullanılıyor — çakışmaması için farklı bir isim önerilir)* | — |
| **Conduit** | Akan, birleştiren kanal |
| **Meridian** | Tüm hatların kesiştiği referans noktası |
| **Lattice** | Birbirine bağlı, yapısal ağ |
| **Vortex** | Whirl'e yakın ama farklı bir projede — çoklu kaynağı tek noktada toplama |
| **Axiom** | Temel, üzerine inşa edilen sağlam zemin |
| **Helix** | Çoklu iplikçiğin (sağlayıcıların) tek sarmalda birleşmesi |
| **Polaris** | Yön gösteren sabit nokta — "her zaman doğru modele yönlendirir" |

### 26.4 Kapanış Notu

Bu doküman, bir sistemin **nasıl inşa edileceğini** tarif ediyor — ama Bölüm 5.2'deki jüri kriterlerinin gerçekten karşılanması, fazların **gerçekten tek tek, atlamadan, test edilerek** tamamlanmasına bağlı. En büyük risk, Faz 0-1'in heyecanla hızlı bitirilip Faz 5-6'nın (cila, test, dokümantasyon — yani jürinin gerçekte gördüğü kısım) aceleye getirilmesi. Zaman bütçeni tersine ayır: teknik çekirdeğe (Faz 0-3) toplam sürenin %50'sini, cila+güvenilirlik+sunuma (Faz 4-6) diğer %50'sini ayır.

**Başarılar — bu gerçekten ödül alabilecek bir proje fikri, eksik olan şey artık sadece disiplinli uygulama.**

---
