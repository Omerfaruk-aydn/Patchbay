"""Themes - Tokyo Night + 6 more themes for Patchbay CLI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Theme:
    name: str
    bg: str
    surface: str
    border: str
    text: str
    muted: str
    accent: str
    success: str
    warning: str
    error: str
    cyan: str
    magenta: str
    orange: str
    # Rich markup compatible hex (no #)
    rich_accent: str
    rich_success: str
    rich_warning: str
    rich_error: str
    rich_muted: str
    rich_text: str
    rich_cyan: str
    rich_magenta: str
    rich_surface: str


TOKYO_NIGHT = Theme(
    name="tokyo-night",
    bg="#1a1b26", surface="#1f2335", border="#3b4261",
    text="#c0caf5", muted="#565f89",
    accent="#7aa2f7", success="#9ece6a", warning="#e0af68", error="#f7768e",
    cyan="#7dcfff", magenta="#bb9af7", orange="#ff9e64",
    rich_accent="#7aa2f7", rich_success="#9ece6a", rich_warning="#e0af68",
    rich_error="#f7768e", rich_muted="#565f89", rich_text="#c0caf5",
    rich_cyan="#7dcfff", rich_magenta="#bb9af7", rich_surface="#1f2335",
)

DARK = Theme(
    name="dark",
    bg="#0D1117", surface="#161B22", border="#30363D",
    text="#E6EDF3", muted="#8B949E",
    accent="#58A6FF", success="#3FB950", warning="#D29922", error="#F85149",
    cyan="#79C0FF", magenta="#D2A8FF", orange="#FFA657",
    rich_accent="#58A6FF", rich_success="#3FB950", rich_warning="#D29922",
    rich_error="#F85149", rich_muted="#8B949E", rich_text="#E6EDF3",
    rich_cyan="#79C0FF", rich_magenta="#D2A8FF", rich_surface="#161B22",
)

DRACULA = Theme(
    name="dracula",
    bg="#282A36", surface="#44475A", border="#6272A4",
    text="#F8F8F2", muted="#6272A4",
    accent="#BD93F9", success="#50FA7B", warning="#F1FA8C", error="#FF5555",
    cyan="#8BE9FD", magenta="#FF79C6", orange="#FFB86C",
    rich_accent="#BD93F9", rich_success="#50FA7B", rich_warning="#F1FA8C",
    rich_error="#FF5555", rich_muted="#6272A4", rich_text="#F8F8F2",
    rich_cyan="#8BE9FD", rich_magenta="#FF79C6", rich_surface="#44475A",
)

CATPPUCCIN = Theme(
    name="catppuccin",
    bg="#1E1E2E", surface="#313244", border="#585B70",
    text="#CDD6F4", muted="#6C7086",
    accent="#89B4FA", success="#A6E3A1", warning="#F9E2AF", error="#F38BA8",
    cyan="#94E2D5", magenta="#F5C2E7", orange="#FAB387",
    rich_accent="#89B4FA", rich_success="#A6E3A1", rich_warning="#F9E2AF",
    rich_error="#F38BA8", rich_muted="#6C7086", rich_text="#CDD6F4",
    rich_cyan="#94E2D5", rich_magenta="#F5C2E7", rich_surface="#313244",
)

GRUVBOX = Theme(
    name="gruvbox",
    bg="#282828", surface="#3C3836", border="#504945",
    text="#EBDBB2", muted="#928374",
    accent="#83A598", success="#B8BB26", warning="#FABD2F", error="#FB4934",
    cyan="#8EC07C", magenta="#D3869B", orange="#FE8019",
    rich_accent="#83A598", rich_success="#B8BB26", rich_warning="#FABD2F",
    rich_error="#FB4934", rich_muted="#928374", rich_text="#EBDBB2",
    rich_cyan="#8EC07C", rich_magenta="#D3869B", rich_surface="#3C3836",
)

NORD = Theme(
    name="nord",
    bg="#2E3440", surface="#3B4252", border="#434C5E",
    text="#ECEFF4", muted="#616E88",
    accent="#88C0D0", success="#A3BE8C", warning="#EBCB8B", error="#BF616A",
    cyan="#8FBCBB", magenta="#B48EAD", orange="#D08770",
    rich_accent="#88C0D0", rich_success="#A3BE8C", rich_warning="#EBCB8B",
    rich_error="#BF616A", rich_muted="#616E88", rich_text="#ECEFF4",
    rich_cyan="#8FBCBB", rich_magenta="#B48EAD", rich_surface="#3B4252",
)

LIGHT = Theme(
    name="light",
    bg="#FFFFFF", surface="#F6F8FA", border="#D0D7DE",
    text="#1F2328", muted="#656D76",
    accent="#0969DA", success="#1A7F37", warning="#9A6700", error="#CF222E",
    cyan="#0550AE", magenta="#8250DF", orange="#BC4C00",
    rich_accent="#0969DA", rich_success="#1A7F37", rich_warning="#9A6700",
    rich_error="#CF222E", rich_muted="#656D76", rich_text="#1F2328",
    rich_cyan="#0550AE", rich_magenta="#8250DF", rich_surface="#F6F8FA",
)

THEMES: dict[str, Theme] = {
    "tokyo-night": TOKYO_NIGHT,
    "dark": DARK,
    "dracula": DRACULA,
    "catppuccin": CATPPUCCIN,
    "gruvbox": GRUVBOX,
    "nord": NORD,
    "light": LIGHT,
}


def get_theme(name: str | None = None) -> Theme:
    from patchbay.config import get_config
    if name is None:
        cfg = get_config()
        name = cfg.get("theme", "tokyo-night")
    return THEMES.get(name, TOKYO_NIGHT)
