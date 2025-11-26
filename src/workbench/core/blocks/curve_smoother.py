import numpy as np
from scipy.interpolate import splrep, splev
from threading import Lock, Condition, Thread
import logging

from ..media_blocks import Block
from ..media_info import MediaInfo, ChannelInfo
from ..helpers.registry import register_block
from ..helpers.define_port_decorator import define_ports

LOGGER = logging.getLogger(__name__)

@register_block
@define_ports(inputs=["in-db"], outputs=["out-db-smooth"])
class CurveSmoother(Block):
    """
    Smooths a noisy frequency spectrum using a B-Spline in a separate thread.
    
    This block fits a cubic spline to the input data, providing a
    mathematically smooth curve. The fitting is done in a worker thread
    to avoid blocking the media graph.
    """

    def __init__(self, name: str, smoothness: float = 0.5, db_floor: float = -120.0) -> None:
        super().__init__(name)
        
        # --- Threading and Synchronization ---
        self._lock = Lock()
        self._condition = Condition()
        self._thread = None
        self._is_running = False
        
        # --- Shared Data ---
        # This holds the *most recent* data frame
        self._latest_frame = None
        self._new_data_available = False
        
        # --- Internal State (protected by lock) ---
        self._log_freq_axis_for_fit = None
        self._out_media_info = None
        self._smoothness_s = max(0, smoothness)
        self._db_floor = db_floor
        self._n_bins = 0


    def on_format_received(self, port_name: str, media_info: MediaInfo):
        """
        Called when the input format is known.
        We pre-calculate the frequency axis to fit against.
        """
        with self._lock:
            # 1. Get metadata from the input
            try:
                fft_size = media_info.metadata['fft_size']
                audio_sr = media_info.metadata['audio_samplerate']
            except KeyError:
                LOGGER.error(f"{self.name}: Input is missing 'fft_size' or "
                             "'audio_samplerate' metadata. Cannot create x-axis.")
                self._log_freq_axis_for_fit = None
                return
            
            self._n_bins = media_info.blocksize
                
            # 2. Generate and store the full linear frequency axis
            linear_freq_axis = np.fft.rfftfreq(fft_size, d=1.0 / audio_sr)
            
            # 3. Create the log-frequency axis specifically for spline fitting (excluding DC)
            self._log_freq_axis_for_fit = np.log10(linear_freq_axis[1:] + 1e-20)
            
            # 4. Set our output format (it's identical to the input)
            self._out_media_info = media_info.copy()
            self.set_port_format("out-db-smooth", self._out_media_info)
            LOGGER.debug(f"{self.name}: X-axis prepared for spline fitting.")

    def on_input_received(self, port_name: str, data: np.ndarray):
        """
        This is the FAST, NON-BLOCKING callback.
        """
        # Try to acquire the lock. If we can't, just drop the frame.
        if self._lock.acquire(blocking=False):
            try:
                # Store the most recent frame, overwriting any old one
                self._latest_frame = data
                self._new_data_available = True
            finally:
                # Ensure the lock is always released
                self._lock.release()
            
            # Wake up the worker thread
            with self._condition:
                self._condition.notify()
        # else:
            # LOGGER.debug(f"{self.name}: Dropped frame due to contention") # Too noisy
            pass # Lock was held, so we just drop the frame.

    def _run(self):
        """
        This is the worker thread's main loop.
        It waits for data, then runs the heavy spline fit.
        """
        LOGGER.debug(f"{self.name}: Worker thread started.")
        while self._is_running:
            frame_to_process = None
            
            # --- Wait for new data ---
            with self._condition:
                while not self._new_data_available and self._is_running:
                    self._condition.wait()
                
                if not self._is_running:
                    break
            
            # --- Grab the latest frame ---
            with self._lock:
                if self._new_data_available:
                    frame_to_process = self._latest_frame
                    self._new_data_available = False # We've "consumed" it
            
            # --- Do the heavy work (outside the lock) ---
            if frame_to_process is not None:
                self._process_frame(frame_to_process)
        
        LOGGER.debug(f"{self.name}: Worker thread stopped.")

    def _process_frame(self, data: np.ndarray):
        """
        This is the HEAVY logic, moved from the old on_input_received.
        It's called by the worker thread.
        """
        # We still need to lock to safely access shared config
        with self._lock:
            if self._log_freq_axis_for_fit is None or self._n_bins == 0:
                return # Not initialized
            
            # Copy config values to local vars so we can release the lock
            # (though in this case, the work is so fast after grabbing
            # the lock, we can just hold it)
            n_channels = data.shape[1]
            output_curve = np.zeros_like(data)

            for i in range(n_channels):
                try:
                    y_data_for_fit = data[1:, i] # Exclude DC
                    
                    # 1. Fit
                    tck = splrep(self._log_freq_axis_for_fit, y_data_for_fit, 
                                 s=self._smoothness_s, k=3)
                    
                    # 2. Evaluate
                    smooth_y_data = splev(self._log_freq_axis_for_fit, tck)
                    
                    # 3. Construct output
                    output_curve[0, i] = data[0, i] # Pass-through DC
                    output_curve[1:, i] = smooth_y_data
                    
                except Exception as e:
                    # Don't log on every frame, too noisy
                    # LOGGER.error(f"{self.name}: Spline fit failed: {e}")
                    return
                    output_curve[:, i] = data[:, i] # Pass-through

            # Apply dB floor
            np.clip(output_curve, self._db_floor, None, out=output_curve)
            
            # --- Send data from the worker thread ---
            self.send_port_data("out-db-smooth", output_curve)


    def on_start(self):
        with self._lock:
            self._is_running = True
            self._new_data_available = False
            self._latest_frame = None
            
        self._thread = Thread(name=f"{self.name}-worker", target=self._run)
        self._thread.start()
        return True

    def on_stop(self):
        with self._lock:
            self._is_running = False
        
        with self._condition:
            self._condition.notify_all() # Wake up thread to exit
            
        if self._thread:
            self._thread.join()
            self._thread = None
        return True

    @property
    def smoothness(self) -> float:
        return self._smoothness_s
    
    @smoothness.setter
    def smoothness(self, value: float):
        with self._lock:
            self._smoothness_s = max(0, value)
        LOGGER.debug(f"{self.name}: Smoothness set to {self._smoothness_s}")
        
    @property
    def db_floor(self) -> float:
        return self._db_floor
    
    @db_floor.setter
    def db_floor(self, value: float):
        with self._lock:
            self._db_floor = value
        LOGGER.debug(f"{self.name}: dB floor set to {self._db_floor}")
