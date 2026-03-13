
import threading
import queue
import logging
import time
from adb_pywrapper.adb_device import AdbDevice

# Configuración del logger
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

class ADBWorker:
    """
    A class that manages ADB command execution in a separate thread,
    preventing the main thread from blocking and ensuring safe access to the device.

    Features:
    - Task queue for serializing commands.
    - Dedicated thread for processing tasks.
    - Configurable timeout for each command.
    - Integrated logging for debugging.
    - Graceful shutdown of the worker thread.

    If no serial is provided, it will attempt to connect to the first available device.
    """

    def __init__(self, device_serial: str = None):
        """
        Initialize the ADBWorker and start the processing thread.

        Args:
            device_serial (str, optional): ADB device serial. If None,
                                           it will try to use the first available device.
        """
        self.adb = None
        self.device_serial = device_serial
        self.q = queue.Queue()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        # self.thread.start()

        if device_serial:
            self._connect(device_serial)
        else:
            devices = AdbDevice.list_devices()
            if devices:
                self._connect(devices[0])
            else:
                LOGGER.warning("No ADB devices found. Use connect_first_available() or start_thread() later.")

    def _connect(self, serial: str):
        """Connect the ADBWorker to the specified device."""
        self.adb = AdbDevice(device=serial)
        self.device_serial = serial
        LOGGER.info(f"ADBWorker connected to device {serial}")

    def start_thread(self):
        LOGGER.info('Starting ADB thread')
        try:
            self.connect_first_available()
        except Exception as e:
            LOGGER.error(f'Error connecting: {e}')
            return False
        self.thread.start()
        return True

    
    def connect_first_available(self):
        """
        Attempt to connect to the first available device if no active connection exists.

        Raises:
            RuntimeError: If a device is already connected.
            Exception: If no devices are found.
        """
        if self.adb is not None:
            raise RuntimeError("A device is already connected.")
        devices = AdbDevice.list_devices()
        if not devices:
            raise Exception("No ADB devices available.")
        self._connect(devices[0])

    def _loop(self):
        """Main loop of the worker thread that processes tasks from the queue."""
        while not self._stop_event.is_set():
            try:
                func, args, kwargs, reply_q = self.q.get(timeout=0.5)
            except queue.Empty:
                continue

            if func is None:
                LOGGER.info("ADBWorker: shutdown requested")
                self.q.task_done()
                break

            start = time.time()
            try:
                out = func(*args, **kwargs)
                reply_q.put(("ok", out))
                LOGGER.info(f"Executed {func.__name__} in {time.time() - start:.2f}s")
            except Exception as e:
                reply_q.put(("err", e))
                LOGGER.error(f"Error executing {func.__name__}: {e}")
            finally:
                self.q.task_done()

    def submit(self, func, *args, timeout=None, **kwargs):
        """
        Submit a function to be executed by the ADBWorker thread.

        Args:
            func (callable): Function to execute (e.g., self.adb.shell).
            *args: Positional arguments for the function.
            timeout (float, optional): Maximum time in seconds to wait for the response.
            **kwargs: Keyword arguments for the function.

        Returns:
            Any: The return value of the executed function.

        Raises:
            TimeoutError: If the response does not arrive within the specified time.
            RuntimeError: If the worker is closed or no device is connected.
            Exception: If the function raises an exception.
        """
        if self._stop_event.is_set():
            raise RuntimeError("ADBWorker is already closed")
        if self.adb is None:
            raise RuntimeError("No device connected. Use connect_first_available().")

        reply_q = queue.Queue()
        self.q.put((func, args, kwargs, reply_q))

        try:
            status, payload = reply_q.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"Timeout waiting for response from {func.__name__}")

        if status == "err":
            raise payload
        return payload

    def shell(self, cmd: str, timeout=None):
        """
        Execute a shell command on the connected ADB device.

        Args:
            cmd (str): Command to execute (e.g., "ls /sdcard").
            timeout (float, optional): Maximum time in seconds to wait for the response.

        Returns:
            str: Output of the command.
        """
        return self.submit(self.adb.shell, cmd, timeout=timeout)

    def root(self, timeout=None):
        """
        Request root privileges on the connected ADB device.

        Args:
            timeout (float, optional): Maximum time in seconds to wait for the response.

        Returns:
            str: Result of the root command.
        """
        return self.submit(self.adb.root, timeout=timeout)

    def close(self):
        """
        Gracefully shut down the ADBWorker, stopping the thread and clearing the queue.

        This method should be called before destroying the object to avoid orphan threads.
        """
        LOGGER.info("Requesting ADBWorker shutdown...")
        try:
            self._stop_event.set()
            self.q.put((None, None, None, None))
            if self.thread.is_alive():
                self.thread.join()
            LOGGER.info("ADBWorker successfully closed")
            return True
        except Exception as e:
            LOGGER.error(f'Error closing: {e}')
            return False
