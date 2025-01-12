import pandas as pd
from typing import Tuple, List, Dict
from dataclasses import dataclass
from functools import lru_cache


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
        """Find minimum exp needed at level to achieve target with target_collectables"""
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
        """
        breakpoints = []
        min_level = max(1, target_level - max_collectables - 5)

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
                    level=current_level,
                    target_collectables=collectables,
                    target_level=target_level,
                    turn_in_exp=turn_in_exp,
                    max_collectables=max_collectables,
                    max_exp=max_exp
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

        return sorted(breakpoints, key=lambda x: (x.collectables_needed, -x.level, -x.exp))

    def calculate_min_collectables(
            self,
            start_level: int,
            target_level: int,
            start_exp: int,
            turn_in_exp: int,
            max_collectables: int = 50
    ) -> Tuple[int, List[Tuple[int, int]]]:
        """
        Calculate minimum number of collectables needed

        Returns:
        Tuple[int, List[Tuple[int, int]]]:
            - Minimum number of collectables needed
            - List of (level, count) tuples showing when to craft
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

    def generate_codechunk(
            self,
            target_level: int,
            turn_in_exp: int,
            max_collectables: int = 23
    ) -> None:
        """Generate C# CodeChunk for determining collectable amount"""
        breakpoints = self.find_breakpoints(target_level, turn_in_exp, max_collectables)

        # Generate the CodeChunk
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
        for bp in breakpoints:
            if bp.level != current_level:
                print(f"\t\t({bp.level}, > {bp.exp}) => {bp.collectables_needed},")
                current_level = bp.level
            else:
                print(f"\t\t({bp.level}, >= {bp.exp}) => {bp.collectables_needed},")

        # Add default case for lowest valid level
        if breakpoints:
            min_level = min(bp.level for bp in breakpoints)
            print(f"\t\t({min_level}, >= 0) => {max_collectables},")

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
            "\t\t\t\tvar json = $\"[{'Group':1,'Item':31919,'Amount':{amount},'Enabled':true,'Type':'Alchemist','Collectable':false}]\";")
        print("\t\t\t\tvar orderMethod = lisbethObject.GetType().GetMethod(\"ExecuteOrders\");")
        print("\t\t\t\tawait (Task<bool>)orderMethod.Invoke(lisbethObject, new object[] { json, false });")
        print("\t\t\t}")
        print("\t\t}")
        print("\t]]>")
        print("</CodeChunk>")

    def find_breakpoints_with_target_exp(
            self,
            target_level: int,
            target_exp: int,
            turn_in_exp: int,
            max_collectables: int = 23
    ) -> List[Breakpoint]:
        """Find breakpoints for reaching specific level and exp target"""
        breakpoints = []
        min_level = max(1, target_level - max_collectables - 5)

        def will_reach_target(level: int, exp: int, collectables: int) -> bool:
            """Check if given collectables will reach target from this state"""
            current_level = level
            current_exp = exp

            # Simulate synthesis
            for _ in range(collectables):
                synthesis_exp = self.get_synthesis_exp(current_level)
                current_exp += synthesis_exp

                while current_level < target_level and current_exp >= self.level_exp_dict[current_level]:
                    current_exp -= self.level_exp_dict[current_level]
                    current_level += 1

            # Add turn-in exp
            current_exp += collectables * turn_in_exp

            while current_level < target_level and current_exp >= self.level_exp_dict[current_level]:
                current_exp -= self.level_exp_dict[current_level]
                current_level += 1

            return current_level > target_level or (current_level == target_level and current_exp >= target_exp)

        for current_level in range(target_level - 1, min_level - 1, -1):
            if current_level not in self.level_exp_dict:
                continue

            max_exp = self.level_exp_dict[current_level]

            # Find minimum collectables needed with max exp
            min_collectables = 1
            while min_collectables <= max_collectables:
                if will_reach_target(current_level, max_exp, min_collectables):
                    break
                min_collectables += 1

            if min_collectables > max_collectables:
                continue

            # Find thresholds for each collectable count
            prev_threshold = max_exp + 1
            for collectables in range(min_collectables, max_collectables + 1):
                # Binary search for threshold
                left, right = 0, max_exp
                threshold = max_exp + 1

                while left <= right:
                    mid = (left + right) // 2
                    if will_reach_target(current_level, mid, collectables):
                        threshold = mid
                        right = mid - 1
                    else:
                        left = mid + 1

                if threshold < prev_threshold and threshold <= max_exp:
                    breakpoints.append(Breakpoint(
                        level=current_level,
                        exp=threshold,
                        collectables_needed=collectables
                    ))
                    prev_threshold = threshold

        return sorted(breakpoints, key=lambda x: (x.collectables_needed, -x.level, -x.exp))

    def generate_codechunk_with_target_exp(
            self,
            target_level: int,
            target_exp: int,
            turn_in_exp: int,
            max_collectables: int = 23
    ) -> None:
        """Generate C# CodeChunk for determining collectables needed to reach specific level and exp"""
        breakpoints = self.find_breakpoints_with_target_exp(
            target_level, target_exp, turn_in_exp, max_collectables
        )

        # Generate the CodeChunk
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
                print(f"\t\t({bp.level}, > {bp.exp}) => {bp.collectables_needed},")
                current_level = bp.level
            else:
                print(f"\t\t({bp.level}, >= {bp.exp}) => {bp.collectables_needed},")

        # Add default case for lowest valid level
        if breakpoints:
            min_level = min(bp.level for bp in breakpoints)
            print(f"\t\t({min_level}, >= 0) => {max_collectables},")

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
            "\t\t\t\tvar json = $\"[{'Group':1,'Item':31919,'Amount':{amount},'Enabled':true,'Type':'Alchemist','Collectable':false}]\";")
        print("\t\t\t\tvar orderMethod = lisbethObject.GetType().GetMethod(\"ExecuteOrders\");")
        print("\t\t\t\tawait (Task<bool>)orderMethod.Invoke(lisbethObject, new object[] { json, false });")
        print("\t\t\t}")
        print("\t\t}")
        print("\t]]>")
        print("</CodeChunk>")


