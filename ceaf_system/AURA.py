# ceaf_system/AURA.py

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid
import json
import os

from .AMA import MemoryExperience
from .MCL import SystemState, CoherenceState

logger = logging.getLogger(__name__)


@dataclass
class SystemInsight:
    insight_type: str
    summary: str
    supporting_evidence: List[Dict[str, Any]]
    recommendation: Optional[str] = None
    actionable_recommendation: Optional[Dict[str, Any]] = None
    insight_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)


class AutonomousUniversalReflectiveAnalyzer:
    def __init__(self):
        self.system_insights: List[SystemInsight] = []
        self.last_analysis_timestamp: Optional[datetime] = None
        logger.info("Initialized Autonomous Universal Reflective Analyzer (AURA)")

    def run_analysis_cycle(self, all_experiences: List[MemoryExperience], state_history: List[SystemState]):
        if not state_history: return
        logger.info(f"AURA: Starting analysis with {len(state_history)} states.")
        self._analyze_loss_to_breakthrough_cycles(state_history)
        self.last_analysis_timestamp = datetime.now()

    def _analyze_loss_to_breakthrough_cycles(self, state_history: List[SystemState]):
        for i in range(1, len(state_history)):
            prev_state, curr_state = state_history[i - 1], state_history[i]
            if (curr_state.coherence_state == CoherenceState.BREAKTHROUGH_IMMINENT and
                    prev_state.coherence_state in [CoherenceState.FAILING_PRODUCTIVELY,
                                                   CoherenceState.PRODUCTIVE_CONFUSION]):

                insight = SystemInsight(
                    insight_type="Loss-to-Breakthrough-Cycle",
                    summary=f"A state of '{prev_state.coherence_state.value}' led to a breakthrough.",
                    supporting_evidence=[
                        {"from_state": prev_state.coherence_state.value, "to_state": curr_state.coherence_state.value}],
                    recommendation="Increase tolerance for productive failure.",
                    actionable_recommendation={
                        "target_module": "MCL", "action": "ADJUST_COHERENCE_TARGET",
                        "parameter": "loss_tolerance", "adjustment_value": 0.05
                    }
                )
                # Avoid duplicates
                if not any(i.summary == insight.summary for i in self.system_insights):
                    self.system_insights.append(insight)
                    logger.info("AURA Insight: Identified a Loss-to-Breakthrough cycle.")

    def get_latest_insights(self, n: int = 5) -> List[SystemInsight]:
        return sorted(self.system_insights, key=lambda x: x.timestamp, reverse=True)[:n]

    def save_state(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump([asdict(i) for i in self.system_insights], f, indent=2, default=str)
        logger.info(f"Saved AURA state to {filepath}")

    def load_state(self, filepath: str):
        if not os.path.exists(filepath): return
        with open(filepath, 'r') as f:
            self.system_insights = [SystemInsight(**data) for data in json.load(f)]
        logger.info(f"Loaded {len(self.system_insights)} insights from AURA state file {filepath}")