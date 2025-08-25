import sys

# Make sure all necessary PySide6 modules are imported
from PySide6.QtWidgets import QApplication

# Import your MainWindow class from its new, organized location
from workbench.ui.views.main_window import MainWindow
from workbench.utils.logger import configure_logger
from workbench.utils.performance_monitor import (
    PerformanceMonitorService,
)


def main():
    """
    The main function to initialize and launch the Measurement Workbench application.
    """
    # It's good practice to configure logging as the first step
    configure_logger()

    # Start performance monitor service
    perf_monitor_service = PerformanceMonitorService()

    # 1. Create the Qt Application instance. This is required for any GUI.
    app = QApplication(sys.argv)

    # 3. Create an instance of your main window
    #    This is the main UI of your application.
    window = MainWindow()

    # 4. Show the main window to the user
    window.show()

    # 5. Start the Qt event loop. This call is blocking and will run until
    #    the user closes the application. The return value is the exit code.
    exit_code = app.exec()

    # dump peformance monitor statistics
    perf_monitor_service.dump()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
