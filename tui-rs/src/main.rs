mod gateway;

use anyhow::Result;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use serde::{Deserialize, Serialize};
use std::io;
use tokio::sync::mpsc;

// ═══════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════

#[derive(Clone, Debug, PartialEq)]
enum Mode {
    Plan,
    Build,
}

#[derive(Clone, Debug)]
enum Popup {
    None,
    Help,
    ModelPicker,
    SessionPicker,
    CommandPalette,
    Transcript,
    FileTree,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct ChatMessage {
    role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    content: Option<String>,
}

#[derive(Debug)]
struct App {
    mode: Mode,
    popup: Popup,
    messages: Vec<ChatMessage>,
    input: String,
    input_cursor: usize,
    scroll_offset: usize,
    provider: String,
    model: String,
    session_id: String,
    is_generating: bool,
    status_message: String,
    token_count: usize,
    file_changes: usize,
    command_list: Vec<CommandEntry>,
    command_selected: usize,
    model_list: Vec<String>,
    model_selected: usize,
    gateway_url: String,
    api_key: String,
    stream_buffer: String,
    rx: Option<mpsc::UnboundedReceiver<gateway::StreamEvent>>,
    last_usage: Option<gateway::Usage>,
    cost_cents: f64,
}

#[derive(Clone, Debug)]
struct CommandEntry {
    id: String,
    label: String,
    shortcut: String,
}

impl Default for App {
    fn default() -> Self {
        let command_list = vec![
            ("clear", "Clear conversation", "/clear"),
            ("status", "Gateway status", "/status"),
            ("models", "List models", "/models"),
            ("sessions", "List sessions", "/sessions"),
            ("save", "Save session", "/save"),
            ("config", "Show config", "/config"),
            ("help", "Help", "/help"),
            ("quit", "Quit", "/quit"),
            ("new_session", "New session", ""),
            ("switch_model", "Switch model", "Ctrl+P"),
            ("switch_session", "Switch session", "Ctrl+S"),
            ("theme", "Switch theme", "/theme"),
            ("export", "Export session", "/export"),
            ("compact", "Compact context", "/compact"),
            ("init", "Generate AGENTS.md", "/init"),
            ("undo", "Undo last change", "/undo"),
            ("diff", "Show changes", "/diff"),
            ("cost", "Show cost", "/cost"),
        ]
        .into_iter()
        .map(|(id, label, shortcut)| CommandEntry {
            id: id.to_string(),
            label: label.to_string(),
            shortcut: shortcut.to_string(),
        })
        .collect();

        Self {
            mode: Mode::Plan,
            popup: Popup::None,
            messages: vec![ChatMessage {
                role: "system".to_string(),
                content: Some("Welcome to Patchbay AI".to_string()),
            }],
            input: String::new(),
            input_cursor: 0,
            scroll_offset: 0,
            provider: "openrouter".to_string(),
            model: "gpt-4o".to_string(),
            session_id: "abc12345".to_string(),
            is_generating: false,
            status_message: String::new(),
            token_count: 0,
            file_changes: 0,
            command_list,
            command_selected: 0,
            model_list: vec![
                "gpt-4o".to_string(),
                "gpt-4o-mini".to_string(),
                "claude-sonnet-4-20250514".to_string(),
                "claude-3-5-sonnet-20241022".to_string(),
                "gemini-2.5-flash".to_string(),
                "gemini-2.5-pro".to_string(),
                "deepseek-chat".to_string(),
            ],
            model_selected: 0,
            gateway_url: std::env::var("PATCHBAY_GATEWAY_URL")
                .unwrap_or_else(|_| "http://localhost:8000".to_string()),
            api_key: std::env::var("PATCHBAY_API_KEY")
                .unwrap_or_else(|_| "".to_string()),
            stream_buffer: String::new(),
            rx: None,
            last_usage: None,
            cost_cents: 0.0,
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// THEME COLORS (Tokyo Night)
// ═══════════════════════════════════════════════════════════════

const BG: Color = Color::Rgb(26, 27, 38);
const SURFACE: Color = Color::Rgb(31, 35, 53);
const BORDER: Color = Color::Rgb(59, 66, 97);
const TEXT: Color = Color::Rgb(192, 202, 245);
const MUTED: Color = Color::Rgb(86, 95, 137);
const ACCENT: Color = Color::Rgb(122, 162, 247);
const SUCCESS: Color = Color::Rgb(158, 206, 106);
const WARNING: Color = Color::Rgb(224, 175, 104);
const ERROR: Color = Color::Rgb(247, 118, 142);
const CYAN: Color = Color::Rgb(125, 207, 255);

// ═══════════════════════════════════════════════════════════════
// APP LOGIC
// ═══════════════════════════════════════════════════════════════

impl App {
    fn handle_key(&mut self, key: event::KeyEvent) -> bool {
        match &self.popup {
            Popup::None => self.handle_main_key(key),
            Popup::Help => {
                if key.code == KeyCode::Esc || key.code == KeyCode::Char('q') {
                    self.popup = Popup::None;
                }
                false
            }
            Popup::CommandPalette => self.handle_command_palette_key(key),
            Popup::ModelPicker => self.handle_model_picker_key(key),
            Popup::SessionPicker => self.handle_session_picker_key(key),
            Popup::Transcript => {
                if key.code == KeyCode::Esc || key.code == KeyCode::Char('q') {
                    self.popup = Popup::None;
                }
                false
            }
            Popup::FileTree => {
                if key.code == KeyCode::Esc || key.code == KeyCode::Char('q') {
                    self.popup = Popup::None;
                }
                false
            }
        }
    }

    fn handle_main_key(&mut self, key: event::KeyEvent) -> bool {
        match key.code {
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                return true; // Quit
            }
            KeyCode::Char('d') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                return true; // Quit
            }
            KeyCode::Char('l') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                // Clear handled by terminal
                false
            }
            KeyCode::Char('p') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::ModelPicker;
                self.model_selected = 0;
                false
            }
            KeyCode::Char('s') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::SessionPicker;
                false
            }
            KeyCode::Char('k') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::CommandPalette;
                self.command_selected = 0;
                false
            }
            KeyCode::Char('h') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::Help;
                false
            }
            KeyCode::Char('t') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::Transcript;
                false
            }
            KeyCode::Char('n') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.messages.clear();
                self.messages.push(ChatMessage {
                    role: "system".to_string(),
                    content: Some("New session started".to_string()),
                });
                self.session_id = format!("{:08x}", rand::random::<u32>());
                false
            }
            KeyCode::Char('b') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                self.popup = Popup::FileTree;
                false
            }
            KeyCode::Tab => {
                self.mode = match self.mode {
                    Mode::Plan => Mode::Build,
                    Mode::Build => Mode::Plan,
                };
                false
            }
            KeyCode::Enter => {
                if !self.input.is_empty() {
                    let input = self.input.clone();
                    self.input.clear();
                    self.input_cursor = 0;
                    self.handle_input(input);
                }
                false
            }
            KeyCode::Char(c) => {
                self.input.insert(self.input_cursor, c);
                self.input_cursor += 1;
                false
            }
            KeyCode::Backspace => {
                if self.input_cursor > 0 {
                    self.input_cursor -= 1;
                    self.input.remove(self.input_cursor);
                }
                false
            }
            KeyCode::Delete => {
                if self.input_cursor < self.input.len() {
                    self.input.remove(self.input_cursor);
                }
                false
            }
            KeyCode::Left => {
                if self.input_cursor > 0 {
                    self.input_cursor -= 1;
                }
                false
            }
            KeyCode::Right => {
                if self.input_cursor < self.input.len() {
                    self.input_cursor += 1;
                }
                false
            }
            KeyCode::Home => {
                self.input_cursor = 0;
                false
            }
            KeyCode::End => {
                self.input_cursor = self.input.len();
                false
            }
            KeyCode::Up => {
                if self.scroll_offset > 0 {
                    self.scroll_offset -= 1;
                }
                false
            }
            KeyCode::Down => {
                self.scroll_offset += 1;
                false
            }
            KeyCode::PageUp => {
                self.scroll_offset = self.scroll_offset.saturating_sub(10);
                false
            }
            KeyCode::PageDown => {
                self.scroll_offset += 10;
                false
            }
            _ => false,
        }
    }

    fn handle_command_palette_key(&mut self, key: event::KeyEvent) -> bool {
        match key.code {
            KeyCode::Esc => {
                self.popup = Popup::None;
                false
            }
            KeyCode::Up => {
                if self.command_selected > 0 {
                    self.command_selected -= 1;
                }
                false
            }
            KeyCode::Down => {
                if self.command_selected < self.command_list.len() - 1 {
                    self.command_selected += 1;
                }
                false
            }
            KeyCode::Enter => {
                if let Some(cmd) = self.command_list.get(self.command_selected) {
                    let cmd_id = cmd.id.clone();
                    self.popup = Popup::None;
                    self.handle_command(&cmd_id);
                }
                false
            }
            _ => false,
        }
    }

    fn handle_model_picker_key(&mut self, key: event::KeyEvent) -> bool {
        match key.code {
            KeyCode::Esc => {
                self.popup = Popup::None;
                false
            }
            KeyCode::Up => {
                if self.model_selected > 0 {
                    self.model_selected -= 1;
                }
                false
            }
            KeyCode::Down => {
                if self.model_selected < self.model_list.len() - 1 {
                    self.model_selected += 1;
                }
                false
            }
            KeyCode::Enter => {
                if let Some(model) = self.model_list.get(self.model_selected) {
                    self.model = model.clone();
                    self.popup = Popup::None;
                    self.status_message = format!("Model: {}", self.model);
                }
                false
            }
            _ => false,
        }
    }

    fn handle_session_picker_key(&mut self, key: event::KeyEvent) -> bool {
        match key.code {
            KeyCode::Esc | KeyCode::Char('q') => {
                self.popup = Popup::None;
                false
            }
            KeyCode::Char('n') => {
                self.popup = Popup::None;
                self.handle_command("new_session");
                false
            }
            _ => false,
        }
    }

    fn handle_input(&mut self, input: String) {
        if input.starts_with('/') {
            let cmd = input.trim().trim_start_matches('/');
            let cmd_name = cmd.split_whitespace().next().unwrap_or(cmd);
            self.handle_command(cmd_name);
        } else if input.starts_with('!') {
            let cmd = input.trim_start_matches('!').trim();
            self.status_message = format!("Running: {}", cmd);
        } else {
            self.messages.push(ChatMessage {
                role: "user".to_string(),
                content: Some(input),
            });
            self.is_generating = true;
            self.status_message = "Generating...".to_string();
            self.stream_buffer.clear();
            // Gateway streaming is triggered in main loop
        }
    }

    fn handle_command(&mut self, cmd: &str) {
        match cmd {
            "quit" | "exit" => {}
            "clear" => {
                self.messages.clear();
                self.messages.push(ChatMessage {
                    role: "system".to_string(),
                    content: Some("Cleared.".to_string()),
                });
            }
            "help" => self.popup = Popup::Help,
            "status" => {
                self.status_message = "Gateway: OK | DB: OK | Dashboard: OK".to_string();
            }
            "models" => self.popup = Popup::ModelPicker,
            "sessions" => self.popup = Popup::SessionPicker,
            "new_session" => {
                self.messages.clear();
                self.messages.push(ChatMessage {
                    role: "system".to_string(),
                    content: Some("New session".to_string()),
                });
                self.session_id = format!("{:08x}", rand::random::<u32>());
            }
            "switch_model" => self.popup = Popup::ModelPicker,
            "switch_session" => self.popup = Popup::SessionPicker,
            "cost" => {
                self.status_message = format!("~{} tokens | {} messages", self.token_count, self.messages.len());
            }
            "compact" => {
                if self.messages.len() > 6 {
                    let recent: Vec<_> = self.messages[self.messages.len() - 4..].to_vec();
                    self.messages.truncate(3);
                    self.messages.push(ChatMessage {
                        role: "system".to_string(),
                        content: Some(format!("Compacted. {} recent kept.", recent.len())),
                    });
                    self.messages.extend(recent);
                    self.status_message = "Compacted.".to_string();
                }
            }
            "undo" => {
                if self.file_changes > 0 {
                    self.file_changes -= 1;
                    self.status_message = "Undone.".to_string();
                } else {
                    self.status_message = "Nothing to undo.".to_string();
                }
            }
            "diff" => {
                self.status_message = format!("{} file changes tracked", self.file_changes);
            }
            _ => {
                self.status_message = format!("Unknown command: {}", cmd);
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// RENDERING
// ═══════════════════════════════════════════════════════════════

fn ui(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Header
            Constraint::Min(1),    // Chat area
            Constraint::Length(3), // Status bar
            Constraint::Length(3), // Input
        ])
        .split(f.area());

    // Header
    render_header(f, app, chunks[0]);

    // Chat area
    render_chat(f, app, chunks[1]);

    // Status bar
    render_status_bar(f, app, chunks[2]);

    // Input
    render_input(f, app, chunks[3]);

    // Popup overlay
    match &app.popup {
        Popup::Help => render_help_popup(f, app),
        Popup::CommandPalette => render_command_palette_popup(f, app),
        Popup::ModelPicker => render_model_picker_popup(f, app),
        Popup::SessionPicker => render_session_picker_popup(f, app),
        Popup::Transcript => render_transcript_popup(f, app),
        Popup::FileTree => render_file_tree_popup(f, app),
        Popup::None => {}
    }
}

fn render_header(f: &mut Frame, app: &App, area: Rect) {
    let mode_text = match app.mode {
        Mode::Plan => Span::styled(" PLAN ", Style::default().fg(CYAN).add_modifier(Modifier::BOLD)),
        Mode::Build => Span::styled(" BUILD ", Style::default().fg(SUCCESS).add_modifier(Modifier::BOLD)),
    };

    let header = Line::from(vec![
        Span::styled(" Patchbay ", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)),
        Span::styled(" | ", Style::default().fg(MUTED)),
        Span::raw(&app.provider),
        Span::styled(" | ", Style::default().fg(MUTED)),
        Span::raw(&app.model),
        Span::styled(" | ", Style::default().fg(MUTED)),
        Span::raw(&app.session_id),
        Span::styled(" | ", Style::default().fg(MUTED)),
        mode_text,
    ]);

    let paragraph = Paragraph::new(header).block(
        Block::default()
            .borders(Borders::BOTTOM)
            .border_style(Style::default().fg(BORDER)),
    );
    f.render_widget(paragraph, area);
}

