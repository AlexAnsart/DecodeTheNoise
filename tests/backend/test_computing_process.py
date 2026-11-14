"""The process layouts are computed in: apart from the API, one task at a time."""

import os
import threading

from computing_tasks import die, spend

from backend.refresh.computing import ComputingProcess


def test_tasks_run_one_at_a_time_in_another_process() -> None:
    """Two layouts at once gave corrupted indices on the server: they must never overlap."""
    computing = ComputingProcess()
    results: list[tuple[float, float, int]] = []
    threads = [
        threading.Thread(target=lambda: results.append(computing.run(spend, 0.2))) for _ in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    computing.close()

    spans = sorted(results)
    assert all(pid != os.getpid() for _, _, pid in spans)
    assert len({pid for _, _, pid in spans}) == 1
    assert all(later[0] >= earlier[1] for earlier, later in zip(spans, spans[1:], strict=False))


def test_a_dead_process_is_replaced() -> None:
    computing = ComputingProcess()
    first = computing.run(spend, 0.0)[2]
    computing.start(die)

    again = computing.run(spend, 0.0)[2]
    computing.close()

    assert again != first
