"""A software CAN bus: FIFO queue with optional frame loss and bit corruption.

Used to test the receiver's robustness (lost frames, corrupted payloads) the way the
brief asks for 'sensor noise, power cycles, link drops' without needing the hardware.
"""
from collections import deque
import random
from .can_protocol import CanFrame


class VirtualCanBus:
    def __init__(self, loss_rate=0.0, corrupt_rate=0.0, seed=7):
        self._q = deque()
        self.loss_rate, self.corrupt_rate = loss_rate, corrupt_rate
        self._rng = random.Random(seed)
        self.sent = self.dropped = self.corrupted = 0

    def send(self, frame: CanFrame):
        self.sent += 1
        if self._rng.random() < self.loss_rate:
            self.dropped += 1
            return
        if self._rng.random() < self.corrupt_rate:
            data = bytearray(frame.data)
            data[self._rng.randrange(7)] ^= 1 << self._rng.randrange(8)   # flip one payload bit
            frame = CanFrame(frame.can_id, bytes(data), frame.timestamp)
            self.corrupted += 1
        self._q.append(frame)

    def receive(self):
        return self._q.popleft() if self._q else None

    def __len__(self):
        return len(self._q)
