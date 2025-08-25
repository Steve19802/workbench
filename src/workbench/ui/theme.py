import logging
from pathlib import Path
import qdarktheme
import qtawesome

LOGGER = logging.getLogger(__name__)


class Theme:
    def __init__(self) -> None:
        self._stylesheet = self.read_stylesheet()
        self.change_theme()

    def read_stylesheet(self):
        """Reads a stylesheet file and applies it to the application."""
        qss_file = Path(__file__).parent / "resources/styles/style.qss"
        LOGGER.debug(f"loading stylesheet: '{qss_file}'")
        try:
            with open(qss_file, "r") as f:
                stylesheet = f.read()
                LOGGER.debug("Stylesheet loaded successfuly")
                return stylesheet
        except FileNotFoundError:
            LOGGER.error(f"Warning: Stylesheet file not found at '{qss_file}'")
            return ""

    def change_theme(self, theme="light"):
        LOGGER.debug(f"Changing theme to '{theme}'")
        qdarktheme.setup_theme(
            theme=theme, corner_shape="sharp", additional_qss=self._stylesheet
        )

        # new_palette: QPalette = cast(QPalette, qdarktheme.load_palette(theme=theme))
        # app: QApplication = cast(QApplication, QApplication.instance())
        # app.setPalette(new_palette)
        qtawesome.reset_cache()
