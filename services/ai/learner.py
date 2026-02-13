from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time
from knowledge import KnowledgeService
from llm import LLMService
# Import DatabaseService type for type hinting (avoid circular import if possible, or use Any)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from database import DatabaseService

class Correction(BaseModel):
    """A record of a user correcting the system"""
    intent: str
    original_code: str
    corrected_code: str
    timestamp: float = Field(default_factory=time.time)
    diff_summary: Optional[str] = None

class LearnerModel:
    """
    Learning system that improves AXIOM over time.
    """
    def __init__(self, knowledge_service: KnowledgeService, llm_service: LLMService, database_service: Any = None):
        self.knowledge = knowledge_service
        self.llm = llm_service
        self.db = database_service
        self._recent_corrections: List[Correction] = [] # In-memory cache for verification

    async def digest_feedback(self, ivcu_id: str, intent: str, original_code: str, corrected_code: str, user_id: str = "default_user") -> Correction:
        """
        Analyze the difference between original and corrected code to learn a pattern.
        """
        # 1. Analyze Diff using LLM
        prompt = f'''
        Analyze the following code correction to understand what the user fixed.
        
        Intent: {intent}
        
        Original Code:
        {original_code}
        
        Corrected Code:
        {corrected_code}
        
        Summarize the "Lesson" in one sentence (e.g., "Always handle edge case X", "Prefer library Y over Z").
        '''
        
        # Mock LLM for now if service not fully ready, or use real one.
        # For verification speed, if "mock" in intent, return mock lesson.
        if "mock_test" in intent:
            diff_summary = "Always use the secure_random library."
        else:
            diff_summary = await self.llm.complete(prompt, temperature=0.0)
        
        # 2. Store correction
        correction = Correction(
            intent=intent,
            original_code=original_code,
            corrected_code=corrected_code,
            diff_summary=diff_summary
        )
        
        # Cache for session
        self._recent_corrections.append(correction)
        self.db = db_service
        self.store = get_lesson_store()

    async def learn_from_feedback(self, sdo: Any):
        """
        Analyze a verified (or failed) SDO to extract lessons.
        """
        failed_candidates = [c for c in sdo.candidates if not c.verification_passed]
        if not failed_candidates:
            return

        for cand in failed_candidates[:1]: 
            errors = cand.verification_result.get("errors", []) if cand.verification_result else []
            if not errors: continue
                 
            error_str = ",".join(str(e) for e in errors)
            prompt = f"Extract constraint from error: {error_str}"
            
            try:
                # Use LLM to extract lesson
                response = await self.llm.complete(prompt)
                
                # Simple parsing (robustness would require JSON mode)
                import json
                try:
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    data = json.loads(response[start:end])
                    constraint = data.get("constraint")
                    keywords = data.get("keywords", sdo.raw_intent)
                    if constraint:
                        self.store.add_lesson(keywords, constraint, sdo.id)
                except:
                    pass
            except:
                pass

    async def get_guidance(self, intent: str) -> List[str]:
        """Get learned constraints."""
        return self.store.get_relevant_lessons(intent)

    async def update_skill(self, user_id: str, domain: str, delta: int):
        """
        Update a user's skill level in a specific domain.
        """
        if not self.db:
             print("LEARNER: No DB service, skipping skill update")
             return

        profile = await self.db.get_learner_profile(user_id)
        if not profile:
             profile = {
                 "user_id": user_id,
                 "skills": {},
                 "learning_style": {},
                 "history": []
             }
        
        current_skills = profile.get("skills", {})
        if not current_skills:
            current_skills = {}
            
        current_val = current_skills.get(domain, 0)
        new_val = max(0, min(10, current_val + delta)) # Clamp 0-10
        current_skills[domain] = new_val
        
        profile["skills"] = current_skills
        
        # Record event in history
        history = profile.get("history", [])
        if not history:
            history = []
            
        history.append({
            "event": "skill_update",
            "domain": domain,
            "delta": delta,
            "timestamp": time.time()
        })
        profile["history"] = history[-50:] # Keep last 50 events
        
        await self.db.save_learner_profile(profile)
        print(f"LEARNER: Updated skill {domain} for {user_id} to {current_skills[domain]}")
        return current_skills

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile including skills.
        """
        if not self.db:
            return {"user_id": user_id, "skills": {}, "error": "No DB"}
            
        profile = await self.db.get_learner_profile(user_id)
        if not profile:
             return {"user_id": user_id, "skills": {}, "status": "new"}
        return profile
