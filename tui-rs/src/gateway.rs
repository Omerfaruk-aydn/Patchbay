use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

// ═══════════════════════════════════════════════════════════════
// GATEWAY CLIENT
// ═══════════════════════════════════════════════════════════════

#[derive(Clone)]
pub struct GatewayClient {
    base_url: String,
    client: Client,
}

#[derive(Debug, Serialize)]
pub struct ChatRequest {
    pub model: String,
    pub messages: Vec<ChatMessage>,
    pub stream: bool,
    pub temperature: f32,
    pub max_tokens: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ChatResponse {
    pub choices: Vec<Choice>,
}

#[derive(Debug, Deserialize)]
pub struct Choice {
    pub message: Option<ChatMessage>,
    pub delta: Option<Delta>,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Delta {
    pub content: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ModelInfo {
    pub id: String,
    #[serde(default)]
    pub name: String,
}

#[derive(Debug, Deserialize)]
pub struct ModelsResponse {
    pub data: Vec<ModelInfo>,
}

#[derive(Debug, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: Option<String>,
}

pub enum StreamEvent {
    Text(String),
    Done,
    Error(String),
}

impl GatewayClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client: Client::new(),
        }
    }

    pub async fn health(&self) -> Result<HealthResponse> {
        let url = format!("{}/health", self.base_url);
        let resp = self.client.get(&url).send().await?.json().await?;
        Ok(resp)
    }

    pub async fn list_models(&self) -> Result<Vec<ModelInfo>> {
        let url = format!("{}/v1/models", self.base_url);
        let resp: ModelsResponse = self.client.get(&url).send().await?.json().await?;
        Ok(resp.data)
    }

    pub async fn chat_completion(
        &self,
        model: &str,
        messages: Vec<ChatMessage>,
        stream: bool,
    ) -> Result<ChatResponse> {
        let url = format!("{}/v1/chat/completions", self.base_url);
        let body = ChatRequest {
            model: model.to_string(),
            messages,
            stream,
            temperature: 0.7,
            max_tokens: 4096,
        };
        let resp = self.client.post(&url).json(&body).send().await?.json().await?;
        Ok(resp)
    }

    pub async fn stream_completion(
        &self,
        model: &str,
        messages: Vec<ChatMessage>,
        tx: mpsc::UnboundedSender<StreamEvent>,
    ) -> Result<()> {
        let url = format!("{}/v1/chat/completions", self.base_url);
        let body = ChatRequest {
            model: model.to_string(),
            messages,
            stream: true,
            temperature: 0.7,
            max_tokens: 4096,
        };

        let response = self.client.post(&url).json(&body).send().await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            let _ = tx.send(StreamEvent::Error(format!("HTTP {}: {}", status, text)));
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

                        if line.is_empty() || line == "data: [DONE]" {
                            if line == "data: [DONE]" {
                                let _ = tx.send(StreamEvent::Done);
                                return Ok(());
                            }
                            continue;
                        }

                        if let Some(data) = line.strip_prefix("data: ") {
                            if let Ok(chunk) = serde_json::from_str::<serde_json::Value>(data) {
                                if let Some(choices) = chunk.get("choices") {
                                    if let Some(choice) = choices.get(0) {
                                        if let Some(delta) = choice.get("delta") {
                                            if let Some(content) = delta.get("content") {
                                                if let Some(text) = content.as_str() {
                                                    let _ = tx.send(StreamEvent::Text(text.to_string()));
                                                }
                                            }
                                        }
                                        if choice.get("finish_reason").is_some() {
                                            let _ = tx.send(StreamEvent::Done);
                                            return Ok(());
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

        let _ = tx.send(StreamEvent::Done);
        Ok(())
    }
}
