"""Re-export widgets from pyggets for backward compatibility."""

from pyggets import (  # noqa: F401
    Button,
    Checkbox,
    Dropdown,
    HBox,
    Label,
    Modal,
    Panel,
    ProgressBar,
    RadioGroup,
    Rect,
    ScrollBox,
    Separator,
    Slider,
    Spacer,
    Style,
    TextInput,
    Toggle,
    Tooltip,
    VBox,
    Widget,
    brighten,
    get_default_theme,
)

# Expose _Box for any internal subclassing
from pyggets.containers import _Box  # noqa: F401, PLC2701