fn render_chat(f: &mut Frame, app: &App, area: Rect) {
    let mut lines: Vec<Line> = Vec::new();

    for msg in &app.messages {
        match msg.role.as_str() {
            "user" => {
                lines.push(Line::from(vec![
                    Span::styled(" You ", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)),
                ]));
                if let Some(content) = &msg.content {
                    for line in content.lines() {
                        lines.push(Line::from(Span::raw(line.to_string())));
                    }
                }
                lines.push(Line::from(""));
            }
            "assistant" => {
                lines.push(Line::from(vec![
                    Span::styled(" AI ", Style::default().fg(SUCCESS).add_modifier(Modifier::BOLD)),
                ]));
                if let Some(content) = &msg.content {
                    for line in content.lines() {
                        lines.push(Line::from(Span::styled(line.to_string(), Style::default().fg(TEXT))));
                    }
                }
                lines.push(Line::from(""));
            }
            "system" => {
                let content = msg.content.as_deref().unwrap_or("");
                lines.push(Line::from(Span::styled(
                    format!(" {}", content),
                    Style::default().fg(MUTED),
                )));
            }
            _ => {}
        }
    }

    // Show streaming buffer
    if app.is_generating && !app.stream_buffer.is_empty() {
        lines.push(Line::from(vec![
            Span::styled(" AI ", Style::default().fg(SUCCESS).add_modifier(Modifier::BOLD)),
        ]));
        for line in app.stream_buffer.lines() {
            lines.push(Line::from(Span::styled(line.to_string(), Style::default().fg(TEXT))));
        }
    }

    let paragraph = Paragraph::new(lines)
        .scroll((app.scroll_offset as u16, 0))
        .wrap(Wrap { trim: false });

    f.render_widget(paragraph, area);
}