#optimizer_21 = LevelOptimizer("levels.csv", "lv20collect.csv")

# Lv 21 and above can craft Lv 20 collectable with 100% HQ.

# optimizer_21.generate_codechunk(target_level=41, turn_in_exp=67771)

#optimizer_21_CUL = LevelOptimizer("levels.csv", "lv20CULcollect.csv")

# optimizer_21_CUL.generate_codechunk(target_level=41, turn_in_exp=67771)

# Lv 41-53 can only reliably craft to the first or second collectability rating.
# optimizer_41 is for: Lv41-49 BSM, ARM, GSM, LTW, ALC
#optimizer_41 = LevelOptimizer("levels.csv", "lv40collect.csv")
# optimizer_41_HQ is for: Lv41-63 CRP, CUL
#optimizer_41_HQ = LevelOptimizer("levels.csv", "lv40HQcollect.csv")

#optimizer_41_HQ.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=39)
# optimizer_41_WVR is for: Lv41-63 WVR
#optimizer_41_WVR = LevelOptimizer("levels.csv", "lv40WVRcollect.csv")

#optimizer_41_WVR.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=38)
# CRP, CUL, and WVR should be leveled to 63 first: they can hit Lv3 collectability
# because of HQ mat.

#optimizer_41.generate_codechunk(target_level=50, turn_in_exp=177985, max_collectables=10)

#optimizer_50 is for: Lv50-53 BSM, ARM, GSM, LTW, ALC
#optimizer_50 = LevelOptimizer("levels.csv", "lv40bcollect.csv")

#optimizer_50.generate_codechunk(target_level=53, turn_in_exp=177985, max_collectables=9)

