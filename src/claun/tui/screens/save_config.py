"""Save configuration modal dialog."""

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from claun.core.config import ScheduleConfig


class SaveConfigModal(ModalScreen[Optional[str]]):
    """Modal dialog for saving configuration to JSON file."""

    CSS = """
    SaveConfigModal {
        align: center middle;
    }

    #modal-container {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick #FF5910;
        background: #0d0d18;
    }

    #modal-title {
        text-align: center;
        color: #FF5910;
        text-style: bold;
        margin-bottom: 1;
    }

    #path-label {
        margin-bottom: 0;
        color: #888;
    }

    #path-input {
        width: 100%;
        margin-bottom: 1;
        border: solid #002D72;
    }

    #path-input:focus {
        border: solid #FF5910;
    }

    #button-row {
        align: center middle;
        height: 3;
    }

    #save-btn {
        margin-right: 2;
        background: #FF5910;
    }

    #cancel-btn {
        background: #002D72;
    }

    #error-label {
        color: #FF0000;
        text-align: center;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "save", "Save", show=False),
    ]

    def __init__(
        self,
        config: ScheduleConfig,
        default_path: str = ".claun.json",
    ) -> None:
        super().__init__()
        self.config = config
        self.default_path = default_path

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("Save Configuration", id="modal-title")
            yield Label("File path:", id="path-label")
            yield Input(value=self.default_path, id="path-input")
            yield Static("", id="error-label")
            with Horizontal(id="button-row"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the input when modal opens."""
        self.query_one("#path-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._do_save()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        self._do_save()

    def _do_save(self) -> None:
        """Save config to file."""
        path_input = self.query_one("#path-input", Input)
        error_label = self.query_one("#error-label", Static)

        path_str = path_input.value.strip()
        if not path_str:
            error_label.update("Please enter a file path")
            return

        path = Path(path_str)
        try:
            self.config.save_to_file(path)
            self.dismiss(path_str)
        except Exception as e:
            error_label.update(f"Error: {e}")