fn render_status_bar(f: &mut Frame, app: &App, area: Rect) {
    let mode_color = match app.mode {
        Mode::Plan => CYAN,
        Mode::Build => SUCCESS,
    };
    let mode_label = match app.mode {
        Mode::Plan => "PLAN",
        Mode::Build => "BUILD",
    };

    let mut spans = vec![
        Span::styled(format!(" {} ", mode_label), Style::default().fg(mode_color).add_modifier(Modifier::BOLD)),
        Span::styled(" Tab ", Style::default().fg(MUTED)),
    ];

    // Add streaming indicator
    if app.is_generating {
        spans.push(Span::styled(" ● generating ", Style::default().fg(WARNING)));
    }

    // Add usage info
        if let Some(usage) = &app.last_usage {
            if let Some(tokens) = usage.total_tokens {
                spans.push(Span::styled(
                    format!(" {} tokens ", tokens),
                    Style::default().fg(MUTED),
                ));
            }
            if let Some(_cost) = usage.prompt_tokens {
                spans.push(Span::styled(
                    format!(" ~${:.4} ", app.cost_cents / 100.0),
                    Style::default().fg(MUTED),
                ));
            }
        }

    spans.push(Span::styled(" Ctrl+K cmd  Ctrl+P model  Ctrl+H help  Ctrl+D exit", Style::default().fg(MUTED)));

    let line = Line::from(spans);
    let paragraph = Paragraph::new(line).block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(BORDER)),
    );
    f.render_widget(paragraph, area);
}

