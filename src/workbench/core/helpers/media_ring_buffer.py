from dvg_ringbuffer import RingBuffer


class MediaRingBuffer(RingBuffer):
    def reduce(self, n):
        if len(self) < n:
            raise IndexError(
                f"Out of range. The ring buffer has only "
                f"{len(self)} items. You requested {n}"
            )
        res = self._unwrap()[:n]
        self._unwrap_buffer_is_dirty = True
        self._idx_L += n
        self._fix_indices()
        return res
