use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

// ═══════════════════════════════════════════════════════════════
// GATEWAY CLIENT - Patchbay Gateway API Integration
// ═══════════════════════════════════════════════════════════════

#[derive(Clone)]
pub struct GatewayClient {
    base_url: String,
    client: Client,
}

// ─── Request Types ───

#[derive(Debug, Serialize)]
pub struct ChatCompletionRequest {
    pub model: String,
    pub messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stream: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
}

// ─── Response Types ───

#[derive(Debug, Deserialize)]
pub struct ChatCompletionResponse {
    pub id: Option<String>,
    pub choices: Option<Vec<Choice>>,
    pub usage: Option<Usage>,
    pub gateway_metadata: Option<GatewayMetadata>,
}

#[derive(Debug, Deserialize)]
pub struct Choice {
    pub index: Option<u32>,
    pub message: Option<ChatMessage>,
    pub delta: Option<Delta>,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Delta {
    pub content: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Usage {
    pub prompt_tokens: Option<u32>,
    pub completion_tokens: Option<u32>,
    pub total_tokens: Option<u32>,
}

#[derive(Debug, Deserialize)]
pub struct GatewayMetadata {
    pub selected_route: Option<String>,
    pub routing_strategy: Option<String>,
    pub cache_hit: Option<bool>,
    pub cost_usd_cents: Option<f64>,
    pub latency_ms: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct ModelsResponse {
    pub data: Vec<ModelInfo>,
}

#[derive(Debug, Deserialize)]
pub struct ModelInfo {
    pub id: String,
    #[serde(default)]
    pub owned_by: String,
    #[serde(default)]
    pub patchbay: Option<ModelCapabilities>,
}

#[derive(Debug, Deserialize)]
pub struct ModelCapabilities {
    pub family: Option<String>,
    pub context_window: Option<u32>,
    pub max_output_tokens: Option<u32>,
    pub supports_vision: Option<bool>,
    pub supports_tools: Option<bool>,
    pub supports_streaming: Option<bool>,
}

#[derive(Debug, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: Option<String>,
    pub latency_ms: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct UsageResponse {
    pub total_requests: Option<u32>,
    pub total_cost_usd_cents: Option<f64>,
    pub total_input_tokens: Option<u64>,
    pub total_output_tokens: Option<u64>,
    pub avg_latency_ms: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct ErrorResponse {
    pub detail: Option<String>,
}

// ─── Stream Events ───

pub enum StreamEvent {
    Text(String),
    Done(Option<Usage>),
    Error(String),
}

impl GatewayClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_default(),
        }
    }

    // ─── Health Check ───

    pub async fn health(&self) -> Result<HealthResponse> {
        let url = format!("{}/health", self.base_url);
        let resp = self.client.get(&url).send().await?.json().await?;
        Ok(resp)
    }

    // ─── List Models ───

    pub async fn list_models(&self) -> Result<Vec<ModelInfo>> {
        let url = format!("{}/v1/models", self.base_url);
        let resp: ModelsResponse = self.client.get(&url).send().await?.json().await?;
        Ok(resp.data)
    }

    // ─── Chat Completion (non-streaming) ───

    pub async fn chat_completion(
        &self,
        model: &str,
        messages: Vec<ChatMessage>,
        temperature: Option<f32>,
        max_tokens: Option<u32>,
    ) -> Result<ChatCompletionResponse> {
        let url = format!("{}/v1/chat/completions", self.base_url);
        let body = ChatCompletionRequest {
            model: model.to_string(),
            messages,
            stream: Some(false),
            temperature,
            max_tokens,
        };
        let resp = self.client.post(&url).json(&body).send().await?.json().await?;
        Ok(resp)
    }

    // ─── Chat Completion (streaming) ───

    pub async fn stream_completion(
        &self,
        model: &str,
        messages: Vec<ChatMessage>,
        temperature: Option<f32>,
        max_tokens: Option<u32>,
        tx: mpsc::UnboundedSender<StreamEvent>,
    ) -> Result<()> {
        let url = format!("{}/v1/chat/completions", self.base_url);
        let body = ChatCompletionRequest {
            model: model.to_string(),
            messages,
            stream: Some(true),
            temperature,
            max_tokens,
        };

        let response = self.client.post(&url).json(&body).send().await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            let error_msg = if let Ok(err) = serde_json::from_str::<ErrorResponse>(&text) {
                err.detail.unwrap_or(text)
            } else {
                text
            };
            let _ = tx.send(StreamEvent::Error(format!("HTTP {}: {}", status, error_msg)));
            return Ok(());
        }

        let mut buffer = String::new();
        let mut bytes = response.bytes_stream();

        use futures_util::StreamExt;
        while let Some(chunk_result) = bytes.next().await {
            match chunk_result {
                Ok(chunk) => {
                    buffer.push_str(&String::from_utf8_lossy(&chunk));

                    while let Some(newline_pos) = buffer.find('\n') {
                        let line = buffer[..newline_pos].trim().to_string();
                        buffer = buffer[newline_pos + 1..].to_string();

                        if line.is_empty() {
                            continue;
                        }

                        if line == "data: [DONE]" {
                            let _ = tx.send(StreamEvent::Done(None));
                            return Ok(());
                        }

                        if let Some(data) = line.strip_prefix("data: ") {
                            if let Ok(chunk) = serde_json::from_str::<serde_json::Value>(data) {
                                // Extract usage from chunk if present
                                let usage = chunk.get("usage").and_then(|u| {
                                    serde_json::from_value::<Usage>(u.clone()).ok()
                                });

                                if let Some(choices) = chunk.get("choices") {
                                    if let Some(choice) = choices.get(0) {
                                        // Handle delta (streaming)
                                        if let Some(delta) = choice.get("delta") {
                                            if let Some(content) = delta.get("content") {
                                                if let Some(text) = content.as_str() {
                                                    if !text.is_empty() {
                                                        let _ = tx.send(StreamEvent::Text(text.to_string()));
                                                    }
                                                }
                                            }
                                        }
                                        // Handle finish_reason
                                        if let Some(reason) = choice.get("finish_reason") {
                                            if !reason.is_null() {
                                                let _ = tx.send(StreamEvent::Done(usage));
                                                return Ok(());
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Err(e) => {
                    let _ = tx.send(StreamEvent::Error(e.to_string()));
                    return Ok(());
                }
            }
        }

        let _ = tx.send(StreamEvent::Done(None));
        Ok(())
    }

    // ─── Usage / Cost ───

    pub async fn get_usage(&self) -> Result<UsageResponse> {
        let url = format!("{}/v1/usage", self.base_url);
        let resp = self.client.get(&url).send().await?.json().await?;
        Ok(resp)
    }

    // ─── Direct API call (for providers like OpenRouter) ───

    pub async fn direct_completion(
        &self,
        api_url: &str,
        api_key: &str,
        model: &str,
        messages: Vec<ChatMessage>,
        stream: bool,
    ) -> Result<ChatCompletionResponse> {
        let body = ChatCompletionRequest {
            model: model.to_string(),
            messages,
            stream: Some(stream),
            temperature: Some(0.7),
            max_tokens: Some(4096),
        };

        let resp = self.client
            .post(api_url)
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await?
            .json()
            .await?;

        Ok(resp)
    }
}
