from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView, ListItem, Label

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""

class Sidebar(ListView):
    def compose(self) -> ComposeResult:
        yield ListItem(Label("One"))
        yield ListItem(Label("Two"))
        yield ListItem(Label("Three"))

class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "app.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        yield Static(TEXT * 10, id="body")
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == "__main__":
    app = GroveApp()
    app.run()
