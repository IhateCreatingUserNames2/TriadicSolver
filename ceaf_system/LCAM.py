# ceaf_system/LCAM.py

import logging
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer, util

from .AMA import MemoryExperience

logger = logging.getLogger(__name__)


class LossCatalogingAndAnalysisModule:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.failure_archive: Dict[str, List[MemoryExperience]] = defaultdict(list)
        self.pattern_embeddings: Dict[str, Any] = {}
        logger.info("Initialized Loss Cataloging and Analysis Module (LCAM)")

    def catalog_failure(self, experience: MemoryExperience):
        if experience.experience_type != 'failure' or not experience.failure_pattern: return
        self.failure_archive[experience.failure_pattern].append(experience)
        if experience.failure_pattern not in self.pattern_embeddings:
            self.pattern_embeddings[experience.failure_pattern] = self.embedder.encode(
                experience.failure_pattern.replace("_", " "))

    def get_insights_for_context(self, query: str) -> Tuple[List[Dict], float]:
        insights = []
        if not self.pattern_embeddings: return [], 0.0

        query_embedding = self.embedder.encode(query)
        candidate_patterns = []
        for pattern, pattern_embedding in self.pattern_embeddings.items():
            similarity = util.cos_sim(query_embedding, pattern_embedding).item()
            if similarity > 0.65:
                candidate_patterns.append((similarity, pattern))

        sorted_patterns = sorted(candidate_patterns, key=lambda x: x[0], reverse=True)

        for similarity, pattern in sorted_patterns[:2]:
            insights.append({"insight_type": "semantic_pattern_match", "failure_pattern": pattern,
                             "lesson": f"Past challenges similar to this query relate to '{pattern}'. Proceed with caution."})

        highest_similarity = max([s[0] for s in sorted_patterns], default=0.0) if sorted_patterns else 0.0
        return insights, float(highest_similarity)

    def load_state(self, filepath: str, all_experiences: List[MemoryExperience]):
        logger.info("LCAM: Rebuilding failure catalog from main memory...")
        self.failure_archive.clear()
        self.pattern_embeddings.clear()
        for exp in all_experiences:
            self.catalog_failure(exp)
        logger.info(f"LCAM state rebuilt. Found {len(self.pattern_embeddings)} unique failure patterns.")