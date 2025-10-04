# main_solver.py (Final Corrected Version with Role Enforcement)
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Import the main CEAF system class
from ceaf_system.Integration import CEAFSystem


# ==============================================================================
# 1. DATA STRUCTURES FOR THE SOLVER'S OUTPUT
# ==============================================================================
@dataclass
class TriadicComponent:
    title: str
    description: str


@dataclass
class ProblemReframe:
    original_problem: str
    triadic_reframe: str
    key_insight: str


@dataclass
class SolutionPath:
    approach_title: str
    steps: List[str]


@dataclass
class TriadicAnalysisResult:
    one_substrate: TriadicComponent
    two_duality: TriadicComponent
    three_emergence: TriadicComponent
    reframe: ProblemReframe
    solution_path: SolutionPath


# ==============================================================================
# 2. THE TRIADIC SOLVER CLASS
# ==============================================================================
class TriadicSolver:
    def __init__(self, ceaf_system: CEAFSystem):
        self.ceaf = ceaf_system
        print("✅ TriadicSolver Initialized. Using CEAF as its cognitive engine.")

    def _parse_component_response(self, response_text: str, default_title: str) -> TriadicComponent:
        separator = '|' if '|' in response_text else ':'
        if separator in response_text:
            parts = response_text.split(separator, 1)
            title_keywords = ["Substrate", "Duality", "Emergence"]
            title = parts[0]
            for keyword in title_keywords:
                title = title.replace(keyword, "").strip()
            description = parts[1].replace("Description:", "").replace("Tension:", "").replace("Properties:",
                                                                                               "").strip()
            if not title or not description:
                return TriadicComponent(title=default_title, description=response_text.strip())
            return TriadicComponent(title=title, description=description)
        else:
            return TriadicComponent(title=default_title, description=response_text.strip())

    async def solve(self, problem_statement: str) -> TriadicAnalysisResult:
        print(f"\n--- Starting Triadic Analysis for: \"{problem_statement}\" ---")

        # PHASE 1: DECOMPOSITION
        print("\n[Phase 1/4] Decomposing problem into ONE, TWO, THREE...")

        # --- Prompts remain the same as they worked perfectly ---
        one_prompt = f"Problem: '{problem_statement}'. Identify the ONE (Substrate). Format: 'Substrate: [name] | Description: [explanation]'"
        two_prompt_base = f"Problem: '{problem_statement}'. Identify the TWO (Governing Duality). Format: 'Duality: [pole1] ↔ [pole2] | Tension: [description]'"
        three_prompt_base = f"Problem: '{problem_statement}'. Identify the THREE (Emergence). Format: 'Emergence: [name] | Properties: [explanation]'"

        one_response_data = await self.ceaf.process({"message": one_prompt})
        one = self._parse_component_response(one_response_data['response'], "Substrate (ONE)")

        two_prompt = f"Previously identified substrate: {one.title}\n\n{two_prompt_base}"
        two_response_data = await self.ceaf.process({"message": two_prompt})
        two = self._parse_component_response(two_response_data['response'], "Duality (TWO)")

        three_prompt = f"Previously identified:\n- Substrate: {one.title}\n- Duality: {two.title}\n\n{three_prompt_base}"
        three_response_data = await self.ceaf.process({"message": three_prompt})
        three = self._parse_component_response(three_response_data['response'], "Emergence (THREE)")

        print("...Decomposition complete.")

        # === FIX START: Add strict role enforcement and output separation ===

        # PHASE 2: REFRAMING
        print("\n[Phase 2/4] Reframing the problem...")
        reframe_prompt = f"""You are a logician and analyst. Your task is to reframe a problem based on a provided triadic decomposition.
DO NOT talk about yourself or your own process. Focus ONLY on the problem.

Decomposition:
- ONE (Substrate): {one.title}
- TWO (Duality): {two.title}
- THREE (Emergence): {three.title}

Original Problem: '{problem_statement}'

YOUR TASK: Reframe the problem and provide the key insight.
Strict Format: 'Original: ... | Reframe: ... | Insight: ...'
"""
        reframe_response_data = await self.ceaf.process({"message": reframe_prompt})
        reframe_response = reframe_response_data['response']

        parts_raw = reframe_response.split('|')
        if len(parts_raw) == 3:
            parts = [p.split(':', 1)[1].strip() if ':' in p else p.strip() for p in parts_raw]
            reframe = ProblemReframe(original_problem=parts[0], triadic_reframe=parts[1], key_insight=parts[2])
        else:
            reframe = ProblemReframe(original_problem=problem_statement, triadic_reframe="Reframing failed",
                                     key_insight=reframe_response)
        print("...Reframing complete.")

        # PHASE 3: PATHFINDING
        print("\n[Phase 3/4] Finding solution path via 'Edge of Coherence'...")
        pathfinding_prompt = f"""You are a mathematician and strategist. Your task is to propose a concrete solution path for a reframed problem.
DO NOT talk about your own internal state or failures. Propose external, mathematical steps.

Reframed Problem: '{reframe.triadic_reframe}'
Core Duality: '{two.title}'

YOUR TASK: Propose a solution path based on finding the 'Edge of Coherence' for the core duality.
Strict Format: 'Approach: ... | Steps: 1. Step one text... 2. Step two text...'
"""
        path_response_data = await self.ceaf.process({"message": pathfinding_prompt})
        path_response = path_response_data['response']

        path_parts_raw = path_response.split('|')
        if len(path_parts_raw) >= 2:
            approach_title = path_parts_raw[0].replace("Approach:", "").strip()
            steps_raw = '|'.join(path_parts_raw[1:]).replace("Steps:", "").strip()
            steps = [s.strip() for s in steps_raw.split('\n') if s.strip()]
            solution_path = SolutionPath(approach_title=approach_title, steps=steps)
        else:
            solution_path = SolutionPath(approach_title="Pathfinding Failed", steps=[path_response])
        print("...Pathfinding complete.")

        # === FIX END ===

        # PHASE 4: ASSEMBLY
        print("\n[Phase 4/4] Assembling final analysis...")
        result = TriadicAnalysisResult(one, two, three, reframe, solution_path)
        print("--- Triadic Analysis Complete ---")
        return result


