import pandas as pd
from typing import Tuple, List, Dict
from dataclasses import dataclass
from functools import lru_cache


# Generated by Claude. Did some robustness checks and should work correctly.

@dataclass
class PlayerState:
    level: int
    current_exp: int
    collectables_made: int
    crafting_history: List[Tuple[int, int]]  # (level_crafted_at, count)


@dataclass
class Breakpoint:
    level: int
    exp: int
    collectables_needed: int


class LevelOptimizer:
    def __init__(self, level_exp_file: str, synthesis_exp_file: str):
        """
        Initialize the optimizer with level requirements and synthesis exp data

        Parameters:
        level_exp_file (str): Path to CSV with level, exp columns
        synthesis_exp_file (str): Path to CSV with level2, exp2 columns
        """
        # Read CSVs
        self.level_exp_df = pd.read_csv(level_exp_file)
        self.synthesis_exp_df = pd.read_csv(synthesis_exp_file)

        # Helper function to safely convert column to int
        def safe_convert_to_int(series):
            if series.dtype == 'O':  # Object (string) type
                try:
                    return series.str.replace(',', '').astype(int)
                except AttributeError:
                    return series.astype(int)
            return series.astype(int)

        # Convert columns to integers, handling both string and numeric inputs
        self.level_exp_df['level'] = safe_convert_to_int(self.level_exp_df['level'])
        self.level_exp_df['exp'] = safe_convert_to_int(self.level_exp_df['exp'])
        self.synthesis_exp_df['level2'] = safe_convert_to_int(self.synthesis_exp_df['level2'])
        self.synthesis_exp_df['exp2'] = safe_convert_to_int(self.synthesis_exp_df['exp2'])

        # Create lookup dictionaries for faster access
        self.level_exp_dict = dict(zip(self.level_exp_df['level'], self.level_exp_df['exp']))
        self.synthesis_exp_dict = dict(zip(self.synthesis_exp_df['level2'], self.synthesis_exp_df['exp2']))

    def get_exp_to_next_level(self, level: int) -> int:
        """Get EXP needed for next level"""
        return self.level_exp_dict.get(level, float('inf'))

    def get_synthesis_exp(self, level: int) -> int:
        """Get synthesis EXP gained at a given level"""
        return self.synthesis_exp_dict.get(level, 0)

    def simulate_single_synthesis(self, state: PlayerState) -> Tuple[int, int]:
        """
        Simulate synthesizing one collectable and return resulting level and exp
        Returns: (new_level, new_exp)
        """
        current_level = state.level
        current_exp = state.current_exp

        synthesis_exp = self.get_synthesis_exp(current_level)
        current_exp += synthesis_exp

        # Check for level ups
        while True:
            exp_needed = self.get_exp_to_next_level(current_level)
            if current_exp >= exp_needed:
                current_exp -= exp_needed
                current_level += 1
            else:
                break

        return current_level, current_exp

    def simulate_synthesis_sequence(
            self,
            start_state: PlayerState,
            num_crafts: int
    ) -> PlayerState:
        """Simulate crafting multiple collectables in sequence"""
        current_level = start_state.level
        current_exp = start_state.current_exp

        # Track how many were crafted at each level
        crafts_at_level = 0
        crafting_history = start_state.crafting_history.copy()

        for _ in range(num_crafts):
            prev_level = current_level
            current_level, current_exp = self.simulate_single_synthesis(
                PlayerState(current_level, current_exp, 0, [])
            )

            # If level changed, record previous crafts and start new count
            if current_level != prev_level:
                if crafts_at_level > 0:
                    crafting_history.append((prev_level, crafts_at_level))
                crafts_at_level = 1
            else:
                crafts_at_level += 1

        # Record final crafts
        if crafts_at_level > 0:
            crafting_history.append((current_level, crafts_at_level))

        return PlayerState(
            level=current_level,
            current_exp=current_exp,
            collectables_made=start_state.collectables_made + num_crafts,
            crafting_history=crafting_history
        )

    def will_reach_target(
            self,
            state: PlayerState,
            target_level: int,
            turn_in_exp: int
    ) -> bool:
        """Check if current state plus turn-ins will reach target level"""
        current_level = state.level
        current_exp = state.current_exp

        # Add turn-in exp
        total_turn_in_exp = state.collectables_made * turn_in_exp
        current_exp += total_turn_in_exp

        # Simulate level ups from turn-ins
        while current_level < target_level:
            exp_needed = self.get_exp_to_next_level(current_level)
            if current_exp >= exp_needed:
                current_exp -= exp_needed
                current_level += 1
            else:
                break

        return current_level >= target_level

    def calculate_min_collectables(
            self,
            start_level: int,
            target_level: int,
            start_exp: int,
            turn_in_exp: int,
            max_collectables: int = 50
    ) -> Tuple[int, List[Tuple[int, int]]]:
        """
        Calculate minimum number of collectables needed using iterative deepening search

        Returns:
        Tuple[int, List[Tuple[int, int]]]:
            - Minimum number of collectables needed
            - List of (level, count) tuples showing when crafting occurred
        """
        if start_level >= target_level:
            return 0, []

        initial_state = PlayerState(start_level, start_exp, 0, [])

        # Try increasing numbers of collectables until we find a solution
        for num_collectables in range(1, max_collectables + 1):
            final_state = self.simulate_synthesis_sequence(initial_state, num_collectables)

            if self.will_reach_target(final_state, target_level, turn_in_exp):
                return num_collectables, final_state.crafting_history

        raise ValueError(f"Could not find solution within {max_collectables} collectables")

    def print_solution(
            self,
            start_level: int,
            target_level: int,
            start_exp: int,
            turn_in_exp: int
    ) -> None:
        """Print detailed solution including EXP calculations"""
        try:
            count, distribution = self.calculate_min_collectables(
                start_level, target_level, start_exp, turn_in_exp
            )

            print(f"Minimum collectables needed: {count}")
            print("\nCrafting distribution:")
            total_synthesis_exp = 0

            for level, num in distribution:
                synthesis_exp = self.get_synthesis_exp(level)
                level_exp = synthesis_exp * num
                total_synthesis_exp += level_exp
                print(f"Level {level}: Crafted {num} collectables for {level_exp:,} synthesis EXP")

            turn_in_total = count * turn_in_exp
            print(f"\nTotal synthesis EXP: {total_synthesis_exp:,}")
            print(f"Total turn-in EXP: {turn_in_total:,}")
            print(f"Total EXP gained: {(total_synthesis_exp + turn_in_total):,}")

        except ValueError as e:
            print(f"Error: {e}")

    @lru_cache(maxsize=1024)
    def find_collectables_needed(
            self,
            level: int,
            exp: int,
            target_level: int,
            turn_in_exp: int,
            max_collectables: int
    ) -> int:
        """Helper function to find collectables needed for a given state (now cached)"""
        try:
            count, _ = self.calculate_min_collectables(
                level, target_level, exp, turn_in_exp, max_collectables
            )
            return count
        except ValueError:
            return max_collectables + 1

    def find_exp_threshold_for_collectables(
            self,
            level: int,
            target_collectables: int,
            target_level: int,
            turn_in_exp: int,
            max_collectables: int,
            max_exp: int
    ) -> int:
        """Find minimum exp needed at this level to achieve target with target_collectables"""
        left, right = 0, max_exp
        result = max_exp + 1  # Default if no solution found

        while left <= right:
            mid = (left + right) // 2
            needed = self.find_collectables_needed(
                level, mid, target_level, turn_in_exp, max_collectables
            )

            if needed <= target_collectables:
                # This exp works, try lower
                result = mid
                right = mid - 1
            else:
                # Need more collectables, try higher exp
                left = mid + 1

        return result

    def find_breakpoints(
            self,
            target_level: int,
            turn_in_exp: int,
            max_collectables: int = 23
    ) -> List[Breakpoint]:
        """
        Find all breakpoints where number of required collectables changes

        Returns:
        List[Breakpoint]: List of (level, exp, collectables_needed) breakpoints
        """
        breakpoints = []
        min_level = max(1, target_level - max_collectables - 5)

        # Process levels from highest to lowest
        for current_level in range(target_level - 1, min_level - 1, -1):
            if current_level not in self.level_exp_dict:
                continue

            max_exp = self.level_exp_dict[current_level]

            # Find minimum collectables needed with max exp
            min_collectables = self.find_collectables_needed(
                current_level, max_exp, target_level, turn_in_exp, max_collectables
            )

            if min_collectables > max_collectables:
                continue

            # Find thresholds for increasing numbers of collectables
            prev_threshold = max_exp + 1
            for collectables in range(min_collectables, max_collectables + 1):
                threshold = self.find_exp_threshold_for_collectables(
                    current_level, collectables, target_level, turn_in_exp,
                    max_collectables, max_exp
                )

                if threshold > max_exp:
                    break

                if threshold < prev_threshold:
                    breakpoints.append(Breakpoint(
                        level=current_level,
                        exp=threshold,
                        collectables_needed=collectables
                    ))
                    prev_threshold = threshold

        # Sort by collectables, then level (descending), then exp (descending)
        return sorted(breakpoints, key=lambda x: (x.collectables_needed, -x.level, -x.exp))

    def print_breakpoints(
            self,
            target_level: int,
            turn_in_exp: int,
            max_collectables: int = 23
    ) -> None:
        """Print all breakpoints in a readable format"""
        breakpoints = self.find_breakpoints(target_level, turn_in_exp, max_collectables)

        print(f"\nBreakpoints to reach level {target_level}:")
        print("\nCollectables | Level | Starting EXP | EXP to Next Level")
        print("-" * 60)

        current_collectables = None
        for bp in breakpoints:
            exp_to_next = self.level_exp_dict.get(bp.level, 0)

            # Add blank line between different collectable counts
            if current_collectables is not None and bp.collectables_needed != current_collectables:
                print()

            print(f"{bp.collectables_needed:11d} | {bp.level:5d} | {bp.exp:,} | {exp_to_next:,}")
            current_collectables = bp.collectables_needed

        if not breakpoints:
            print("No valid breakpoints found")

    def generate_codechunk(self, target_level: int, turn_in_exp: int, max_collectables: int = 23) -> None:
        """Generate C# CodeChunk for determining collectable amount"""
        breakpoints = self.find_breakpoints(target_level, turn_in_exp, max_collectables)

        # Start building the CodeChunk
        print("<CodeChunk Name=\"SetLisbethJson\">")
        print("\t<![CDATA[")
        print(f"\t\tint amount = {max_collectables};")
        print("\t\tint level = Core.Me.Levels[ClassJobType.Alchemist];")
        print("\t\tint exp = (int)Experience.CurrentExperience;")
        print()
        print("\t\tamount = (level, exp) switch")
        print("\t\t{")

        # Group breakpoints by level
        current_level = None
        for bp in sorted(breakpoints, key=lambda x: (x.collectables_needed, -x.level, -x.exp)):
            if bp.level != current_level:
                # First condition for this level
                print(f"\t\t({bp.level}, > {bp.exp}) => {bp.collectables_needed},")
                current_level = bp.level
            else:
                print(f"\t\t({bp.level}, >= {bp.exp}) => {bp.collectables_needed},")

        # Add default case for lowest valid level
        if breakpoints:
            min_level = min(bp.level for bp in breakpoints)
            print(f"\t\t({min_level}, >= 0) => {max_collectables},")

        # Close the switch expression with default case
        print("\t\t_ => amount")
        print("\t\t};")
        print()
        print("\t\tif (Core.Me.HasAura(1411)) {")
        print("\t\t\tamount = (int)Math.Ceiling((amount + 1) / 2.0);")
        print("\t\t}")
        print()
        print(
            "\t\tff14bot.Helpers.Logging.Write($\"Estimated amount of collectables needed to level to next checkpoint: {amount}\");")
        print()
        print("\t\tvar lisbeth = BotManager.Bots.FirstOrDefault(c => c.Name == \"Lisbeth\");")
        print("\t\tif (lisbeth != null)")
        print("\t\t{")
        print("\t\t\tvar lisbethObject = lisbeth.GetType().GetProperty(\"Lisbeth\").GetValue(lisbeth);")
        print("\t\t\tif (lisbethObject != null)")
        print("\t\t\t{")
        print(
            "\t\t\t\tvar json = $\"[{{'Group':1,'Item':31919,'Amount':{amount},'Enabled':true,'Type':'Alchemist','Collectable':false}}]\";")
        print("\t\t\t\tvar orderMethod = lisbethObject.GetType().GetMethod(\"ExecuteOrders\");")
        print("\t\t\t\tawait (Task<bool>)orderMethod.Invoke(lisbethObject, new object[] { json, false });")
        print("\t\t\t}")
        print("\t\t}")
        print("\t]]>")
        print("</CodeChunk>")