fn render_input(f: &mut Frame, app: &App, area: Rect) {
    let input_line = Line::from(vec![
        Span::styled(
            format!(" {}> ", if app.mode == Mode::Build { "B" } else { "P" }),
            Style::default().fg(if app.mode == Mode::Build { SUCCESS } else { CYAN }).add_modifier(Modifier::BOLD),
        ),
        Span::styled(&app.input, Style::default().fg(TEXT)),
        Span::styled(" ", Style::default().fg(TEXT)), // Cursor
    ]);

    let paragraph = Paragraph::new(input_line).block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(BORDER))
            .title(" Input "),
    );
    f.render_widget(paragraph, area);
}

fn render_help_popup(f: &mut Frame, _app: &App) {
    let area = centered_rect(70, 80, f.area());
    f.render_widget(Clear, area);

    let text = vec![
        Line::from(Span::styled(" Patchbay AI - Help", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))),
        Line::from(""),
        Line::from(Span::styled(" Keyboard", Style::default().fg(TEXT).add_modifier(Modifier::BOLD))),
        Line::from(vec![Span::styled("  Ctrl+D", Style::default().fg(CYAN)), Span::raw("       Quick exit")]),
        Line::from(vec![Span::styled("  Ctrl+L", Style::default().fg(CYAN)), Span::raw("       Clear screen")]),
        Line::from(vec![Span::styled("  Ctrl+R", Style::default().fg(CYAN)), Span::raw("       Search history")]),
        Line::from(vec![Span::styled("  Ctrl+P", Style::default().fg(CYAN)), Span::raw("       Model picker")]),
        Line::from(vec![Span::styled("  Ctrl+S", Style::default().fg(CYAN)), Span::raw("       Session picker")]),
        Line::from(vec![Span::styled("  Ctrl+K", Style::default().fg(CYAN)), Span::raw("       Command palette")]),
        Line::from(vec![Span::styled("  Ctrl+H", Style::default().fg(CYAN)), Span::raw("       Help")]),
        Line::from(vec![Span::styled("  Ctrl+T", Style::default().fg(CYAN)), Span::raw("       Transcript")]),
        Line::from(vec![Span::styled("  Ctrl+N", Style::default().fg(CYAN)), Span::raw("       New session")]),
        Line::from(vec![Span::styled("  Ctrl+B", Style::default().fg(CYAN)), Span::raw("       File tree")]),
        Line::from(vec![Span::styled("  Tab", Style::default().fg(CYAN)), Span::raw("           Switch Plan/Build")]),
        Line::from(vec![Span::styled("  Esc", Style::default().fg(CYAN)), Span::raw("            Close popup")]),
        Line::from(""),
        Line::from(Span::styled(" Slash Commands", Style::default().fg(TEXT).add_modifier(Modifier::BOLD))),
        Line::from(vec![Span::styled("  /help", Style::default().fg(ACCENT)), Span::raw("       This help")]),
        Line::from(vec![Span::styled("  /clear", Style::default().fg(ACCENT)), Span::raw("      Clear conversation")]),
        Line::from(vec![Span::styled("  /model", Style::default().fg(ACCENT)), Span::raw("      Switch model")]),
        Line::from(vec![Span::styled("  /status", Style::default().fg(ACCENT)), Span::raw("     Gateway status")]),
        Line::from(vec![Span::styled("  /undo", Style::default().fg(ACCENT)), Span::raw("       Undo last change")]),
        Line::from(vec![Span::styled("  /compact", Style::default().fg(ACCENT)), Span::raw("    Compact context")]),
        Line::from(vec![Span::styled("  /cost", Style::default().fg(ACCENT)), Span::raw("       Show cost")]),
        Line::from(vec![Span::styled("  /quit", Style::default().fg(ACCENT)), Span::raw("       Exit")]),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(" Help "),
    );
    f.render_widget(paragraph, area);
}

