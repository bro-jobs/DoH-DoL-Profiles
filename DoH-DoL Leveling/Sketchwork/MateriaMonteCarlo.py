import numpy as np
from typing import NamedTuple
import matplotlib.pyplot as plt
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MeldAttempt:
    success_rate: float
    quantity: int
    materia_name: str
    slot: str


def simulate_melds(meld_attempts: list[MeldAttempt], n_simulations: int = 10000) -> tuple[np.ndarray, dict]:
    """
    Run Monte Carlo simulation for materia melding.
    Returns array of total materia used per simulation and dictionary of materia used by type.
    """
    total_materia_per_sim = np.zeros(n_simulations)
    materia_by_type = defaultdict(lambda: np.zeros(n_simulations))

    for sim in range(n_simulations):
        materia_used = 0
        materia_counts = defaultdict(int)

        for attempt in meld_attempts:
            # For each required successful meld
            successes_needed = attempt.quantity
            attempts_this_meld = 0

            while successes_needed > 0:
                attempts_this_meld += 1
                # Check if meld succeeded
                if np.random.random() < attempt.success_rate:
                    successes_needed -= 1

            materia_used += attempts_this_meld
            materia_counts[attempt.materia_name] += attempts_this_meld

        total_materia_per_sim[sim] = materia_used
        for materia_name, count in materia_counts.items():
            materia_by_type[materia_name][sim] = count

    return total_materia_per_sim, dict(materia_by_type)


def calculate_statistics(results: np.ndarray) -> tuple[float, list[float]]:
    """Calculate mean and specified percentiles."""
    mean = np.mean(results)
    percentiles = np.percentile(results, [50, 75, 90, 95])
    return mean, percentiles


def main():
    # Define melding attempts
    meld_attempts = [
        MeldAttempt(1.0, 33, "Command XII", "guaranteed"),
        MeldAttempt(0.17, 20, "Command XII", "overmeld 1"),
        MeldAttempt(0.17, 2, "Cunning XII", "overmeld 1"),
        MeldAttempt(0.17, 4, "Competence XII", "overmeld 1"),
        MeldAttempt(0.10, 23, "Command XI", "overmeld 2"),
        MeldAttempt(0.10, 3, "Competence XI", "overmeld 2"),
        MeldAttempt(0.07, 17, "Command XI", "overmeld 3"),
        MeldAttempt(0.07, 6, "Competence XI", "overmeld 3"),
        MeldAttempt(0.07, 3, "Cunning IX", "overmeld 3"),
        MeldAttempt(0.05, 21, "Cunning IX", "overmeld 4")
    ]

    # Run simulation
    n_sims = 10000
    results, materia_by_type = simulate_melds(meld_attempts, n_sims)

    # Calculate overall statistics
    mean, percentiles = calculate_statistics(results)

    print(f"\nResults from {n_sims} simulations:")
    print(f"Expected total materia needed: {mean:.1f}")
    print(f"Percentiles for total materia:")
    print(f"  50th: {percentiles[0]:.1f}")
    print(f"  75th: {percentiles[1]:.1f}")
    print(f"  90th: {percentiles[2]:.1f}")
    print(f"  95th: {percentiles[3]:.1f}")

    # List of all unique materia types
    materia_types = [
        "Command XII",
        "Command XI",
        "Cunning XII",
        "Cunning IX",
        "Competence XII",
        "Competence XI"
    ]

    print("\nBreakdown by individual materia type:")
    for materia_type in materia_types:
        if materia_type in materia_by_type:
            mean, percentiles = calculate_statistics(materia_by_type[materia_type])

            # Calculate guaranteed melds for this type
            guaranteed = sum(m.quantity for m in meld_attempts
                             if m.materia_name == materia_type and m.success_rate == 1)

            print(f"\n{materia_type}:")
            print(f"  Expected: {mean:.1f}")
            print(f"  50th percentile: {percentiles[0]:.1f}")
            print(f"  75th percentile: {percentiles[1]:.1f}")
            print(f"  90th percentile: {percentiles[2]:.1f}")
            print(f"  95th percentile: {percentiles[3]:.1f}")
            if guaranteed > 0:
                print(f"  Guaranteed melds: {guaranteed}")

            # Calculate non-guaranteed melds needed
            total_melds = sum(m.quantity for m in meld_attempts
                              if m.materia_name == materia_type)
            if total_melds - guaranteed > 0:
                print(f"  Additional melds needed: {total_melds - guaranteed}")


if __name__ == "__main__":
    main()