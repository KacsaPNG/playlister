"""
Main Application Entry Point.
Initializes PyQt6 application, DualDeckAudioEngine, and runs the main event loop.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.audio.engine import DualDeckAudioEngine
from app.config import DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE
from app.gui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger("playlisterag")


def main():
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PlaylisterAG DJ")
    app.setOrganizationName("PlaylisterAG")

    logger.info("Initializing Dual-Deck Audio Engine...")
    engine = DualDeckAudioEngine(
        sample_rate=DEFAULT_SAMPLE_RATE,
        block_size=DEFAULT_BLOCK_SIZE,
    )

    logger.info("Creating Main Window...")
    window = MainWindow(engine)
    window.show()

    logger.info("DJ System running.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