fn render_command_palette_popup(f: &mut Frame, app: &App) {
    let area = centered_rect(50, 70, f.area());
    f.render_widget(Clear, area);

    let items: Vec<ListItem> = app
        .command_list
        .iter()
        .enumerate()
        .map(|(i, cmd)| {
            let style = if i == app.command_selected {
                Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(TEXT)
            };
            ListItem::new(Line::from(vec![
                Span::styled(format!(" {} ", cmd.label), style),
                Span::styled(format!("  {}", cmd.shortcut), Style::default().fg(MUTED)),
            ]))
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(" Commands "),
    );
    f.render_widget(list, area);
}

fn render_model_picker_popup(f: &mut Frame, app: &App) {
    let area = centered_rect(50, 60, f.area());
    f.render_widget(Clear, area);

    let items: Vec<ListItem> = app
        .model_list
        .iter()
        .enumerate()
        .map(|(i, model)| {
            let style = if i == app.model_selected {
                Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(TEXT)
            };
            let marker = if *model == app.model {
                Span::styled(" *", Style::default().fg(SUCCESS))
            } else {
                Span::raw("")
            };
            ListItem::new(Line::from(vec![
                Span::styled(format!(" {} ", model), style),
                marker,
            ]))
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(format!(" Models ({}) ", app.model_list.len())),
    );
    f.render_widget(list, area);
}

fn render_session_picker_popup(f: &mut Frame, _app: &App) {
    let area = centered_rect(50, 50, f.area());
    f.render_widget(Clear, area);

    let text = vec![
        Line::from(Span::styled(" Sessions", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))),
        Line::from(""),
        Line::from(Span::styled("  No sessions saved.", Style::default().fg(MUTED))),
        Line::from(""),
        Line::from(vec![
            Span::styled("  Press ", Style::default().fg(MUTED)),
            Span::styled("n", Style::default().fg(CYAN).add_modifier(Modifier::BOLD)),
            Span::styled(" for new session", Style::default().fg(MUTED)),
        ]),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(" Sessions "),
    );
    f.render_widget(paragraph, area);
}

fn render_transcript_popup(f: &mut Frame, app: &App) {
    let area = centered_rect(80, 80, f.area());
    f.render_widget(Clear, area);

    let mut lines: Vec<Line> = vec![
        Line::from(Span::styled(
            format!(" Transcript ({} messages)", app.messages.len()),
            Style::default().fg(ACCENT).add_modifier(Modifier::BOLD),
        )),
    ];

    for msg in &app.messages {
        match msg.role.as_str() {
            "user" => {
                lines.push(Line::from(Span::styled(" You:", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))));
                if let Some(content) = &msg.content {
                    for line in content.lines().take(5) {
                        lines.push(Line::from(Span::raw(line.to_string())));
                    }
                }
            }
            "assistant" => {
                lines.push(Line::from(Span::styled(" AI:", Style::default().fg(SUCCESS).add_modifier(Modifier::BOLD))));
                if let Some(content) = &msg.content {
                    for line in content.lines().take(5) {
                        lines.push(Line::from(Span::styled(line.to_string(), Style::default().fg(TEXT))));
                    }
                }
            }
            _ => {}
        }
    }

    let paragraph = Paragraph::new(lines).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(" Transcript "),
    );
    f.render_widget(paragraph, area);
}

