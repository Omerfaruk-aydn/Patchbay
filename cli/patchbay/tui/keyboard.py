"""Keyboard - Key bindings and shortcuts for Patchbay CLI."""

from __future__ import annotations

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

kb = KeyBindings()


# ═══════════════════════════════════════════════════════════════
# GLOBAL SHORTCUTS
# ═══════════════════════════════════════════════════════════════

@kb.add("c-d")
def _(event):
    """Ctrl+D: Quick exit."""
    event.app.exit()


@kb.add("c-l")
def _(event):
    """Ctrl+L: Clear screen."""
    event.app.renderer.clear()


@kb.add("c-c")
def _(event):
    """Ctrl+C: Cancel current input."""
    event.app.current_buffer.reset()


@kb.add("c-a")
def _(event):
    """Ctrl+A: Beginning of line."""
    event.app.current_buffer.cursor_position = 0


@kb.add("c-e")
def _(event):
    """Ctrl+E: End of line."""
    event.app.current_buffer.cursor_position = len(event.app.current_buffer.text)


@kb.add("c-w")
def _(event):
    """Ctrl+W: Delete word backward."""
    buf = event.app.current_buffer
    pos = buf.cursor_position
    text = buf.text[:pos]
    # Find last word boundary
    i = pos - 1
    while i > 0 and text[i] == " ":
        i -= 1
    while i > 0 and text[i - 1] != " ":
        i -= 1
    buf.text = buf.text[:i] + buf.text[pos:]
    buf.cursor_position = i


@kb.add("c-u")
def _(event):
    """Ctrl+U: Delete line backward."""
    buf = event.app.current_buffer
    buf.text = buf.text[buf.cursor_position:]
    buf.cursor_position = 0


@kb.add("c-k")
def _(event):
    """Ctrl+K: Delete line forward."""
    buf = event.app.current_buffer
    buf.text = buf.text[:buf.cursor_position]


@kb.add("c-h")
def _(event):
    """Ctrl+H: Delete character backward."""
    buf = event.app.current_buffer
    if buf.cursor_position > 0:
        buf.text = buf.text[:buf.cursor_position - 1] + buf.text[buf.cursor_position:]
        buf.cursor_position -= 1


@kb.add("c-f")
def _(event):
    """Ctrl+F: Forward character."""
    buf = event.app.current_buffer
    if buf.cursor_position < len(buf.text):
        buf.cursor_position += 1


@kb.add("c-b")
def _(event):
    """Ctrl+B: Backward character."""
    buf = event.app.current_buffer
    if buf.cursor_position > 0:
        buf.cursor_position -= 1


@kb.add("escape")
def _(event):
    """Escape: Cancel input / close modal."""
    buf = event.app.current_buffer
    if buf.text:
        buf.reset()
    else:
        event.app.exit()


@kb.add("tab")
def _(event):
    """Tab: Toggle Plan/Build mode (handled by app)."""
    pass  # Handled by app via callback


@kb.add("c-n")
def _(event):
    """Ctrl+N: New session (handled by app)."""
    pass  # Handled by app via callback


@kb.add("c-s")
def _(event):
    """Ctrl+S: Session picker (handled by app)."""
    pass  # Handled by app via callback


@kb.add("c-p")
def _(event):
    """Ctrl+P: Model picker (handled by app)."""
    pass  # Handled by app via callback


@kb.add("c-r")
def _(event):
    """Ctrl+R: Reverse search (handled by prompt_toolkit)."""
    pass  # Handled by prompt_toolkit search


@kb.add("c-t")
def _(event):
    """Ctrl+T: Transcript overlay (handled by app)."""
    pass  # Handled by app via callback


@kb.add("c-m")
def _(event):
    """Ctrl+M: Markdown preview (handled by app)."""
    pass  # Handled by app via callback
