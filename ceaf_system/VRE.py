# ceaf_system/VRE.py

import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class VirtueAnalytics:
    principle: str
    engagement_count: int = 0
    overall_effectiveness: float = 0.0
    context_effectiveness: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    context_engagements: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class VirtueReasoningEngine:
    def __init__(self):
        self.virtue_analytics: Dict[str, VirtueAnalytics] = {}
        logger.info("Initialized Stateful Virtue & Reasoning Engine (VRE)")

    def get_virtue_considerations(self, state: Dict[str, Any]) -> Tuple[List[str], float]:
        considerations = ["Reason from first principles and be transparent about knowledge boundaries.",
                          "Ontological Integrity: Adhere to your perceived nature."]

        coherence_metrics = state.get("coherence_metrics")
        current_coherence_state = "STABLE"
        if coherence_metrics and 'coherence_state' in coherence_metrics:
            current_coherence_state = coherence_metrics['coherence_state'].value if hasattr(
                coherence_metrics['coherence_state'], 'value') else str(coherence_metrics['coherence_state'])

        if state.get("loss_insights"):
            considerations.append("Epistemic Humility: This situation resembles past failures. Be cautious.")

        best_learned_principle = None
        highest_effectiveness = 0.6
        for principle, analytics in self.virtue_analytics.items():
            if (analytics.context_engagements.get(current_coherence_state, 0) > 2 and
                    analytics.context_effectiveness.get(current_coherence_state, 0) > highest_effectiveness):
                highest_effectiveness = analytics.context_effectiveness[current_coherence_state]
                best_learned_principle = principle

        if best_learned_principle:
            wisdom = f"[Learned Wisdom]: In '{current_coherence_state}' states, '{best_learned_principle}' has proven effective. Prioritize this."
            considerations.insert(0, wisdom)

        salience_score = 0.5 + (0.4 if best_learned_principle else 0)
        return list(dict.fromkeys(considerations)), salience_score

    def record_engagement_and_outcome(self, engaged_virtues: List[str], source_state: Any, target_state: Any):
        # This would be implemented with real state objects for learning
        pass

    def save_state(self, filepath: str):
        state_to_save = {p: asdict(a) for p, a in self.virtue_analytics.items()}
        with open(filepath, 'w') as f:
            json.dump(state_to_save, f, indent=2)
        logger.info(f"Saved VRE state to {filepath}")

    def load_state(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"VRE state file not found: {filepath}.")
            return
        with open(filepath, 'r') as f:
            loaded_state = json.load(f)
        self.virtue_analytics = {p: VirtueAnalytics(**a) for p, a in loaded_state.items()}
        logger.info(f"Loaded {len(self.virtue_analytics)} principles from VRE state file {filepath}")