optimizer_21 = LevelOptimizer("levels.csv", "lv20collect.csv")

# Lv 21 and above can craft Lv 20 collectable with 100% HQ.

# optimizer_21.generate_codechunk(target_level=41, turn_in_exp=67771)

optimizer_21_CUL = LevelOptimizer("levels.csv", "lv20CULcollect.csv")

# optimizer_21_CUL.generate_codechunk(target_level=41, turn_in_exp=67771)

# Lv 41-53 can only reliably craft to the first or second collectability rating.
# optimizer_41 is for: Lv41-49 BSM, ARM, GSM, LTW, ALC
optimizer_41 = LevelOptimizer("levels.csv", "lv40collect.csv")
# optimizer_41_HQ is for: Lv41-63 CRP, CUL
optimizer_41_HQ = LevelOptimizer("levels.csv", "lv40HQcollect.csv")

optimizer_41_HQ.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=39)
# optimizer_41_WVR is for: Lv41-63 WVR
optimizer_41_WVR = LevelOptimizer("levels.csv", "lv40WVRcollect.csv")

optimizer_41_WVR.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=38)
# CRP, CUL, and WVR should be leveled to 63 first: they can hit Lv3 collectability
# because of HQ mat.

optimizer_41.generate_codechunk(target_level=50, turn_in_exp=177985, max_collectables=10)

#optimizer_50 is for: Lv50-53 BSM, ARM, GSM, LTW, ALC
optimizer_50 = LevelOptimizer("levels.csv", "lv40bcollect.csv")

optimizer_50.generate_codechunk(target_level=53, turn_in_exp=177985, max_collectables=9)

#optimizer_53 is for: Lv53-63 BSM, ARM, GSM, LTW, ALC
optimizer_53 = LevelOptimizer("levels.csv", "lv40FULLcollect.csv")
optimizer_53.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=30)

#optimizer_63 is for all classes and we can reach third collectability rating here.
# Make sure to turn Suborder Mode to Quick Synth All on Lisbeth from here on!
optimizer_63 = LevelOptimizer("levels.csv", "lv60collect.csv")
optimizer_63.generate_codechunk(target_level=67, turn_in_exp=464875, max_collectables=12)