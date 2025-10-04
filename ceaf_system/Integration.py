# ceaf_system/Integration.py

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import all components
from .AMA import AdaptiveMemoryArchitecture
from .MCL import MetacognitiveControlLoop
from .NCIM import NarrativeCoherenceIdentityModule
from .VRE import VirtueReasoningEngine
from .AURA import AutonomousUniversalReflectiveAnalyzer
from .LCAM import LossCatalogingAndAnalysisModule
from .ORA import CEAFOrchestrator


class CEAFSystem:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        load_dotenv()
        logger.info("Initializing CEAF System...")

        self.persistence_path = Path(self.config.get("persistence_path", "./ceaf_data"))
        self.persistence_path.mkdir(exist_ok=True, parents=True)

        # Initialize all modules
        self.memory = AdaptiveMemoryArchitecture(**self.config.get("memory", {}))
        self.mcl = MetacognitiveControlLoop(**self.config.get("mcl", {}))
        self.ncim = NarrativeCoherenceIdentityModule(**self.config.get("ncim", {}))
        self.vre = VirtueReasoningEngine(**self.config.get("vre", {}))
        self.aura = AutonomousUniversalReflectiveAnalyzer()
        self.lcam = LossCatalogingAndAnalysisModule()
        self.ora = CEAFOrchestrator(
            memory_architecture=self.memory, mcl=self.mcl, ncim=self.ncim
        )

        self._load_system_state()
        self.interaction_count = 0
        self.aura_analysis_interval = self.config.get("aura_analysis_interval", 10)

        logger.info("CEAF System initialized successfully")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing a user query."""
        self.interaction_count += 1
        start_time = datetime.now()

        query = input_data.get("message", "")
        session_id = input_data.get("session_id", "default_session")

        if self.interaction_count > 0 and self.interaction_count % self.aura_analysis_interval == 0:
            logger.info("Triggering periodic AURA analysis...")
            self.aura.run_analysis_cycle(self.memory.experiences, list(self.mcl.state_history))
            self.mcl.apply_aura_recommendations(self.aura.get_latest_insights())

        state = await self.ora.process_query(query, input_data)

        if self.interaction_count > 0 and self.interaction_count % self.config.get("auto_save_interval", 5) == 0:
            # We call shutdown here which now only saves state
            self.save_state()

        return {
            "response": state.get("response_draft", "Error processing request."),
            "metadata": {
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "coherence_state": self.mcl.current_state.value,
            }
        }

    def _load_system_state(self):
        logger.info("Loading system state from persistence path...")
        self.memory.load_memory_state(str(self.persistence_path / "ama_state.json"))
        self.mcl.load_state(str(self.persistence_path / "mcl_state.json"))
        self.ncim.load_state(str(self.persistence_path / "ncim_state.json"))
        self.vre.load_state(str(self.persistence_path / "vre_state.json"))
        self.aura.load_state(str(self.persistence_path / "aura_state.json"))
        self.lcam.load_state(None, self.memory.experiences)

    def save_state(self):
        """Saves the state of all components."""
        logger.info("Saving system state...")
        self.memory.save_memory_state(str(self.persistence_path / "ama_state.json"))
        self.mcl.save_state(str(self.persistence_path / "mcl_state.json"))
        self.ncim.save_state(str(self.persistence_path / "ncim_state.json"))
        self.vre.save_state(str(self.persistence_path / "vre_state.json"))
        self.aura.save_state(str(self.persistence_path / "aura_state.json"))
        logger.info("System state saved.")

    # === FIX: Rename shutdown to a more accurate name ===
    async def shutdown_and_save(self):
        """Gracefully saves state and allows network clients to close."""
        self.save_state()
        # This small sleep gives asyncio time to process pending close operations
        # from libraries like httpx that litellm uses under the hood.
        await asyncio.sleep(0.1)