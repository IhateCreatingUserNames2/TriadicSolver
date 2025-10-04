# ceaf_system/AMA.py
# Adaptive Memory Architecture with Loss Integration

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import faiss
from sentence_transformers import SentenceTransformer
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MemoryExperience:
    content: str
    timestamp: datetime
    experience_type: str
    context: Dict[str, Any]
    outcome_value: float
    learning_value: float
    cluster_id: Optional[int] = None
    embedding: Optional[np.ndarray] = field(default=None, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    failure_pattern: Optional[str] = None
    recovery_path: Optional[str] = None


class AdaptiveMemoryArchitecture:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", max_clusters: int = 1000):
        self.embedder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.experiences: List[MemoryExperience] = []
        self.clusters: Dict[int, List[int]] = {}  # cluster_id -> list of experience indices
        self.next_cluster_id = 0
        self.max_clusters = max_clusters
        self.clustering_threshold = 0.3
        logger.info(f"Initialized AMA with {embedding_model}")

    def add_experience(self, experience: MemoryExperience) -> int:
        if experience.embedding is None:
            experience.embedding = self.embedder.encode(experience.content)

        cluster_id = self._assign_to_cluster(experience)
        experience.cluster_id = cluster_id

        self.experiences.append(experience)
        self.index.add(np.array([experience.embedding]))

        logger.info(f"Added {experience.experience_type} experience to cluster {cluster_id}")
        return cluster_id

    def _assign_to_cluster(self, experience: MemoryExperience) -> int:
        if self.index.ntotal == 0:
            return self._create_cluster(len(self.experiences))

        k = min(5, self.index.ntotal)
        D, I = self.index.search(np.array([experience.embedding]), k)

        for dist, idx in zip(D[0], I[0]):
            if dist < self.clustering_threshold:
                existing_exp = self.experiences[idx]
                if existing_exp.cluster_id is not None:
                    self.clusters[existing_exp.cluster_id].append(len(self.experiences))
                    return existing_exp.cluster_id

        return self._create_cluster(len(self.experiences))

    def _create_cluster(self, experience_index: int) -> int:
        if len(self.clusters) >= self.max_clusters:
            self._merge_weakest_clusters()

        cluster_id = self.next_cluster_id
        self.next_cluster_id += 1
        self.clusters[cluster_id] = [experience_index]
        logger.info(f"Created new cluster {cluster_id}")
        return cluster_id

    def _merge_weakest_clusters(self):
        # Simplified: merge two smallest clusters
        if len(self.clusters) < 2: return
        sorted_clusters = sorted(self.clusters.items(), key=lambda item: len(item[1]))
        c1_id, c1_indices = sorted_clusters[0]
        c2_id, c2_indices = sorted_clusters[1]

        # Merge c2 into c1
        self.clusters[c1_id].extend(c2_indices)
        for idx in c2_indices:
            self.experiences[idx].cluster_id = c1_id
        del self.clusters[c2_id]
        logger.info(f"Merged cluster {c2_id} into {c1_id}")

    def retrieve_with_loss_context(self, query: str, k: int = 5) -> Tuple[List[MemoryExperience], float]:
        if self.index.ntotal == 0:
            return [], 0.0

        query_embedding = self.embedder.encode(query)
        search_k = min(k * 3, self.index.ntotal)
        D, I = self.index.search(np.array([query_embedding]), search_k)

        scored_experiences = []
        for dist, idx in zip(D[0], I[0]):
            exp = self.experiences[idx]
            similarity = 1 / (1 + dist)
            score = similarity * (1 + exp.learning_value * 0.5)
            if exp.experience_type == 'failure':
                score *= 1.2  # Boost relevance of failures
            scored_experiences.append((score, exp))

        scored_experiences.sort(key=lambda x: x[0], reverse=True)
        final_results = [exp for _, exp in scored_experiences[:k]]

        avg_salience = 0.0
        if scored_experiences:
            avg_salience = float(np.mean([s for s, e in scored_experiences[:k]]))

        return final_results, avg_salience

    def save_memory_state(self, filepath: str):
        state = {
            'experiences': [asdict(e) for e in self.experiences],
            'clusters': self.clusters,
            'next_cluster_id': self.next_cluster_id
        }
        # Convert numpy arrays to lists for JSON serialization
        for exp in state['experiences']:
            if 'embedding' in exp and exp['embedding'] is not None:
                exp['embedding'] = exp['embedding'].tolist()

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        logger.info(f"Saved AMA state to {filepath}")

    def load_memory_state(self, filepath: str):
        if not os.path.exists(filepath):
            logger.warning(f"AMA state file not found: {filepath}.")
            return

        with open(filepath, 'r') as f:
            state = json.load(f)

        self.experiences = [MemoryExperience(**{**e, 'embedding': np.array(e['embedding']) if e['embedding'] else None})
                            for e in state['experiences']]
        self.clusters = {int(k): v for k, v in state.get('clusters', {}).items()}
        self.next_cluster_id = state.get('next_cluster_id', 0)

        # Rebuild FAISS index
        self.index.reset()
        embeddings_to_add = [e.embedding for e in self.experiences if e.embedding is not None]
        if embeddings_to_add:
            self.index.add(np.vstack(embeddings_to_add))
        logger.info(f"Loaded AMA state from {filepath}. Rebuilt index with {self.index.ntotal} vectors.")