#optimizer_53 is for: Lv53-63 BSM, ARM, GSM, LTW, ALC
#optimizer_53 = LevelOptimizer("levels.csv", "lv40FULLcollect.csv")
#optimizer_53.generate_codechunk(target_level=63, turn_in_exp=359521, max_collectables=30)

#optimizer_63 is for all classes and we can reach third collectability rating here.
# Make sure to turn Suborder Mode to Quick Synth All on Lisbeth from here on!
#optimizer_63 = LevelOptimizer("levels.csv", "lv60collect.csv")
#optimizer_63.generate_codechunk(target_level=67, turn_in_exp=464875, max_collectables=14)

#optimizer_70 = LevelOptimizer("levels.csv", "lv70collect.csv")
#optimizer_70.generate_codechunk(target_level=80, turn_in_exp=755426, max_collectables=45)

#optimizer_70.generate_codechunk_with_target_exp(target_level=77, target_exp=879334, turn_in_exp=755426, max_collectables=29)

optimizer_81 = LevelOptimizer("levels.csv", "lv81collect.csv")

# CRP, GSM to Lv84:

optimizer_81.generate_codechunk(84, turn_in_exp=1055241, max_collectables=21)

# BSM to Lv88

optimizer_81.generate_codechunk(88, turn_in_exp=1055241, max_collectables=49)

optimizer_80 = LevelOptimizer("levels.csv", "lv80collect.csv")

# ALC to Lv87:

optimizer_80.generate_codechunk_with_target_exp(87, target_exp=5681564, turn_in_exp=1024632, max_collectables=47)

# LTW, WVR, ARM to Lv82 (leves, require manual modification):

optimizer_81.generate_codechunk(82, turn_in_exp=1870000, max_collectables=6)

optimizer_83 = LevelOptimizer("levels.csv", "lv83collect.csv")

# LTW, ARM to Lv84 (leves, require manual modification):

optimizer_83.generate_codechunk(84, turn_in_exp=3165820, max_collectables=5)

# WVR to Lv86 (leves, require manual modification):

optimizer_83.generate_codechunk(86, turn_in_exp=3165820, max_collectables=9)

optimizer_85 = LevelOptimizer("levels.csv", "lv85collect.csv")

# CRP 84-86 (collectables)

optimizer_85.generate_codechunk(86, turn_in_exp=1417077, max_collectables=10)

optimizer_87 = LevelOptimizer("levels.csv", "lv87collect.csv")

# ARM 84-87

optimizer_85.generate_codechunk_with_target_exp(target_level= 87, target_exp=5681564, turn_in_exp=1417077,
                                                max_collectables=19)

# GSM, CUL 84-88

optimizer_85.generate_codechunk(88, turn_in_exp=1417077, max_collectables=21)

# LTW to Lv87 (leves)

optimizer_84 = LevelOptimizer("levels.csv", "lv84collect.csv")
optimizer_84.generate_codechunk_with_target_exp(87, target_exp=5681564, turn_in_exp=3451960, max_collectables=9)

# WVR to Lv88 (leves)

optimizer_86 = LevelOptimizer("levels.csv", "lv86collect.csv")
optimizer_86.generate_codechunk(88, turn_in_exp=3845200, max_collectables=5)

# to Lv90 (collectables)

optimizer_89 = LevelOptimizer("levels.csv", "lv89collect.csv")
optimizer_89.generate_codechunk(90, turn_in_exp=1853298, max_collectables=10)

# WVR to Lv90 (leves)

optimizer_89.generate_codechunk(90, turn_in_exp=4514600, max_collectables=5)

# Lv91 collectable to Lv92

optimizer_91 = LevelOptimizer("levels.csv", "lv91collect.csv")
optimizer_91.generate_codechunk(92, turn_in_exp=2335689, max_collectables=10)
# GSM leve to lv92
optimizer_91.generate_codechunk(92, turn_in_exp=5390860, max_collectables=5)
# WVR leve to lv92
optimizer_91.generate_codechunk(92, turn_in_exp=5390860, max_collectables=5)

