"""
SDO Engine (Phase 3)
Orchestrates adaptive code generation with Thompson Sampling,
candidate pruning, undo/rollback, semantic caching, multi-LLM routing,
and policy enforcement.
"""
import asyncio
import uuid
import time
from typing import List, Optional, Dict, Any
from sdo import SDO, SDOStatus, Candidate
from llm import LLMService
# Use local import or assumes knowledge.py is in path
try:
    from knowledge import KnowledgeService, DecisionNode, ReasoningTrace, RetrievedContext
except ImportError:
    # Fallback if knowledge service not fully set up
    from knowledge import KnowledgeService, RetrievedContext
    DecisionNode = Any
    ReasoningTrace = Any
from verification import VerificationOrchestra
from bandit import ThompsonBandit, GenerationStats, SpeculativeExecutor
from history import SDOHistory
from cache import SemanticCache, get_cache
from router import LLMRouter, get_router, init_router, ChatRequest, ChatMessage
from policy import PolicyEngine, get_policy_engine, PolicyResult
from agents.code_generator import CodeGenerator
from agents.test_generator import TestGenerator
from agents.doc_generator import DocGenerator
from agents.refactor_agent import RefactorAgent
from economics import EconomicsService, get_economics_service
from learner import LearnerModel
from memory import GraphRAG, VectorMemory, GraphMemory, MemoryConfig
from events import get_event_store, EventType, IVCUEventStore




