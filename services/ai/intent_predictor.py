
import random
from typing import List, Optional

class IntentPredictor:
    """
    Predicts the next likely user intent based on context/history.
    Start with heuristics/LLM, move to dedicated ML model later.
    """
    
    def __init__(self, llm_service=None):
        self.llm = llm_service
        
    async def predict_next(self, current_intent: str, recent_history: List[str]) -> Optional[str]:
        """
        Predict what the user might want next.
        """
        # Heuristic 1: If user just created a Type/Interface, they might want a Function/Implementation
        if "interface" in current_intent.lower() or "type" in current_intent.lower():
            return f"Implement function satisfying {current_intent}"
            
        # Heuristic 2: If user implemented a function, they might want tests
        if "implement" in current_intent.lower() or "function" in current_intent.lower():
            return "Generate unit tests for previous code"
            
        # LLM-based prediction (if available)
        if self.llm:
            try:
                # Mock call for now to save tokens, or use cheap model
                # prompt = f"History: {recent_history}\nCurrent: {current_intent}\nNext likely command?"
                pass
            except Exception:
                pass
                
        return None

    def should_speculate(self, confidence: float) -> bool:
        """Decide if we should trigger speculation"""
        return confidence > 0.7
