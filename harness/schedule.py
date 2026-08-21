"""Precompute interleaved, deterministic trial schedules."""

from __future__ import annotations

import random
from collections.abc import Iterable

from .bundle import Trial


def blocked_schedule(
    tasks: Iterable[str],
    conditions: Iterable[str],
    replicates: int,
    seed: int,
    *,
    reuse_generation_seed_across_conditions: bool = False,
) -> tuple[Trial, ...]:
    """Interleave every condition within each task/replicate block.

    The returned order is recorded before model work. A randomly selected base
    order rotates across replicates, so a complete cycle gives every condition
    every within-block position exactly once. Confirmation registrations must
    use a whole number of cycles or adjust for the remaining position imbalance.
    Reusing a generation seed across conditions is opt-in because it requires a
    recorded provider seed-support calibration before a real model run.
    """
    if replicates < 1:
        raise ValueError("replicates must be positive")
    task_names, condition_names = tuple(tasks), tuple(conditions)
    if not task_names or not condition_names or len(set(condition_names)) != len(condition_names):
        raise ValueError("tasks and unique conditions are required")
    rng = random.Random(seed)
    planned: list[Trial] = []
    for task in task_names:
        base_order = list(condition_names)
        rng.shuffle(base_order)
        for replicate in range(1, replicates + 1):
            rotation = (replicate - 1) % len(base_order)
            block = base_order[rotation:] + base_order[:rotation]
            shared_seed = rng.randrange(2**31)
            planned.extend(
                Trial(
                    task,
                    replicate,
                    condition,
                    shared_seed if reuse_generation_seed_across_conditions else rng.randrange(2**31),
                )
                for condition in block
            )
    return tuple(planned)