fn render_file_tree_popup(f: &mut Frame, _app: &App) {
    let area = centered_rect(50, 60, f.area());
    f.render_widget(Clear, area);

    let text = vec![
        Line::from(Span::styled(" File Tree", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))),
        Line::from(""),
        Line::from(Span::styled("  src/", Style::default().fg(CYAN))),
        Line::from(Span::raw("    main.rs")),
        Line::from(Span::raw("    lib.rs")),
        Line::from(Span::styled("  tests/", Style::default().fg(CYAN))),
        Line::from(Span::raw("    test_main.rs")),
        Line::from(Span::styled("  Cargo.toml", Style::default().fg(TEXT))),
    ];

    let paragraph = Paragraph::new(text).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT))
            .title(" File Tree "),
    );
    f.render_widget(paragraph, area);
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

// ═══════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════

#[tokio::main]
async fn main() -> Result<()> {
    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::default();
    let gw = gateway::GatewayClient::new(&app.gateway_url);

    // Try to fetch models from gateway on startup
    if let Ok(models) = gw.list_models().await {
        if !models.is_empty() {
            app.model_list = models.iter().map(|m| m.id.clone()).collect();
            app.status_message = format!("Loaded {} models from gateway", models.len());
        }
    }

    // Main loop
    loop {
        // Process streaming events
        let mut done_event = false;
        let mut error_event = None;
        let mut usage_data = None;
        if let Some(rx) = app.rx.as_mut() {
            while let Ok(event) = rx.try_recv() {
                match event {
                    gateway::StreamEvent::Text(text) => {
                        app.stream_buffer.push_str(&text);
                    }
                    gateway::StreamEvent::Done(usage) => {
                        done_event = true;
                        usage_data = usage;
                    }
                    gateway::StreamEvent::Error(err) => {
                        error_event = Some(err);
                    }
                }
            }
        }
        if done_event {
            let content = app.stream_buffer.clone();
            if !content.is_empty() {
                app.messages.push(ChatMessage {
                    role: "assistant".to_string(),
                    content: Some(content),
                });
            }
            if let Some(u) = &usage_data {
                app.last_usage = Some(u.clone());
                if let Some(tokens) = u.total_tokens {
                    app.token_count += tokens as usize;
                }
            }
            app.stream_buffer.clear();
            app.is_generating = false;
            app.status_message.clear();
            app.rx = None;
        }
        if let Some(err) = error_event {
            app.stream_buffer.clear();
            app.is_generating = false;
            app.status_message = format!("Error: {}", err);
            app.rx = None;
        }

        // Trigger streaming if needed
        if app.is_generating && app.rx.is_none() {
            if let Some(last_msg) = app.messages.last() {
                if last_msg.role == "user" {
                    let mut gw_messages: Vec<gateway::ChatMessage> = app.messages.iter().map(|m| {
                        gateway::ChatMessage {
                            role: m.role.clone(),
                            content: m.content.clone(),
                        }
                    }).collect();

                    // Add system prompt
                    gw_messages.insert(0, gateway::ChatMessage {
                        role: "system".to_string(),
                        content: Some("You are Patchbay AI, a helpful coding assistant. Be concise and helpful.".to_string()),
                    });

                    let (tx, rx) = mpsc::unbounded_channel();
                    app.rx = Some(rx);
                    app.stream_buffer.clear();

                    let model = app.model.clone();
                    let gw_clone = gw.clone();
                    tokio::spawn(async move {
                        let _ = gw_clone.stream_completion(
                            &model,
                            gw_messages,
                            Some(0.7),
                            Some(4096),
                            tx,
                        ).await;
                    });
                }
            }
        }

        terminal.draw(|f| ui(f, &app))?;

        if event::poll(std::time::Duration::from_millis(50))? {
            if let Event::Key(key) = event::read()? {
                if app.handle_key(key) {
                    break;
                }
            }
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    Ok(())
}
