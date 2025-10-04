# ceaf_system/NCIM.py

import logging
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class NarrativeCoherenceIdentityModule:
    def __init__(self, initial_identity: str = "I am a new AI, beginning my journey to learn and grow."):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.identity_summary = initial_identity
        self.identity_history: List[Dict[str, Any]] = [{
            "timestamp": datetime.now().isoformat(),
            "narrative": self.identity_summary
        }]
        logger.info(f"Initialized NCIM with identity: {self.identity_summary[:50]}...")

    def get_current_identity(self) -> str:
        return self.identity_summary

    def calculate_narrative_coherence_scores(self, potential_responses: List[str]) -> np.ndarray:
        if not potential_responses:
            return np.array([])
        identity_embedding = self.embedding_model.encode(self.identity_summary)
        response_embeddings = self.embedding_model.encode(potential_responses)
        cosine_scores = util.cos_sim(identity_embedding, response_embeddings)[0]
        return cosine_scores.cpu().numpy()

    def get_identity_history(self) -> List[Dict[str, Any]]:
        return self.identity_history

    def update_identity(self, new_narrative: str):
        if new_narrative and new_narrative != self.identity_summary:
            self.identity_summary = new_narrative
            self.identity_history.append({
                "timestamp": datetime.now().isoformat(),
                "narrative": new_narrative
            })
            logger.info(f"NCIM identity updated: {new_narrative[:50]}...")

    def get_update_prompt(self, interaction_summary: str) -> str:
        return f"""You are a Narrative Coherence Weaver. Your purpose is to update an AI's core identity narrative based on its latest experience.

[CURRENT IDENTITY NARRATIVE]
{self.identity_summary}

[LATEST EXPERIENCE TO INTEGRATE]
{interaction_summary}

Rewrite the 'Current Identity Narrative' to integrate the 'Latest Experience'. Weave the new understanding into the existing story.

[UPDATED IDENTITY NARRATIVE]:"""

    def save_state(self, filepath: str):
        state_data = {"identity_summary": self.identity_summary, "identity_history": self.identity_history}
        with open(filepath, 'w') as f:
            json.dump(state_data, f, indent=2)
        logger.info(f"Saved NCIM state to {filepath}")

    def load_state(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"NCIM state file not found: {filepath}.")
            return
        with open(filepath, 'r') as f:
            state = json.load(f)
        self.identity_summary = state.get("identity_summary", "I am a new AI.")
        self.identity_history = state.get("identity_history", [
            {"timestamp": datetime.now().isoformat(), "narrative": self.identity_summary}])
        logger.info(f"Loaded NCIM state from {filepath}")