class SDOEngine:
    """
    SDO Generation Engine (Phase 3)
    
    Features:
    - Thompson Sampling for adaptive strategy selection
    - Parallel candidate generation with pruning
    - Speculative execution with early stopping
    - Full undo/rollback support via history snapshots
    - Semantic caching for similar intents (Phase 3)
    - Multi-LLM routing with fallback (Phase 3)
    - Policy enforcement for code safety (Phase 3)
    """
    
    def __init__(
        self, 
        llm_service: LLMService, 
        knowledge_service=None,
        bandit_persistence_path: Optional[str] = None,
        history_persistence_dir: Optional[str] = None,
        enable_cache: bool = True,
        enable_policy: bool = True,

        database_service: Any = None,
        stream_callback: Any = None
    ):
        self.llm = llm_service
        self.knowledge = knowledge_service
        self.db = database_service
        self.stream_callback = stream_callback

        self.learner = LearnerModel(knowledge_service, llm_service, database_service) # Phase E
        self.orchestra = VerificationOrchestra()
        self.event_store: Optional[IVCUEventStore] = None

        
        # Agent Pool
        self.code_agent = CodeGenerator(llm_service)
        self.test_agent = TestGenerator(llm_service)
        self.doc_agent = DocGenerator(llm_service)
        self.refactor_agent = RefactorAgent(llm_service)
        
        # Economics
        self.economics = get_economics_service()
        
        # Phase 2: Adaptive generation
        self.bandit = ThompsonBandit(persistence_path=bandit_persistence_path)
        self.history = SDOHistory(persistence_dir=history_persistence_dir)
        self.speculator = SpeculativeExecutor()
        
        # Phase 3: Intelligence layer
        self.cache = get_cache() if enable_cache else None
        self.router = init_router(llm_service)
        self.policy = get_policy_engine() if enable_policy else None
        
        # Phase 4: GraphRAG
        self.rag = None
        self._init_rag()
        
        # Stats tracking
        self._generation_count = 0
        self._success_count = 0
        self._cache_hits = 0
        
    def _init_rag(self):
        """Initialize Tier 3 Memory (GraphRAG)"""
        try:
            vector = VectorMemory() # Embed helper needed in real app
            graph = GraphMemory()
            self.rag = GraphRAG(vector, graph)
            # Async init needed, usually done in startup
            # For now we lazy init or assume external init
        except Exception as e:
            print(f"GraphRAG init failed: {e}")

    async def generate_candidates(
        self,
        sdo: SDO,
        count: int = 3,
        temperature_range: tuple = (0.1, 0.7)
    ) -> List[Candidate]:
        """
        Generate multiple candidates in parallel.
        """
        sdo.status = SDOStatus.GENERATING
        candidates = []
        
        # Phase 4: Init Event Store
        if not self.event_store and self.db:
             # Assume db service has a pool or we get it somehow. 
             # For now, we lazily init or assume global pool availability if integrated
             self.event_store = await get_event_store(getattr(self.db, 'pool', None))
             
             # Emit Intent Created Event if first time
             try:
                 await self.event_store.append_event(
                     ivcu_id=sdo.id,
                     event_type=EventType.INTENT_CREATED,
                     event_data={
                         "raw_intent": sdo.raw_intent,
                         "parsed_intent": sdo.parsed_intent,
                         "language": sdo.language
                     }
                 )
             except Exception as e:
                 print(f"Event Store Error: {e}")

        
        # RAG Context Retrieval (Phase 4: GraphRAG)
        retrieved_context_str = ""
        
        # Try GraphRAG first
        if self.rag:
            try:
                rag_result = await self.rag.retrieve(sdo.raw_intent)
                retrieved_context_str = rag_result.get("synthesis", "")
                sdo.retrieved_context = rag_result
                print(f"DEBUG: GraphRAG retrieved context len={len(retrieved_context_str)}")
            except Exception as e:
                print(f"GraphRAG retrieval failed: {e}")
        
        # Fallback to legacy KnowledgeService if no RAG or empty
        if not retrieved_context_str and self.knowledge:
            try:
                context = await self.knowledge.retrieve_context_for_intent(sdo.raw_intent)
                retrieved_context_str = context.to_prompt_str()
                sdo.retrieved_context = context.model_dump()
            except Exception as e:
                print(f"Legacy RAG retrieval failed: {e}")

        # Async generation
        tasks = []
        for i in range(count):
            # Linearly interpolate temperature
            if count > 1:
                temp = temperature_range[0] + (i / (count - 1)) * (temperature_range[1] - temperature_range[0])
            else:
                temp = temperature_range[0]
                
            tasks.append(self._generate_single(sdo, temp, i, retrieved_context_str))
            
        results = await asyncio.gather(*tasks)
        sdo.candidates = [c for c in results if c is not None]
        
        return sdo.candidates

    async def _generate_single(
        self,
        sdo: SDO,
        temperature: float,
        index: int,
        context_str: str = ""
    ) -> Optional[Candidate]:
        """Generate a single candidate"""
        try:
            # Augment prompt if context exists
            prompt_context = sdo.model_copy() # Shallow copy
            if context_str:
                if not prompt_context.parsed_intent:
                    prompt_context.parsed_intent = {}
                prompt_context.parsed_intent["_rag_context"] = context_str

            # Phase E: Adaptive Learning
            # Retrieve learned guidance/lessons for this intent or project
            print(f"DEBUG: Checking Learner for guidance on intent: {sdo.raw_intent[:20]}...")
            learned_constraints = await self.learner.get_guidance(sdo.raw_intent)
            if learned_constraints:
                print(f"DEBUG: Found {len(learned_constraints)} learned constraints.")
                # Inject into constraints list
                if not prompt_context.constraints:
                     prompt_context.constraints = []
                prompt_context.constraints.extend(learned_constraints)

            # Phase 3: Check Semantic Cache
            if self.cache and index == 0:  # Only check once per batch
                cache_entry = await self.cache.get(
                    query=sdo.raw_intent,
                    model="gpt-4-turbo", # Default model for now
                    embedding=None # In real impl, pass embedding from memory_service
                )
                if cache_entry:
                    print(f"Cache Hit for intent: {sdo.raw_intent[:50]}...")
                    self._cache_hits += 1
                    return Candidate(
                        id=str(uuid.uuid4()),
                        code=cache_entry.response,
                        confidence=0.9, # High confidence for cached results
                        model_id=f"cache:{cache_entry.model}",
                        reasoning="Retrieved from Semantic Cache",
                        metadata={"cached_at": cache_entry.created_at}
                    )

            # Execute generation via Code Agent
            # Router logic temporarily bypassed in favor of Agent's structured output
            
            agent_result = await self.code_agent.run(prompt_context)
            
            if agent_result.success:
                code = agent_result.data.get("code", "")
                reasoning_raw = agent_result.data.get("reasoning", [])
                model_id = f"agent:code_generator:t{temperature:.1f}"
            else:
                print(f"Agent failed: {agent_result.error}")
                return None
            
            # Phase 3: Generate Reasoning Trace
            # Map LLM reasoning to DecisionNodes
            nodes = []
            if reasoning_raw:
                for i, step in enumerate(reasoning_raw):
                    nodes.append(DecisionNode(
                        id=str(i+1),
                        type="inference",
                        title=step.get("step", f"Step {i+1}"),
                        description=step.get("explanation", ""),
                        confidence=step.get("confidence", 0.8)
                    ))
                trace = ReasoningTrace(ivcu_id=sdo.id if sdo.id else str(uuid.uuid4()), nodes=nodes)
            else:
                # Fallback
                trace = self._generate_trace_for_candidate(sdo, model_id)
            
                result_candidate = Candidate(
                id=str(uuid.uuid4()),
                code=code,
                confidence=0.5,
                model_id=model_id,
                reasoning=f"Generated via Agent Pool (temp={temperature:.2f})",
                metadata={"reasoning_trace": trace.model_dump() if trace else None}
            )
            
            # Emit Candidate Generated Event
            if self.event_store:
                try:
                    await self.event_store.append_event(
                        ivcu_id=sdo.id,
                        event_type=EventType.CANDIDATE_GENERATED,
                        event_data={
                            "candidate_id": result_candidate.id,
                            "code": code,
                            "confidence": 0.5,
                            "model_id": model_id,
                            "reasoning": f"Generated via Agent Pool (temp={temperature:.2f})"
                        }
                    )
                except Exception as e: 
                    print(f"Event Store Error: {e}")
            
            # Stream Event
            if self.stream_callback:
                 await self.stream_callback(sdo.id, "CANDIDATE_GENERATED", {
                     "candidate_id": result_candidate.id, 
                     "model": model_id
                 })

            return result_candidate

        except Exception as e:
            print(f"Generation error: {e}")
            return None

    def _generate_trace_for_candidate(self, sdo: SDO, model_id: str) -> Optional[ReasoningTrace]:
        """Synthesize a reasoning trace for the candidate (Fallback)"""
        try:
            nodes = []
            nodes.append(DecisionNode(
                id="1",
                type="constraint",
                title="Intent Analysis",
                description=f"Analyzed intent. Extracted {len(sdo.constraints) if sdo.constraints else 0} constraints.",
                confidence=0.9
            ))
            return ReasoningTrace(ivcu_id=str(uuid.uuid4()), nodes=nodes)
        except Exception:
            return None
    
    async def verify_candidates(
        self,
        sdo: SDO,
        run_tier2: bool = True
    ) -> SDO:
        """
        Verify all candidates and update their scores.
        
        Args:
            sdo: SDO with candidates
            run_tier2: Whether to run Tier 2 verification
        
        Returns:
            Updated SDO with verification results
        """
        sdo.status = SDOStatus.VERIFYING
        
        if not sdo.candidates:
            return sdo
        
        if self.policy:
            for candidate in sdo.candidates:
                # Skip if already pruned or failed (though usually fresh here)
                res = self.policy.check_post_generation(candidate.code)
                if not res.passed:
                    candidate.verification_passed = False
                    candidate.verification_score = 0.0
                    candidate.verification_result = {"policy_violations": [v.to_dict() for v in res.violations]}
                    # Mark as pruned/failed so we don't waste resources in proper verification?
                    # For now just let it fail.
        
        # Verify all candidates in parallel (only those that passed policy if we wanted to optmize, 
        # but let's run all for now or filter)
        candidates_to_verify = [
            {"id": c.id, "code": c.code} 
            for c in sdo.candidates 
            if c.verification_passed is not False # Explicitly False means policy failed
        ]
        
        if not candidates_to_verify:
             return sdo

        results = await self.orchestra.verify_parallel_candidates(
            candidates=candidates_to_verify,
            sdo_id=sdo.id,
            language=sdo.language,
            contracts=[c.model_dump() for c in sdo.contracts]
        )
        
        # Update candidates with verification results
        result_map = {r.candidate_id: r for r in results}
        
        for candidate in sdo.candidates:
            if candidate.id in result_map:
                vr = result_map[candidate.id]
                candidate.verification_passed = vr.passed
                # Combine with existing score if any? 
                candidate.verification_score = vr.confidence
                candidate.verification_result = vr.model_dump()
                candidate.confidence = (candidate.confidence + vr.confidence) / 2
                

                    
                # Emit Verification Event (Phase 4)
                try:
                    if self.event_store:
                        await self.event_store.append_event(
                            ivcu_id=sdo.id,
                            event_type=EventType.VERIFICATION_COMPLETED,
                            event_data={
                                "candidate_id": candidate.id,
                                "passed": vr.passed,
                                "score": vr.confidence,
                                "results": vr.model_dump()
                            }
                        )
                except Exception as e:
                    print(f"Event emission failed: {e}")
                    
                # Stream Event
                if self.stream_callback:
                     await self.stream_callback(sdo.id, "VERIFICATION_COMPLETED", {
                         "candidate_id": candidate.id,
                         "passed": vr.passed,
                         "score": vr.confidence
                     })


        
        # Phase 5: Trigger Learning from Feedback

        # If the best candidate (or any significant failure) occurred, learn.
        # We can learn from the whole SDO results.
        if self.learner:
             # Fire and forget / async
             asyncio.create_task(self.learner.learn_from_feedback(sdo))

        return sdo

    
    async def select_best_candidate(
        self,
        sdo: SDO,
        strategy: str = "verification_score"
    ) -> Optional[Candidate]:
        """
        Select the best candidate based on strategy.
        
        Strategies:
        - verification_score: Highest verification confidence
        - combined: Weighted combination of generation and verification
        - first_passing: First candidate that passes verification
        
        Returns:
        """
        if not sdo.candidates:
            return None
        
        # Filter to non-pruned candidates
        active = [c for c in sdo.candidates if not c.pruned]
        
        if not active:
            return None
        
        if strategy == "verification_score":
            # Sort by verification score, then confidence
            sorted_candidates = sorted(
                active,
                key=lambda c: (c.verification_passed, c.verification_score),
                reverse=True
            )
        elif strategy == "combined":
            # Weighted score
            sorted_candidates = sorted(
                active,
                key=lambda c: c.confidence * 0.4 + c.verification_score * 0.6,
                reverse=True
            )
        elif strategy == "first_passing":
            # First one that passed
            passing = [c for c in active if c.verification_passed]
            sorted_candidates = passing if passing else active
        else:
            sorted_candidates = active
        
        best = sorted_candidates[0]
        
        # Update SDO
        sdo.selected_candidate_id = best.id
        sdo.code = best.code
        sdo.confidence = best.confidence
        sdo.verification_result = best.verification_result
        sdo.status = SDOStatus.VERIFIED if best.verification_passed else SDOStatus.FAILED
        
        # Emit Candidate Selected Event
        if self.event_store and best:
             await self.event_store.append_event(
                ivcu_id=sdo.id,
                event_type=EventType.CANDIDATE_SELECTED,
                event_data={
                    "candidate_id": best.id,
                    "code": best.code,
                    "confidence": best.confidence,
                    "verification_result": best.verification_result
                }
            )

        
        return best
    
    async def prune_candidates(
        self,
        sdo: SDO,
        keep_top: int = 2,
        min_confidence: float = 0.3
    ) -> List[Candidate]:
        """
        Prune low-quality candidates.
        
        Args:
            sdo: SDO with candidates
            keep_top: Number of top candidates to keep
            min_confidence: Minimum confidence to avoid pruning
        
        Returns:
            List of remaining active candidates
        """
        if not sdo.candidates:
            return []
        
        # Sort by confidence
        sorted_candidates = sorted(
            sdo.candidates,
            key=lambda c: c.verification_score if c.verification_score > 0 else c.confidence,
            reverse=True
        )
        
        # Keep top N and any above min_confidence
        for i, candidate in enumerate(sorted_candidates):
            if i >= keep_top and candidate.confidence < min_confidence:
                candidate.pruned = True
        
        return [c for c in sdo.candidates if not c.pruned]
    
    async def full_generation_flow(
        self,
        sdo: SDO,
        candidate_count: int = 3,
        use_adaptive: bool = True
    ) -> SDO:
        """
        Complete generation flow: generate → verify → select.
        
        Args:
            sdo: SDO with parsed intent
            candidate_count: Number of candidates to generate (may be overridden by bandit)
            use_adaptive: Whether to use Thompson Sampling for strategy selection
        
        Returns:
            SDO with selected code
        """
        # Snapshot before generation for undo
        self.history.snapshot(sdo, "before_generation")
        
        # Phase 2: Use bandit for adaptive strategy selection
        if use_adaptive:
            arm = self.bandit.select_arm()
            candidate_count = arm.candidate_count
            temperature_range = (max(0.1, arm.temperature - 0.2), arm.temperature + 0.1)
            sdo.generation_strategy = {
                "arm_id": arm.id,
                "temperature": arm.temperature,
                "candidate_count": arm.candidate_count
            }
        else:
            arm = None
            temperature_range = (0.1, 0.7)
            
        # Phase 3: Policy Pre-Check
        if self.policy:
            try:
                policy_res = self.policy.check_pre_generation(sdo.raw_intent)
                if not policy_res.passed:
                    sdo.status = SDOStatus.FAILED
                    msg = policy_res.violations[0].message if policy_res.violations else "Unknown Policy Violation"
                    sdo.error = f"Policy Violation: {msg}"
                    return sdo
            except Exception as e:
                print(f"Policy Engine Error: {e}")
                # Fallback: Allow generation but log error
                # OR fail safe? Let's fail safe if we can't check policy.
                # sdo.status = SDOStatus.FAILED
                # sdo.error = f"Policy check failed: {e}"
                # return sdo
                pass # For now, proceed if policy crashes to avoid total service failure

        # --- Economic Check ---
        estimate = self.economics.estimate_generation_cost(
            intent=sdo.raw_intent, 
            language=sdo.language,
            candidate_count=candidate_count
        )
        # Using a fixed session for user in dev
        can_proceed, msg, warning = self.economics.check_budget("dev-session", estimate.estimated_cost_usd)
        
        if warning:
            # TODO: Propagate warning to UI via SDO
            pass
            
        if not can_proceed:
            sdo.status = SDOStatus.FAILED
            sdo.error = f"Budget exceeded: {msg}"
            return sdo
        # ----------------------
        
            # Phase 4: Event Bus - Start
            # Note: Event emission disabled due to NATS client instability (serialization/crash)
            # try:
            #     bus = await eventbus.get_event_bus()
            #     if bus:
            #         await bus.emit_generation_started(
            #             ivcu_id=sdo.id,
            #             intent=sdo.raw_intent,
            #             model_id="gpt-4-turbo"
            #         )
            # except Exception as e:
            #     print(f"Event emission failed: {e}")

        # 1. Generate candidates
        await self.generate_candidates(sdo, count=candidate_count, temperature_range=temperature_range)
        
        if not sdo.candidates:
            sdo.status = SDOStatus.FAILED
            if arm:
                self.bandit.update(arm.id, reward=0.0, intent_type=self._get_intent_type(sdo))
            
            # Phase 4: Event Bus - Failure
            try:
                bus = await eventbus.get_event_bus()
                if bus:
                    await bus.emit_generation_completed(
                        ivcu_id=sdo.id,
                        candidate_id="none",
                        success=False,
                        tokens_used=0,
                        cost=0.0
                    )
            except Exception as e:
                print(f"Event emission failed: {e}")
                
            return sdo
        
        # 2. Quick verify (Tier 1 only) and prune
        await self.verify_candidates(sdo, run_tier2=False)
        await self.prune_candidates(sdo, keep_top=2)
        
        # 3. Full verify remaining
        # 3. Full verify remaining
        await self.verify_candidates(sdo, run_tier2=True)
        
        # --- Record Cost ---
        # Rough estimation of actuals based on generated lengths
        # In production, LLMService would return exact usage, here we approximate or would need to thread usage back
        total_input = estimate.input_tokens # Use estimate for now
        total_output = sum(len(c.code)//4 for c in sdo.candidates) # Approx
        
        self.economics.record_usage(
            session_id="dev-session",
            sdo_id=sdo.id,
            operation="generate",
            model="gpt-4-turbo",
            input_tokens=total_input,
            output_tokens=total_output
        )
        # -------------------
        
        # 4. Select best
        best = await self.select_best_candidate(sdo)
        
        # Phase 4: Event Bus - Complete
        try:
            bus = await eventbus.get_event_bus()
            if bus and best:
                await bus.emit_generation_completed(
                    ivcu_id=sdo.id,
                    candidate_id=best.id,
                    success=best.verification_passed,
                    tokens_used=total_input + total_output,
                    cost=estimate.estimated_cost_usd # Approx
                )
        except Exception as e:
            print(f"Event emission failed: {e}")
        
        # 5. Update bandit with result
        if arm and best:
            reward = (best.verification_score if best.verification_passed else 0.0) * best.confidence
            self.bandit.update(arm.id, reward=reward, intent_type=self._get_intent_type(sdo))
            self._generation_count += 1
            if best.verification_passed:
                self._success_count += 1
                
                # Phase 3: Update Cache
                if self.cache:
                    await self.cache.set(
                        query=sdo.raw_intent,
                        response=best.code,
                        model="gpt-4-turbo"
                    )
        
        # 6. Record step and snapshot
        sdo.add_step(
            step_type="generation",
            content={
                "candidates_generated": len(sdo.candidates),
                "selected_id": sdo.selected_candidate_id,
                "strategy": sdo.generation_strategy if hasattr(sdo, 'generation_strategy') else None,
                "bandit_stats": self.get_stats()
            },
            confidence=sdo.confidence,
            model="sdo_engine_v2"
        )
        
        self.history.snapshot(sdo, "after_generation")
        
        return sdo
    
    async def adaptive_generation_flow(
        self,
        sdo: SDO,
        early_stop_threshold: float = 0.9
    ) -> SDO:
        """
        Speculative generation with early stopping.
        
        Generates candidates one at a time, verifying immediately.
        Stops early if a high-confidence candidate is found.
        
        Args:
            sdo: SDO with parsed intent
            early_stop_threshold: Confidence threshold for early stopping
        
        Returns:
            SDO with selected code
        """
        self.history.snapshot(sdo, "before_adaptive_generation")
        
        arm = self.bandit.select_arm()
        sdo.generation_strategy = {"arm_id": arm.id, "mode": "speculative"}
        sdo.status = SDOStatus.GENERATING
        
        # RAG context retrieval
        retrieved_context_str = ""
        if self.knowledge:
            try:
                context = await self.knowledge.retrieve_context_for_intent(sdo.raw_intent)
                retrieved_context_str = context.to_prompt_str()
                sdo.retrieved_context = context.model_dump()
            except Exception as e:
                print(f"RAG retrieval failed: {e}")
        
        # Speculative execution
        candidates = []
        for i in range(arm.candidate_count):
            temp = arm.temperature + (i * 0.1)  # Slight variation
            candidate = await self._generate_single(sdo, temp, i, retrieved_context_str)
            
            if not candidate:
                continue
            
            # Immediate verification
            result = await self.orchestra.quick_verify(
                candidate.code, sdo.id, sdo.language
            )
            
            candidate.verification_passed = result.passed
            candidate.verification_score = result.confidence
            candidate.verification_result = result.model_dump()
            candidates.append(candidate)
            
            # Early stop if high confidence
            if result.passed and result.confidence >= early_stop_threshold:
                break
        
        sdo.candidates = candidates
        sdo.status = SDOStatus.VERIFYING
        
        # Select best and update bandit
        if candidates:
            best = await self.select_best_candidate(sdo)
            if best:
                reward = best.verification_score * (1.0 if best.verification_passed else 0.3)
                self.bandit.update(arm.id, reward=reward)
        else:
            sdo.status = SDOStatus.FAILED
            self.bandit.update(arm.id, reward=0.0)
        
        self.history.snapshot(sdo, "after_adaptive_generation")
        
        return sdo
    
    def undo(self, sdo_id: str) -> Optional[Dict[str, Any]]:
        """
        Undo the last operation on an SDO.
        
        Returns:
            Previous state dict, or None if no history
        """
        return self.history.undo(sdo_id)
    
    def redo(self, sdo_id: str) -> Optional[Dict[str, Any]]:
        """
        Redo the last undone operation.
        
        Returns:
            Next state dict, or None if at latest
        """
        return self.history.redo(sdo_id)
    
    def get_history(self, sdo_id: str) -> List[dict]:
        """Get operation history for an SDO."""
        return self.history.list_snapshots(sdo_id)
    
    def get_stats(self) -> dict:
        """Get generation statistics."""
        return {
            "total_generations": self._generation_count,
            "successful": self._success_count,
            "success_rate": self._success_count / max(self._generation_count, 1),
            "bandit_arms": self.bandit.get_arm_stats(),
                "overall_stats": {
                    "avg_confidence": self.bandit.stats.avg_confidence,
                    "intent_type_stats": self.bandit.stats.intent_type_stats
                }
            }
        
    async def generate_counterfactual(self, base_sdo: SDO, prompt: str) -> SDO:
        """
        Fork a verified SDO and regenerate it based on a "What If" prompt.
        """
        print(f"SDO_ENGINE: Generating counterfactual for {base_sdo.id}: '{prompt}'")
        
        # 1. Fork SDO
        import uuid
        variant_sdo = SDO(
            id=str(uuid.uuid4()),
            raw_intent=base_sdo.raw_intent, # Keep original intent
            language=base_sdo.language,
            status=SDOStatus.DRAFT,
            meta={
                "forked_from": base_sdo.id,
                "counterfactual_prompt": prompt,
                "type": "counterfactual"
            }
        )
        
        # 2. Construct Prompt Context with explicit override
        # We treat the counterfactual prompt as a "Hard Constraint" that overrides previous decisions
        prompt_context = PromptContext(
            intent=base_sdo.raw_intent,
            tech_stack=[], # Let it re-decide or imply from prompt
            constraints=[f"CONSTRAINT: {prompt}", "Maintain original functionality where possible."],
            examples=[]
        )
        
        # 3. Retrieve relevant context (similar to standard flow but maybe focused on the difference)
        # For now, reuse standard search
        docs = await self.knowledge.search(prompt + " " + base_sdo.raw_intent)
        variant_sdo.retrieved_context = [d.content for d in docs[:2]]
        
        # 4. Generate Code
        # We use a specific system prompt for counterfactuals to encourage exploration
        system_prompt = """
        You are an AXIOM Counterfactual Engine.
        Your goal is to rewrite the provided implementation to satisfy a new "What If" constraint.
        
        Original Implementation is provided for context.
        You must Strict adhere to the new constraint.
        """
        
        user_prompt = f"""
        Original Intent: {base_sdo.raw_intent}
        
        Original Code:
        {base_sdo.code}
        
        NEW CONSTRAINT / WHAT IF:
        {prompt}
        
        Output the complete rewritten code.
        """
        
        response = await self.llm.complete(user_prompt, system_prompt=system_prompt)
        
        # 5. Create Candidate
        candidate = Candidate(
            id=str(uuid.uuid4()),
            sdo_id=variant_sdo.id,
            code=response,
            model_id="counterfactual-v1",
            confidence=0.85 # Heuristic
        )
        
        # 6. Verify (Lightweight for speed in exploration)
        vr = await self.orchestra.verify(candidate.code, variant_sdo.language)
        candidate.verification_passed = vr.valid
        candidate.verification_result = vr.to_dict()
        candidate.verification_score = 1.0 if vr.valid else 0.5
        
        variant_sdo.candidates = [candidate]
        variant_sdo.selected_candidate_id = candidate.id
        variant_sdo.code = candidate.code
        variant_sdo.status = SDOStatus.VERIFIED if vr.valid else SDOStatus.FAILED
        
        # Persist
        if self.db:
            await self.db.save_sdo(variant_sdo.model_dump())
            
        return variant_sdo
    
    def _get_intent_type(self, sdo: SDO) -> str:
        """Extract intent type for stats tracking."""
        if sdo.parsed_intent and isinstance(sdo.parsed_intent, dict):
            return sdo.parsed_intent.get("action", "unknown")
        return "unknown"
