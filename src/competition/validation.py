import random


def assign_folds(row_count: int, folds: int, seed: int) -> list[int]:
    indices = list(range(row_count))
    random.Random(seed).shuffle(indices)
    assignments = [0] * row_count
    for position, index in enumerate(indices):
        assignments[index] = position % folds
    return assignments
