# ceaf_system/MCL.py
# Metacognitive Control Loop
import os

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from datetime import datetime
import json
from collections import deque
import inspect

logger = logging.getLogger(__name__)


class CoherenceState(Enum):
    STABLE = "stable"
    EXPLORING = "exploring"
    EDGE_OF_CHAOS = "edge_of_chaos"
    PRODUCTIVE_CONFUSION = "productive_confusion"
    FAILING_PRODUCTIVELY = "failing_productively"
    RECOVERING = "recovering"
    BREAKTHROUGH_IMMINENT = "breakthrough_imminent"


@dataclass
class CoherenceMetrics:
    semantic_coherence: float = 0.5
    narrative_coherence: float = 0.5
    epistemic_coherence: float = 0.5
    creative_novelty: float = 0.5
    loss_tolerance: float = 0.5
    overall_coherence: float = field(init=False)
    edge_proximity: float = field(init=False)
    breakthrough_potential: float = field(init=False)

    def __post_init__(self):
        weights = {'semantic': 0.25, 'narrative': 0.25, 'epistemic': 0.20, 'creative': 0.15, 'loss': 0.15}
        # Use getattr for safer access
        self.overall_coherence = sum(getattr(self, name, 0.5) * weight for name, weight in weights.items())
        self.edge_proximity = (1 - abs(self.overall_coherence - 0.7)) * self.creative_novelty
        self.breakthrough_potential = self.edge_proximity * self.loss_tolerance


@dataclass
class SystemState:
    timestamp: datetime
    coherence_state: CoherenceState
    metrics: CoherenceMetrics


