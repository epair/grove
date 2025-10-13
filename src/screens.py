"""Modal screens for Grove application."""

from textual.app import ComposeResult
from textual.widgets import Label, Input, Button, Checkbox
from textual.containers import Center, Vertical, Horizontal
from textual.screen import ModalScreen


class WorktreeFormScreen(ModalScreen[dict[str, str] | None]):
    """A modal screen for creating new worktrees."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the form layout."""
        with Vertical(id="dialog"):
            yield Label("Create New Worktree", id="title")
            yield Label("Name:")
            yield Input(placeholder="Enter worktree name", id="name_input")
            yield Label("Prefix:")
            yield Input(value="ep/", placeholder="ep/", id="prefix_input")
            with Horizontal(id="worktree_button_container"):
                yield Button("Cancel", variant="default", id="cancel_button")
                yield Button("Create", variant="primary", id="create_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "create_button":
            prefix = self.query_one("#prefix_input", Input).value
            name = self.query_one("#name_input", Input).value

            if not name.strip():
                return  # Don't submit if name is empty

            self.dismiss({"prefix": prefix, "name": name})
        elif event.button.id == "cancel_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "name_input":
            # Trigger create button when Enter is pressed in name field
            prefix = self.query_one("#prefix_input", Input).value
            name = event.input.value

            if name.strip():
                self.dismiss({"prefix": prefix, "name": name})

    def action_cancel(self) -> None:
        """Cancel the form and return to main app."""
        self.dismiss(None)


class ConfirmDeleteScreen(ModalScreen[bool]):
    """A modal screen for confirming worktree deletion."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No")
    ]

    def __init__(self, worktree_name: str) -> None:
        super().__init__()
        self.worktree_name = worktree_name

    def compose(self) -> ComposeResult:
        """Create the confirmation dialog layout."""
        with Vertical(id="delete_dialog"):
            yield Label("Delete Worktree", id="delete_title")
            yield Label(f"Are you sure you want to delete '{self.worktree_name}'?", id="delete_message")
            yield Label("This action cannot be undone.", id="delete_warning")
            with Horizontal(id="delete_button_container"):
                yield Button("No (n)", variant="default", id="no_button")
                yield Button("Yes (y)", variant="error", id="yes_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "yes_button":
            self.dismiss(True)
        elif event.button.id == "no_button":
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)


class PRFormScreen(ModalScreen[dict[str, str | list[str]] | None]):
    """A modal screen for creating a pull request."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the PR form layout."""
        with Vertical(id="pr_dialog"):
            yield Label("Create Pull Request", id="pr_title")
            yield Label("PR Title:")
            yield Input(placeholder="Enter PR title", id="pr_title_input")
            yield Label("Select Reviewers:", id="reviewers_label")

            # Two-column layout for reviewers
            with Horizontal(id="reviewers_container"):
                with Vertical(classes="reviewer_column"):
                    yield Checkbox("njm", value=True, id="checkbox_njm")
                    yield Checkbox("swlkr", id="checkbox_swlkr")
                    yield Checkbox("daviswahl", id="checkbox_daviswahl")
                with Vertical(classes="reviewer_column"):
                    yield Checkbox("BryceFrye", id="checkbox_BryceFrye")
                    yield Checkbox("neddenriep", id="checkbox_neddenriep")
                    yield Checkbox("gorilla076", id="checkbox_gorilla076")

            with Horizontal(id="pr_button_container"):
                yield Button("Cancel", variant="default", id="cancel_pr_button")
                yield Button("Create PR", variant="primary", id="create_pr_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "create_pr_button":
            title = self.query_one("#pr_title_input", Input).value

            if not title.strip():
                return  # Don't submit if title is empty

            # Collect selected reviewers
            reviewers = []
            for reviewer in ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]:
                checkbox = self.query_one(f"#checkbox_{reviewer}", Checkbox)
                if checkbox.value:
                    reviewers.append(reviewer)

            self.dismiss({"title": title, "reviewers": reviewers})
        elif event.button.id == "cancel_pr_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "pr_title_input":
            title = event.input.value

            if title.strip():
                # Collect selected reviewers
                reviewers = []
                for reviewer in ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]:
                    checkbox = self.query_one(f"#checkbox_{reviewer}", Checkbox)
                    if checkbox.value:
                        reviewers.append(reviewer)

                self.dismiss({"title": title, "reviewers": reviewers})

    def action_cancel(self) -> None:
        """Cancel the form and return to main app."""
        self.dismiss(None)