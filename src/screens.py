"""Modal screens for Grove application."""

from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Label, Input, Button, Checkbox, ListView, ListItem
from textual.containers import Vertical, Horizontal
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


class SetupWizardScreen(ModalScreen[str | None]):
    """A modal screen for first-time setup to configure repository path."""

    BINDINGS = [
        ("escape", "cancel", "Exit"),
        ("c", "custom_path", "Custom path"),
    ]

    def __init__(self, detected_repos: list[Path]) -> None:
        """Initialize the setup wizard.

        Args:
            detected_repos: List of auto-detected repository paths
        """
        super().__init__()
        self.detected_repos = detected_repos
        self.is_custom_mode = False

    def compose(self) -> ComposeResult:
        """Create the setup wizard layout."""
        with Vertical(id="setup_dialog"):
            yield Label("🌲 Grove Setup Wizard", id="setup_title")
            yield Label("No configuration found. Please select your repository:", id="setup_message")

            if self.detected_repos:
                yield Label(f"Detected {len(self.detected_repos)} potential repositories:", id="detected_label")
                # Create a ListView with detected repositories
                with ListView(id="repo_list"):
                    for repo in self.detected_repos:
                        yield ListItem(Label(str(repo)))
                yield Label("Press Enter to select, or press 'c' for custom path", id="setup_hint")
            else:
                yield Label("No repositories detected.", id="no_repos_label")
                yield Label("Press 'c' to enter a custom path", id="custom_hint")

            # Custom path input (initially hidden)
            yield Label("Enter repository path:", id="custom_label", classes="hidden")
            yield Input(placeholder="/path/to/repo", id="custom_input", classes="hidden")

            with Horizontal(id="setup_button_container"):
                yield Button("Exit (Esc)", variant="default", id="exit_button")
                yield Button("Confirm", variant="primary", id="confirm_button", classes="hidden")

    def action_custom_path(self) -> None:
        """Switch to custom path entry mode."""
        self.is_custom_mode = True

        # Hide repo list and show custom input
        try:
            self.query_one("#repo_list").add_class("hidden")
            self.query_one("#detected_label").add_class("hidden")
            self.query_one("#setup_hint").add_class("hidden")
        except Exception:
            # Elements might not exist if no repos detected
            pass

        try:
            self.query_one("#no_repos_label").add_class("hidden")
            self.query_one("#custom_hint").add_class("hidden")
        except Exception:
            # Elements might not exist if repos were detected
            pass

        self.query_one("#custom_label").remove_class("hidden")
        self.query_one("#custom_input").remove_class("hidden")
        self.query_one("#confirm_button").remove_class("hidden")

        # Focus the input
        self.query_one("#custom_input", Input).focus()

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """Handle selection from detected repositories list."""
        # Get the index of the selected item and use it to get the path from our list
        list_view = self.query_one("#repo_list", ListView)
        selected_index = list_view.index
        if selected_index is not None and selected_index < len(self.detected_repos):
            selected_path = str(self.detected_repos[selected_index])
            self.dismiss(selected_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm_button":
            custom_path = self.query_one("#custom_input", Input).value.strip()

            if not custom_path:
                self.notify("Please enter a path", severity="warning")
                return

            # Validate path
            path_obj = Path(custom_path).expanduser()
            if not path_obj.exists():
                self.notify(f"Path does not exist: {custom_path}", severity="error")
                return

            if not (path_obj / ".bare").is_dir():
                self.notify(f"Path does not contain .bare directory: {custom_path}", severity="error")
                return

            self.dismiss(str(path_obj.resolve()))
        elif event.button.id == "exit_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in custom path input."""
        if event.input.id == "custom_input":
            custom_path = event.input.value.strip()

            if not custom_path:
                self.notify("Please enter a path", severity="warning")
                return

            path_obj = Path(custom_path).expanduser()
            if not path_obj.exists():
                self.notify(f"Path does not exist: {custom_path}", severity="error")
                return

            if not (path_obj / ".bare").is_dir():
                self.notify(f"Path does not contain .bare directory: {custom_path}", severity="error")
                return

            self.dismiss(str(path_obj.resolve()))

    def action_cancel(self) -> None:
        """Exit the wizard."""
        self.dismiss(None)


class RepositorySelectionScreen(ModalScreen[str | None]):
    """A modal screen for selecting a repository from a list."""

    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("q", "quit", "Quit"),
        ("a", "add_repository", "Add Repository"),
        ("d", "delete_repository", "Delete Repository"),
        ("j", "cursor_down", "Move down"),
        ("k", "cursor_up", "Move up"),
    ]

    def __init__(self, repositories: list[dict[str, str]]) -> None:
        """Initialize with list of repositories.

        Args:
            repositories: List of Repository dicts with 'name' and 'path' keys
        """
        super().__init__()
        self.repositories = repositories

    def compose(self) -> ComposeResult:
        """Create the selection screen layout."""
        with Vertical(id="selection_dialog"):
            yield Label("Select Repository", id="selection_title")

            if self.repositories:
                with ListView(id="selection_repo_list"):
                    for repo in self.repositories:
                        # Display name on first line, path on second (indented)
                        repo_label = f"{repo['name']}\n  {repo['path']}"
                        yield ListItem(Label(repo_label))
                yield Label(
                    "[a] Add  [d] Delete  [q] Quit",
                    id="selection_help",
                )
            else:
                yield Label("No repositories configured", id="no_repos")
                yield Label("Press 'a' to add a repository", id="add_help")

            with Horizontal(id="selection_button_container"):
                yield Button("Quit (q)", variant="default", id="quit_button")

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """Handle repository selection."""
        list_view = self.query_one("#selection_repo_list", ListView)
        selected_index = list_view.index

        if selected_index is not None and selected_index < len(self.repositories):
            self.dismiss(self.repositories[selected_index]["path"])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "quit_button":
            self.dismiss(None)

    def action_add_repository(self) -> None:
        """Show add repository screen."""
        from .config import detect_potential_repositories, add_repository

        def handle_add_result(result: str | None) -> None:
            if result:
                # Add repository to config
                try:
                    add_repository(result)
                    self.notify(f"Added repository: {Path(result).name}")
                    # Refresh the screen by re-pushing with updated list
                    from .config import get_repositories

                    self.app.pop_screen()
                    self.app.push_screen(RepositorySelectionScreen(get_repositories()))
                except Exception as e:
                    self.notify(f"Failed to add repository: {e}", severity="error")

        # Detect potential repositories
        detected = detect_potential_repositories()
        self.app.push_screen(AddRepositoryScreen(detected), handle_add_result)

    def action_delete_repository(self) -> None:
        """Show delete confirmation for selected repository."""
        if not self.repositories:
            self.notify("No repositories to delete", severity="warning")
            return

        list_view = self.query_one("#selection_repo_list", ListView)
        selected_index = list_view.index

        if selected_index is None:
            self.notify("Please select a repository to delete", severity="warning")
            return

        from .config import remove_repository

        selected_repo = self.repositories[selected_index]

        def handle_delete_result(confirmed: bool) -> None:
            if confirmed:
                try:
                    remove_repository(selected_repo["path"])
                    self.notify(f"Removed repository: {selected_repo['name']}")
                    # Refresh the screen
                    from .config import get_repositories

                    self.app.pop_screen()
                    self.app.push_screen(RepositorySelectionScreen(get_repositories()))
                except Exception as e:
                    self.notify(f"Failed to remove repository: {e}", severity="error")

        self.app.push_screen(
            ConfirmDeleteRepositoryScreen(selected_repo["name"], selected_repo["path"]),
            handle_delete_result,
        )

    def action_quit(self) -> None:
        """Quit Grove."""
        self.dismiss(None)


