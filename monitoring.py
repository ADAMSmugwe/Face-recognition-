import time
from collections import defaultdict
from typing import Dict, List


class Metrics:
    def __init__(self) -> None:
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)

    def inc(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def time(self, name: str, duration: float) -> None:
        self.timers[name].append(duration)

    def timer(self, name: str):
        start = time.time()
        class _T:
            def __enter__(_self):
                return _self
            def __exit__(_self, exc_type, exc, tb):
                elapsed = time.time() - start
                self.time(name, elapsed)
        return _T()

    def export(self) -> Dict[str, object]:
        return {
            "counters": dict(self.counters),
            "timers": {k: {"count": len(v), "avg": (sum(v)/len(v) if v else 0.0)} for k, v in self.timers.items()},
        }

metrics = Metrics()


