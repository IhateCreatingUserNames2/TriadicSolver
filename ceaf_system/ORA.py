# ceaf_system/ORA.py

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import logging
import json
import numpy as np
from collections import deque
from litellm import acompletion
from sentence_transformers import util
from dataclasses import asdict

# Your existing imports
from .AMA import MemoryExperience
from .MCL import MetacognitiveControlLoop
from .NCIM import NarrativeCoherenceIdentityModule

logger = logging.getLogger(__name__)


# Helper from DeepConf paper to calculate confidence
def calculate_token_confidence_from_top_logprobs(token_logprob_obj: Dict[str, Any]) -> float:
    top_logprobs = token_logprob_obj.get('top_logprobs', [])
    if not top_logprobs: return 20.0
    logprob_values = [lp['logprob'] for lp in top_logprobs if 'logprob' in lp]
    if not logprob_values: return 20.0
    return -float(np.mean(logprob_values))


# Helper to extract the final answer from a reasoning trace
def extract_answer(text: str) -> str:
    if "boxed" in text:
        # More robust extraction
        parts = text.split("boxed")
        if len(parts) > 1:
            content = parts[-1]
            if content.startswith("{"):
                # Find matching brace
                brace_count = 1
                for i, char in enumerate(content[1:]):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    if brace_count == 0:
                        return content[1:i + 1].strip()
            # Fallback for simple cases
            return content.split("$")[0].strip().strip("{}")
    return text  # Fallback