class AddRepositoryScreen(ModalScreen[str | None]):
    """A modal screen for adding a new repository."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("c", "custom_path", "Custom path"),
    ]

    def __init__(self, detected_repos: list[Path]) -> None:
        """Initialize the add repository screen.

        Args:
            detected_repos: List of auto-detected repository paths
        """
        super().__init__()
        self.detected_repos = detected_repos
        self.is_custom_mode = False

    def compose(self) -> ComposeResult:
        """Create the add repository screen layout."""
        with Vertical(id="add_repo_dialog"):
            yield Label("Add Repository", id="add_repo_title")
            yield Label("Select a repository to add:", id="add_repo_message")

            if self.detected_repos:
                yield Label(f"Detected {len(self.detected_repos)} potential repositories:", id="add_detected_label")
                with ListView(id="add_repo_list"):
                    for repo in self.detected_repos:
                        yield ListItem(Label(str(repo)))
                yield Label("Press Enter to select, or press 'c' for custom path", id="add_repo_hint")
            else:
                yield Label("No repositories detected.", id="add_no_repos_label")
                yield Label("Press 'c' to enter a custom path", id="add_custom_hint")

            # Custom path input (initially hidden)
            yield Label("Enter repository path:", id="add_custom_label", classes="hidden")
            yield Input(placeholder="/path/to/repo", id="add_custom_input", classes="hidden")

            with Horizontal(id="add_repo_button_container"):
                yield Button("Cancel (Esc)", variant="default", id="add_cancel_button")
                yield Button("Confirm", variant="primary", id="add_confirm_button", classes="hidden")

    def action_custom_path(self) -> None:
        """Switch to custom path entry mode."""
        self.is_custom_mode = True

        # Hide repo list and show custom input
        try:
            self.query_one("#add_repo_list").add_class("hidden")
            self.query_one("#add_detected_label").add_class("hidden")
            self.query_one("#add_repo_hint").add_class("hidden")
        except Exception:
            pass

        try:
            self.query_one("#add_no_repos_label").add_class("hidden")
            self.query_one("#add_custom_hint").add_class("hidden")
        except Exception:
            pass

        self.query_one("#add_custom_label").remove_class("hidden")
        self.query_one("#add_custom_input").remove_class("hidden")
        self.query_one("#add_confirm_button").remove_class("hidden")

        # Focus the input
        self.query_one("#add_custom_input", Input).focus()

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """Handle selection from detected repositories list."""
        list_view = self.query_one("#add_repo_list", ListView)
        selected_index = list_view.index
        if selected_index is not None and selected_index < len(self.detected_repos):
            selected_path = str(self.detected_repos[selected_index])
            self.dismiss(selected_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add_confirm_button":
            custom_path = self.query_one("#add_custom_input", Input).value.strip()

            if not custom_path:
                self.notify("Please enter a path", severity="warning")
                return

            # Validate path
            path_obj = Path(custom_path).expanduser()
            if not path_obj.exists():
                self.notify(f"Path does not exist: {custom_path}", severity="error")
                return

            if not (path_obj / ".bare").is_dir():
                self.notify(f"Path does not contain .bare directory: {custom_path}", severity="error")
                return

            self.dismiss(str(path_obj.resolve()))
        elif event.button.id == "add_cancel_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in custom path input."""
        if event.input.id == "add_custom_input":
            custom_path = event.input.value.strip()

            if not custom_path:
                self.notify("Please enter a path", severity="warning")
                return

            path_obj = Path(custom_path).expanduser()
            if not path_obj.exists():
                self.notify(f"Path does not exist: {custom_path}", severity="error")
                return

            if not (path_obj / ".bare").is_dir():
                self.notify(f"Path does not contain .bare directory: {custom_path}", severity="error")
                return

            self.dismiss(str(path_obj.resolve()))

    def action_cancel(self) -> None:
        """Cancel adding repository."""
        self.dismiss(None)


