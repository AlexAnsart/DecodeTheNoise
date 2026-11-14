"""What each actor of a workspace says on average: one summed vector per actor. Pure."""

import numpy as np

_INITIAL = 64


class ActorIndex:
    def __init__(self, dims: int) -> None:
        self.ids: list[str] = []
        self.rows: dict[str, int] = {}
        self.sums = np.zeros((_INITIAL, dims), dtype=np.float32)
        self.counts = np.zeros(_INITIAL, dtype=np.int32)
        # Milliseconds of the first and last dated item; 0 while the actor has none.
        self.first = np.zeros(_INITIAL, dtype=np.float64)
        self.last = np.zeros(_INITIAL, dtype=np.float64)

    def _row(self, actor_id: str) -> int:
        row = self.rows.get(actor_id)
        if row is not None:
            return row
        row = len(self.ids)
        if row == len(self.counts):
            self.sums = np.concatenate([self.sums, np.zeros_like(self.sums)])
            self.counts = np.concatenate([self.counts, np.zeros_like(self.counts)])
            self.first = np.concatenate([self.first, np.zeros_like(self.first)])
            self.last = np.concatenate([self.last, np.zeros_like(self.last)])
        self.ids.append(actor_id)
        self.rows[actor_id] = row
        return row

    def add(self, actor_id: str, vector: np.ndarray, ts: float) -> int:
        """Counts one more item for the actor; returns the actor's row."""
        row = self._row(actor_id)
        self.sums[row] += vector
        self.counts[row] += 1
        if ts > 0:
            self.first[row] = ts if self.first[row] == 0 else min(self.first[row], ts)
            self.last[row] = max(self.last[row], ts)
        return row

    def replace(self, row: int, old: np.ndarray, new: np.ndarray) -> None:
        """An item of the actor changed its text: its vector is swapped in the sum."""
        self.sums[row] += new - old

    def similar(self, row: int, top: int, minimum: int) -> list[tuple[str, float, int]]:
        """Other actors by cosine of the mean vectors, nearest first, among those with at
        least `minimum` items. Empty when this actor is itself under the minimum."""
        used = len(self.ids)
        if self.counts[row] < minimum:
            return []
        eligible = np.flatnonzero(self.counts[:used] >= minimum)
        eligible = eligible[eligible != row]
        if len(eligible) == 0:
            return []
        means = self.sums[eligible]
        means = means / np.maximum(np.linalg.norm(means, axis=1, keepdims=True), 1e-12)
        own = self.sums[row] / max(float(np.linalg.norm(self.sums[row])), 1e-12)
        scores = means @ own
        order = np.argsort(-scores, kind="stable")[:top]
        return [
            (self.ids[eligible[i]], float(scores[i]), int(self.counts[eligible[i]])) for i in order
        ]