def display_analysis(result: TriadicAnalysisResult):
    # This function remains the same
    print("\n\n==============================================")
    print("    T R I A D I C   S O L V E R   R E S U L T")
    print("==============================================")
    print(f"\n[ 1 ] ONE (Substrate): {result.one_substrate.title}")
    print(f"      {result.one_substrate.description}")
    print(f"\n[ 2 ] TWO (Duality): {result.two_duality.title}")
    print(f"      {result.two_duality.description}")
    print(f"\n[ 3 ] THREE (Emergence): {result.three_emergence.title}")
    print(f"      {result.three_emergence.description}")
    print("\n----------------- REFRAME ------------------")
    print(f"Original Problem: {result.reframe.original_problem}")
    print(f"Triadic Reframe:  {result.reframe.triadic_reframe}")
    print(f"Key Insight:      {result.reframe.key_insight}")
    print("\n-------------- SOLUTION PATH ---------------")
    print(f"Proposed Approach: {result.solution_path.approach_title}")
    for step in result.solution_path.steps:
        if step.lstrip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
            print(f"  {step}")
        else:
            print(f"  - {step}")
    print("==============================================")


async def main():
    # This function remains the same
    config = {
        "persistence_path": "./ceaf_solver_data",
        "auto_save_interval": 3,
        "aura_analysis_interval": 5,
        "mcl": {"history_window": 50},
        "ora": {"precision_mode_by_default": False}
    }
    ceaf_instance = CEAFSystem(config=config)
    solver = TriadicSolver(ceaf_system=ceaf_instance)
    try:
        problem = "The Hard Problem of Consciousness: Why do we have subjective experience (qualia)?"
        analysis_result = await solver.solve(problem)
        display_analysis(analysis_result)
    finally:
        print("\nShutting down and saving state...")
        await ceaf_instance.shutdown_and_save()
        print("Shutdown complete.")


if __name__ == "__main__":
    # This block remains the same
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nFATAL ERROR in main execution: {e}")
        import traceback

        traceback.print_exc()