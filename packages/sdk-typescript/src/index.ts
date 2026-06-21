const API_BASE = process.env.PATCHBAY_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionResponse {
  id: string;
  choices: {
    index: number;
    message: { role: string; content: string };
    finish_reason: string;
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  gateway_metadata: {
    selected_route: { provider: string; model: string } | null;
    routing_strategy: string;
    cache_hit: boolean;
    cost_usd_cents: number;
    latency_ms: number;
  };
}

export class GatewayClient {
  private apiKey: string;
  private baseUrl: string;

  constructor(apiKey: string, baseUrl: string = API_BASE) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async chat(params: {
    model: string;
    messages: ChatMessage[];
    maxTokens?: number;
    temperature?: number;
  }): Promise<ChatCompletionResponse> {
    const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    return res.json();
  }

  async listModels() {
    const res = await fetch(`${this.baseUrl}/v1/models`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
    return res.json();
  }
}