class ConfirmDeleteRepositoryScreen(ModalScreen[bool]):
    """A modal screen for confirming repository deletion."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
    ]

    def __init__(self, repo_name: str, repo_path: str) -> None:
        """Initialize the confirmation screen.

        Args:
            repo_name: Name of the repository
            repo_path: Path to the repository
        """
        super().__init__()
        self.repo_name = repo_name
        self.repo_path = repo_path

    def compose(self) -> ComposeResult:
        """Create the confirmation dialog layout."""
        with Vertical(id="delete_repo_dialog"):
            yield Label("Delete Repository", id="delete_repo_title")
            yield Label(f"Are you sure you want to remove:", id="delete_repo_message")
            yield Label(f"  {self.repo_name}", id="delete_repo_name")
            yield Label(f"  {self.repo_path}", id="delete_repo_path")
            yield Label("")  # Blank line
            yield Label("This only removes from config,", id="delete_repo_warning1")
            yield Label("files will not be deleted.", id="delete_repo_warning2")
            with Horizontal(id="delete_repo_button_container"):
                yield Button("No (n)", variant="default", id="no_repo_button")
                yield Button("Yes (y)", variant="error", id="yes_repo_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "yes_repo_button":
            self.dismiss(True)
        elif event.button.id == "no_repo_button":
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)