class MetacognitiveControlLoop:
    def __init__(self, history_window: int = 100):
        self.history_window = history_window
        self.current_state = CoherenceState.STABLE
        self.state_history: deque = deque(maxlen=history_window)
        self.coherence_targets = {'semantic': 0.8, 'narrative': 0.75, 'epistemic': 0.7, 'creative': 0.6, 'loss': 0.7}
        self.applied_recommendation_ids: set[str] = set()
        logger.info("Initialized Metacognitive Control Loop (MCL)")

    def assess_coherence_from_deepconf(self, deepconf_metadata: Dict[str, Any],
                                       narrative_score: float) -> CoherenceMetrics:
        total_traces = deepconf_metadata.get("total_traces_run", 1) or 1
        valid_traces = deepconf_metadata.get("valid_traces_for_voting", 1)
        stopped_traces = deepconf_metadata.get("early_stopped_traces", 0)

        epistemic_score = valid_traces / total_traces
        creative_score = stopped_traces / total_traces
        semantic_score = (epistemic_score * 0.7) + (narrative_score * 0.3)
        loss_tolerance = 0.5

        metrics = CoherenceMetrics(
            semantic_coherence=semantic_score,
            narrative_coherence=narrative_score,
            epistemic_coherence=epistemic_score,
            creative_novelty=creative_score,
            loss_tolerance=loss_tolerance
        )

        new_state_enum = self._determine_coherence_state(metrics)
        if new_state_enum != self.current_state:
            logger.info(f"MCL State Transition: {self.current_state.value} -> {new_state_enum.value}")
            self.current_state = new_state_enum

        self.state_history.append(
            SystemState(timestamp=datetime.now(), coherence_state=self.current_state, metrics=metrics))
        return metrics

    def _determine_coherence_state(self, metrics: CoherenceMetrics) -> CoherenceState:
        if metrics.breakthrough_potential > 0.6: return CoherenceState.BREAKTHROUGH_IMMINENT
        if metrics.loss_tolerance > 0.7 and metrics.overall_coherence < 0.5: return CoherenceState.FAILING_PRODUCTIVELY
        if 0.6 < metrics.overall_coherence < 0.8 and metrics.creative_novelty > 0.7: return CoherenceState.EDGE_OF_CHAOS
        if metrics.epistemic_coherence < 0.5 and metrics.creative_novelty > 0.6: return CoherenceState.PRODUCTIVE_CONFUSION
        if self.current_state in [CoherenceState.FAILING_PRODUCTIVELY,
                                  CoherenceState.PRODUCTIVE_CONFUSION] and metrics.overall_coherence > 0.7: return CoherenceState.RECOVERING
        if metrics.creative_novelty > 0.5 and metrics.overall_coherence > 0.7: return CoherenceState.EXPLORING
        return CoherenceState.STABLE

    def get_next_turn_parameters(self, precision_mode: bool = False) -> Dict[str, Any]:
        if precision_mode:
            logger.info("MCL: Generating parameters for PRECISION MODE.")
            return {"temperature": 0.7, "confidence_threshold": 16.8, "warmup_traces": 3, "total_budget": 8}

        logger.info("MCL: Generating parameters for FAST MODE.")
        params = {"temperature": 0.6, "confidence_threshold": 17.5, "warmup_traces": 1, "total_budget": 1}
        if self.current_state in [CoherenceState.EDGE_OF_CHAOS, CoherenceState.EXPLORING]:
            params["temperature"] = 0.9
        elif self.current_state == CoherenceState.FAILING_PRODUCTIVELY:
            params["temperature"] = 1.0
            params["total_budget"] = 4

        return params

    def apply_aura_recommendations(self, insights: List[Any]):
        for insight in insights:
            rec = insight.actionable_recommendation
            if rec and rec.get('target_module') == 'MCL' and insight.insight_id not in self.applied_recommendation_ids:
                if rec.get('action') == 'ADJUST_COHERENCE_TARGET':
                    param = rec.get('parameter')
                    value = rec.get('adjustment_value')
                    if param in self.coherence_targets and isinstance(value, float):
                        old_value = self.coherence_targets[param]
                        new_value = max(0.1, min(0.9, old_value + value))
                        self.coherence_targets[param] = new_value
                        logger.info(f"MCL SELF-TUNING via AURA: Adjusted '{param}' target to {new_value:.2f}.")
                        self.applied_recommendation_ids.add(insight.insight_id)

    def save_state(self, filepath: str):
        # === FIX START: Make the JSON encoder robust to NumPy types ===
        class MCLEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime):
                    return o.isoformat()
                if isinstance(o, CoherenceState):
                    return o.value
                if isinstance(o, (CoherenceMetrics, SystemState)):
                    return asdict(o)
                # This is the crucial addition to handle NumPy floats
                if isinstance(o, np.floating):
                    return float(o)
                # This handles NumPy integers
                if isinstance(o, np.integer):
                    return int(o)
                return super().default(o)

        # === FIX END ===

        state = {
            "current_state": self.current_state.value,
            "state_history": list(self.state_history),
            "coherence_targets": self.coherence_targets
        }
        try:
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2, cls=MCLEncoder)
            logger.info(f"Saved MCL state to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save MCL state: {e}")

    def load_state(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"MCL state file not found: {filepath}.")
            return

        try:
            with open(filepath, 'r') as f:
                state = json.load(f)

            self.current_state = CoherenceState(state.get("current_state", "stable"))
            self.coherence_targets = state.get("coherence_targets", self.coherence_targets)
            loaded_history = []
            for s_dict in state.get("state_history", []):
                try:
                    metrics_params = inspect.signature(CoherenceMetrics).parameters
                    metrics_data = {k: v for k, v in s_dict['metrics'].items() if k in metrics_params}

                    loaded_history.append(SystemState(
                        timestamp=datetime.fromisoformat(s_dict['timestamp']),
                        coherence_state=CoherenceState(s_dict['coherence_state']),
                        metrics=CoherenceMetrics(**metrics_data)
                    ))
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(f"Skipping malformed history entry during MCL load: {e}")
            self.state_history = deque(loaded_history, maxlen=self.history_window)
            logger.info(f"Loaded MCL state from {filepath}")
        except Exception as e:
            logger.error(f"Error loading MCL state: {e}")