# Lv93 collectable to Lv96

optimizer_93 = LevelOptimizer("levels.csv", "lv93collect.csv")
optimizer_93.generate_codechunk(96, turn_in_exp=2720952, max_collectables=21)
# to lv94
optimizer_93.generate_codechunk(94, turn_in_exp=2720952, max_collectables=10)
# WVR leve to lv94
optimizer_93.generate_codechunk(94, turn_in_exp=6231280, max_collectables=5)
# to lv98
optimizer_93.generate_codechunk(98, turn_in_exp=2720952, max_collectables=34)

# Lv95 collectable to Lv98

optimizer_95 = LevelOptimizer("levels.csv", "lv95collect.csv")
optimizer_95.generate_codechunk(98, turn_in_exp=3122973, max_collectables=21)
# to lv96
optimizer_95.generate_codechunk(96, turn_in_exp=3122973, max_collectables=10)
# to lv100
optimizer_95.generate_codechunk(100, turn_in_exp=3122973, max_collectables=34)
# wvr leve to lv96
optimizer_95.generate_codechunk(96, turn_in_exp=7858900, max_collectables=5)


# Lv97 collectable to Lv98

optimizer_97 = LevelOptimizer("levels.csv", "lv97collect.csv")
optimizer_97.generate_codechunk(98, turn_in_exp=3583647, max_collectables=11)
# to lv100
optimizer_97.generate_codechunk(100, turn_in_exp=3583647, max_collectables=21)
# leve to lv98
optimizer_97.generate_codechunk(98, turn_in_exp=8250720, max_collectables=5)

# lv99 collectable to lv100

optimizer_99 = LevelOptimizer("levels.csv", "lv99collect.csv")
optimizer_99.generate_codechunk(100, turn_in_exp=4067919, max_collectables=10)

# alc leve to lv95
optimizer_95.generate_codechunk(95, turn_in_exp=7118800, max_collectables=3)

# alc craft to lv96
optimizer_95.generate_codechunk(96, turn_in_exp=0, max_collectables=30)

# ARM to lv98.5
optimizer_95.generate_codechunk_with_target_exp(98, target_exp=13626426, turn_in_exp=3122973, max_collectables=25)

# ARM to lv100
optimizer_95.generate_codechunk(100, turn_in_exp=3122973, max_collectables=34)

# CRP to lv99
optimizer_99.generate_codechunk_with_target_exp(99, target_exp=3615868, turn_in_exp=4067919, max_collectables=6)

# wvr leve to lv99.5
optimizer_99.generate_codechunk_with_target_exp(99, target_exp=11044184, turn_in_exp=10294000, max_collectables=4)

# gsm collectable to lv99
optimizer_97.generate_codechunk(99, turn_in_exp=3583647, max_collectables=15)

# bsm collectable to lv99.5
optimizer_99.generate_codechunk_with_target_exp(99, target_exp=10276865, turn_in_exp=4067919, max_collectables=7)



# cul to lv99.5
optimizer_99.generate_codechunk_with_target_exp(99, target_exp=8468900, turn_in_exp=4067919, max_collectables=7)

# ltw leve to lv99.7
optimizer_99.generate_codechunk_with_target_exp(99, target_exp=16275248, turn_in_exp=10294000, max_collectables=4)

# ltw leve to lv96
optimizer_95.generate_codechunk(96, turn_in_exp=4909520, max_collectables=7)

# alc leve to lv100
optimizer_99.generate_codechunk(100, turn_in_exp=8366760, max_collectables=6)

# alc collectable to lv98

optimizer_97.generate_codechunk_with_target_exp(98, target_exp=0, turn_in_exp=3583647, max_collectables=10)

# BSM leve to lv84

optimizer_83.generate_codechunk(88, turn_in_exp=3050260, max_collectables=15)