use serde::{Deserialize, Serialize};

// ═══════════════════════════════════════════════════════════════
// LSP CLIENT - Language Server Protocol Integration
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct LspClient {
    language: String,
    server_command: String,
    server_args: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct LspRequest {
    jsonrpc: String,
    id: u32,
    method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    params: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct LspResponse {
    #[allow(dead_code)]
    jsonrpc: String,
    id: Option<u32>,
    result: Option<serde_json::Value>,
    error: Option<LspError>,
}

#[derive(Debug, Deserialize)]
pub struct LspError {
    code: i32,
    message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Diagnostic {
    pub range: Range,
    pub severity: Option<u32>,
    pub message: String,
    #[serde(default)]
    pub source: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Range {
    pub start: Position,
    pub end: Position,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Position {
    pub line: u32,
    pub character: u32,
}

#[derive(Debug, Clone)]
pub struct LspEvent {
    pub diagnostics: Vec<Diagnostic>,
    pub file: String,
}

pub enum LspServerStatus {
    NotStarted,
    Starting,
    Running,
    Error(String),
}

impl LspClient {
    pub fn detect_language(file_path: &str) -> Option<Self> {
        let path = std::path::Path::new(file_path);
        let ext = path.extension()?.to_str()?;

        match ext {
            "ts" | "tsx" | "js" | "jsx" => Some(Self {
                language: "typescript".to_string(),
                server_command: "typescript-language-server".to_string(),
                server_args: vec!["--stdio".to_string()],
            }),
            "py" => Some(Self {
                language: "python".to_string(),
                server_command: "pylsp".to_string(),
                server_args: vec![],
            }),
            "go" => Some(Self {
                language: "go".to_string(),
                server_command: "gopls".to_string(),
                server_args: vec![],
            }),
            "rs" => Some(Self {
                language: "rust".to_string(),
                server_command: "rust-analyzer".to_string(),
                server_args: vec![],
            }),
            "java" => Some(Self {
                language: "java".to_string(),
                server_command: "jdtls".to_string(),
                server_args: vec![],
            }),
            "c" | "cpp" | "h" | "hpp" => Some(Self {
                language: "c-cpp".to_string(),
                server_command: "clangd".to_string(),
                server_args: vec![],
            }),
            "cs" => Some(Self {
                language: "csharp".to_string(),
                server_command: "omnisharp".to_string(),
                server_args: vec!["--languageserver".to_string(), "--hostPID".to_string(), "0".to_string()],
            }),
            "rb" => Some(Self {
                language: "ruby".to_string(),
                server_command: "solargraph".to_string(),
                server_args: vec!["stdio".to_string()],
            }),
            "php" => Some(Self {
                language: "php".to_string(),
                server_command: "php-language-server".to_string(),
                server_args: vec![],
            }),
            _ => None,
        }
    }

    pub fn language(&self) -> &str {
        &self.language
    }

    pub fn is_available(&self) -> bool {
        std::process::Command::new(&self.server_command)
            .arg("--version")
            .output()
            .is_ok()
    }
}

// ═══════════════════════════════════════════════════════════════
// MCP CLIENT - Model Context Protocol Integration
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct McpClient {
    name: String,
    transport: McpTransport,
}

#[derive(Debug, Clone)]
pub enum McpTransport {
    Stdio { command: String, args: Vec<String> },
    Sse { url: String },
}

#[derive(Debug, Serialize)]
pub struct McpRequest {
    jsonrpc: String,
    id: u32,
    method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    params: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct McpResponse {
    #[allow(dead_code)]
    jsonrpc: String,
    id: Option<u32>,
    result: Option<serde_json::Value>,
    error: Option<McpError>,
}

#[derive(Debug, Deserialize)]
pub struct McpError {
    code: i32,
    message: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct McpTool {
    pub name: String,
    pub description: Option<String>,
    #[serde(default)]
    pub input_schema: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct McpResource {
    pub uri: String,
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
}

#[derive(Debug, Clone)]
pub struct McpServerInfo {
    pub name: String,
    pub transport: String,
    pub tools: Vec<McpTool>,
    pub resources: Vec<McpResource>,
    pub status: McpServerStatus,
}

#[derive(Debug, Clone)]
pub enum McpServerStatus {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

impl McpClient {
    pub fn new_stdio(name: &str, command: &str, args: Vec<String>) -> Self {
        Self {
            name: name.to_string(),
            transport: McpTransport::Stdio {
                command: command.to_string(),
                args,
            },
        }
    }

    pub fn new_sse(name: &str, url: &str) -> Self {
        Self {
            name: name.to_string(),
            transport: McpTransport::Sse {
                url: url.to_string(),
            },
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn transport_type(&self) -> &str {
        match &self.transport {
            McpTransport::Stdio { .. } => "stdio",
            McpTransport::Sse { .. } => "sse",
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// TOOL DEFINITIONS (for AI)
// ═══════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize)]
pub struct ToolDefinition {
    #[serde(rename = "type")]
    pub tool_type: String,
    pub function: ToolFunction,
}

#[derive(Debug, Clone, Serialize)]
pub struct ToolFunction {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
}

pub fn get_all_tool_definitions() -> Vec<ToolDefinition> {
    vec![
        // File tools
        make_tool("read_file", "Read file contents with line numbers",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "offset": {"type": "integer", "default": 0},
                    "limit": {"type": "integer", "default": 200}
                },
                "required": ["path"]
            })),
        make_tool("write_file", "Write content to a file",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            })),
        make_tool("edit_file", "Replace exact string in file",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"}
                },
                "required": ["path", "old_string", "new_string"]
            })),
        make_tool("run_bash", "Execute shell command",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30}
                },
                "required": ["command"]
            })),
        make_tool("grep_search", "Search file contents with regex",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "include": {"type": "string", "default": "*"}
                },
                "required": ["pattern"]
            })),
        make_tool("glob_search", "Find files by glob pattern",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."}
                },
                "required": ["pattern"]
            })),
        make_tool("list_directory", "List directory contents",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."}
                }
            })),
        make_tool("run_tests", "Run project tests",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "default": ""},
                    "framework": {"type": "string", "default": "auto"}
                }
            })),
        make_tool("git_status", "Show git status",
            serde_json::json!({"type": "object", "properties": {}})),
        make_tool("git_diff", "Show git diff",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": ""}
                }
            })),
        make_tool("git_log", "Show recent git commits",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "default": 10}
                }
            })),
        make_tool("web_fetch", "Fetch content from URL",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            })),
    ]
}

fn make_tool(name: &str, description: &str, parameters: serde_json::Value) -> ToolDefinition {
    ToolDefinition {
        tool_type: "function".to_string(),
        function: ToolFunction {
            name: name.to_string(),
            description: description.to_string(),
            parameters,
        },
    }
}
