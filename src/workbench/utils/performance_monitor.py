from time import perf_counter
from dvg_ringbuffer import RingBuffer
import numpy as np
from .singleton import SingletonMeta
from engineering_notation import EngNumber


class PerformanceTimer:
    def __init__(self, name, buffer_size=1024) -> None:
        self.name = name
        self.buffer_size = buffer_size
        self.start_buf = RingBuffer(buffer_size)
        self.stop_buf = RingBuffer(buffer_size)

    def mark_start(self) -> None:
        self.start_buf.append(perf_counter())

    def mark_stop(self) -> None:
        self.stop_buf.append(perf_counter())

    def get_stats(self) -> dict:
        stats = {}
        if len(self.start_buf) > 0:
            stats["start"] = self._calulate_stats(np.diff(self.start_buf))
        if len(self.stop_buf) > 0:
            stats["stop"] = self._calulate_stats(np.diff(self.stop_buf))
        if len(self.start_buf) == len(self.stop_buf):
            stats["diff"] = self._calulate_stats(
                np.subtract(self.stop_buf, self.start_buf)
            )
        return stats

    def _calulate_stats(self, data) -> dict:
        stats = {}
        stats["mean"] = np.mean(data) if len(data) > 0 else "N/A"
        stats["min"] = np.min(data) if len(data) > 0 else "N/A"
        stats["max"] = np.max(data) if len(data) > 0 else "N/A"
        stats["std"] = np.std(data) if len(data) > 0 else "N/A"
        return stats

    def __str__(self) -> str:
        stats = self.get_stats()
        tmp = ""
        for group_key, group in stats.items():
            tmp += f"{group_key}\n    "
            tmp += (
                ", ".join(
                    [f"{key}: {EngNumber(value)}" for key, value in group.items()]
                )
                + "\n  "
            )

        return f"PerformanceTimer {self.name}\n  {tmp}"


class PerformanceMonitorService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.timers = {}
        print("PerformanceMonitorService Created")

    def new_timer(self, name, buffer_size=1024) -> PerformanceTimer:
        timer = PerformanceTimer(name, buffer_size)
        self.timers[timer] = timer
        return timer

    def dump(self) -> None:
        print("PerformanceMonitorService Dump")
        for timer in self.timers:
            print(timer)