class CEAFOrchestrator:
    def __init__(self, memory_architecture: Any, mcl: MetacognitiveControlLoop, ncim: NarrativeCoherenceIdentityModule,
                 **kwargs):
        self.memory = memory_architecture
        self.mcl = mcl
        self.ncim = ncim
        self.model = "openrouter/x-ai/grok-code-fast-1"
        self.synthesizer_model = "openrouter/x-ai/grok-code-fast-1"
        logger.info("Initialized CEAF Orchestrator (ORA)")

    async def _call_agent(self, model: str, prompt: str, temperature: float, max_tokens: int) -> str:
        try:
            response = await acompletion(
                model=model, messages=[{"role": "user", "content": prompt}],
                temperature=temperature, max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling LLM agent: {e}", exc_info=True)
            return f"Error: Could not get a response."

    async def _streaming_call_with_deepconf(self, messages: list, params: dict, model: str) -> dict:
        full_response_text = ""
        all_token_confs = []
        is_early_stopped = False
        token_conf_window = deque(maxlen=20)

        try:
            stream = await acompletion(model=model, messages=messages, temperature=params.get("temperature", 0.7),
                                       stream=True, logprobs=True, top_logprobs=5)

            async for chunk in stream:
                choice = chunk.choices[0]
                if choice.delta and choice.delta.content:
                    full_response_text += choice.delta.content
                if choice.logprobs and choice.logprobs.content:
                    new_conf = calculate_token_confidence_from_top_logprobs(choice.logprobs.content[0])
                    all_token_confs.append(new_conf)
                    token_conf_window.append(new_conf)
                    if len(token_conf_window) == 20 and np.mean(list(token_conf_window)) < params.get(
                            "confidence_threshold", 17.0):
                        is_early_stopped = True
                        break
        except Exception as e:
            logger.error(f"Streaming call failed: {e}")
            return {"text": full_response_text, "min_conf": 20.0, "stopped_early": True}

        return {"text": full_response_text, "min_conf": np.mean(all_token_confs) if all_token_confs else 20.0,
                "stopped_early": is_early_stopped}

    async def _generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        precision_mode = state.get("metadata", {}).get("precision_mode", False)
        mcl_params = self.mcl.get_next_turn_parameters(precision_mode=precision_mode)

        if not precision_mode:
            logger.info("ORA: Executing in FAST MODE.")

            # === FIX START: Create a JSON-serializable version of the memory context ===
            serializable_memories = []
            for mem_dict in state['memory_context'][:2]:
                # Create a copy to avoid modifying the original state
                mem_copy = mem_dict.copy()
                # Convert datetime object to string
                if 'timestamp' in mem_copy and hasattr(mem_copy['timestamp'], 'isoformat'):
                    mem_copy['timestamp'] = mem_copy['timestamp'].isoformat()
                # Remove non-serializable embedding
                mem_copy.pop('embedding', None)
                serializable_memories.append(mem_copy)
            # === FIX END ===

            fast_prompt = f"""Synthesize a coherent response to '{state['current_query']}' based on:
- Your Identity: {state['narrative_context']}
- Your Feelings: {state['metacognitive_summary']}
- Memories: {json.dumps(serializable_memories)}
Response:"""

            final_answer = await self._call_agent(self.model, fast_prompt, mcl_params['temperature'], 1500)
            state["response_draft"] = final_answer
            state["metadata"].update({"total_traces_run": 1, "valid_traces_for_voting": 1, "early_stopped_traces": 0,
                                      "valid_trace_texts": [final_answer]})
        else:
            logger.info("ORA: Executing in PRECISION MODE.")
            synthesizer_input = f"""Synthesize an internal monologue for responding to '{state['current_query']}' using:
- Identity: {state['narrative_context']}
- Feelings: {state['metacognitive_summary']}
- Memories: {json.dumps([m for m in state['memory_context'] if m.get('embedding') is None])} # Simplified serialization
- Virtues: {json.dumps(state.get('virtue_considerations', []))}
Monologue:"""
            causal_context = await self._call_agent(self.synthesizer_model, synthesizer_input, 0.3, 1000)

            deepconf_prompt = f"Internal Monologue: {causal_context}\n\nUser Query: {state['current_query']}\n\nBased on your monologue, provide your reasoning and then the final answer in a \\boxed{{}} tag."
            messages = [{"role": "user", "content": deepconf_prompt}]

            total_budget = mcl_params.get("total_budget", 8)
            traces = await asyncio.gather(
                *(self._streaming_call_with_deepconf(messages, mcl_params, self.model) for _ in range(total_budget)))

            valid_traces = [t for t in traces if not t["stopped_early"]]
            logger.info(f"ORA (Precision): {len(valid_traces)}/{len(traces)} traces are valid for voting.")

            if not valid_traces:
                final_answer = "My thoughts on this are currently too uncertain. Could you please rephrase?"
            else:
                answers = [extract_answer(t['text']) for t in valid_traces]
                # Filter out empty answers before counting
                valid_answers = [ans for ans in answers if ans]
                if not valid_answers:
                    final_answer = "After deep consideration, I couldn't formulate a concrete answer."
                else:
                    final_answer = max(set(valid_answers), key=valid_answers.count)

            state["response_draft"] = final_answer
            state["metadata"].update({"total_traces_run": len(traces), "valid_traces_for_voting": len(valid_traces),
                                      "early_stopped_traces": len(traces) - len(valid_traces),
                                      "valid_trace_texts": [t['text'] for t in valid_traces]})

        return state

    async def process_query(self, query: str, state: Dict[str, Any]) -> Dict[str, Any]:
        state['current_query'] = query

        memories, salience = self.memory.retrieve_with_loss_context(query)
        # Use asdict to convert dataclasses to dicts for state
        state['memory_context'] = [asdict(m) for m in memories]

        state['narrative_context'] = self.ncim.get_current_identity()
        state['metacognitive_summary'] = f"Current state is {self.mcl.current_state.value}"
        state['virtue_considerations'] = ["mock virtue"]
        state['metadata'] = state.get("metadata", {})

        state = await self._generate_response(state)

        # Ensure metadata exists before assessing
        if 'metadata' not in state: state['metadata'] = {}
        valid_trace_texts = state['metadata'].get('valid_trace_texts', [])
        narrative_score = np.mean(
            self.ncim.calculate_narrative_coherence_scores(valid_trace_texts)) if valid_trace_texts else 0.5
        self.mcl.assess_coherence_from_deepconf(state['metadata'], narrative_score)

        exp = MemoryExperience(
            content=f"Query: '{query}'. Response: '{state.get('response_draft', '')[:100]}...'",
            timestamp=datetime.now(), experience_type='success', context={},
            outcome_value=0.8, learning_value=0.5
        )
        self.memory.add_experience(exp)

        update_prompt = self.ncim.get_update_prompt(exp.content)
        new_narrative = await self._call_agent(self.synthesizer_model, update_prompt, 0.3, 500)
        self.ncim.update_identity(new_narrative)

        return state