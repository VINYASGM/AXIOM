"""
Thompson Sampling Bandit for Adaptive Candidate Selection

Implements multi-armed bandit using Beta distributions to learn
optimal generation strategies (temperature, candidate count, model).

Inspired by Chronos SDO's γ-selection mechanism.
"""
import json
import random
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Arm:
    """A bandit arm representing a generation strategy."""
    id: str
    temperature: float
    candidate_count: int
    model_variant: str = "gpt-4-turbo"
    
    # Beta distribution parameters (successes, failures)
    alpha: float = 1.0  # Prior: 1 success
    beta: float = 1.0   # Prior: 1 failure
    
    # Stats
    total_trials: int = 0
    total_reward: float = 0.0
    
    def sample(self) -> float:
        """Sample from Beta distribution."""
        return random.betavariate(self.alpha, self.beta)
    
    def update(self, reward: float):
        """Update arm with observation. Reward should be in [0, 1]."""
        # Clamp reward to valid range
        reward = max(0.0, min(1.0, reward))
        
        # Beta-Bernoulli update with continuous reward
        self.alpha += reward
        self.beta += (1.0 - reward)
        self.total_trials += 1
        self.total_reward += reward
    
    @property
    def mean(self) -> float:
        """Expected value of arm."""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def ucb(self) -> float:
        """Upper confidence bound for exploration."""
        if self.total_trials == 0:
            return float('inf')
        return self.mean + math.sqrt(2 * math.log(self.total_trials + 1) / self.total_trials)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Arm':
        return cls(**data)


@dataclass
class GenerationStats:
    """Tracks generation statistics across sessions."""
    total_generations: int = 0
    total_verifications: int = 0
    successful_verifications: int = 0
    avg_confidence: float = 0.0
    intent_type_stats: Dict[str, Dict] = field(default_factory=dict)
    
    def record_generation(self, intent_type: str, verified: bool, confidence: float):
        """Record a generation outcome."""
        self.total_generations += 1
        self.total_verifications += 1
        if verified:
            self.successful_verifications += 1
        
        # Running average for confidence
        self.avg_confidence = (
            (self.avg_confidence * (self.total_generations - 1) + confidence) 
            / self.total_generations
        )
        
        # Per-intent-type stats
        if intent_type not in self.intent_type_stats:
            self.intent_type_stats[intent_type] = {
                "count": 0, "success": 0, "avg_conf": 0.0
            }
        
        stats = self.intent_type_stats[intent_type]
        stats["count"] += 1
        if verified:
            stats["success"] += 1
        stats["avg_conf"] = (
            (stats["avg_conf"] * (stats["count"] - 1) + confidence) 
            / stats["count"]
        )
    
    @property
    def success_rate(self) -> float:
        if self.total_verifications == 0:
            return 0.0
        return self.successful_verifications / self.total_verifications


class ThompsonBandit:
    """
    Thompson Sampling multi-armed bandit for generation strategy selection.
    
    Learns optimal combinations of:
    - Temperature (0.1 to 0.9)
    - Candidate count (2 to 5)
    - Model variant
    
    Usage:
        bandit = ThompsonBandit()
        arm = bandit.select_arm()
        # ... generate with arm.temperature, arm.candidate_count ...
        bandit.update(arm.id, reward=confidence_score * verified)
    """
    
    DEFAULT_ARMS = [
        # Low temp, few candidates (precise tasks)
        {"id": "precise_2", "temperature": 0.1, "candidate_count": 2},
        {"id": "precise_3", "temperature": 0.2, "candidate_count": 3},
        
        # Medium temp, medium candidates (balanced)
        {"id": "balanced_3", "temperature": 0.4, "candidate_count": 3},
        {"id": "balanced_4", "temperature": 0.5, "candidate_count": 4},
        
        # High temp, more candidates (creative tasks)
        {"id": "creative_4", "temperature": 0.7, "candidate_count": 4},
        {"id": "creative_5", "temperature": 0.8, "candidate_count": 5},
    ]
    
    def __init__(self, persistence_path: Optional[str] = None):
        """
        Initialize bandit with default arms.
        
        Args:
            persistence_path: Optional path to save/load state
        """
        self.arms: Dict[str, Arm] = {}
        self.stats = GenerationStats()
        self.persistence_path = persistence_path
        
        # Initialize default arms
        for arm_config in self.DEFAULT_ARMS:
            arm = Arm(**arm_config)
            self.arms[arm.id] = arm
        
        # Load persisted state if available
        if persistence_path:
            self._load()
    
    def select_arm(self, intent_type: Optional[str] = None) -> Arm:
        """
        Select an arm using Thompson Sampling.
        
        Args:
            intent_type: Optional hint for intent-aware selection
        
        Returns:
            Selected Arm with generation parameters
        """
        # Thompson Sampling: sample from each arm's Beta distribution
        samples = [(arm_id, arm.sample()) for arm_id, arm in self.arms.items()]
        
        # Select arm with highest sample
        best_arm_id = max(samples, key=lambda x: x[1])[0]
        return self.arms[best_arm_id]
    
    def select_arm_ucb(self, exploration_weight: float = 1.0) -> Arm:
        """
        Select using Upper Confidence Bound (alternative to Thompson).
        Better for initial exploration.
        """
        def ucb_score(arm: Arm) -> float:
            if arm.total_trials == 0:
                return float('inf')  # Prioritize unexplored
            exploitation = arm.mean
            exploration = exploration_weight * math.sqrt(
                2 * math.log(sum(a.total_trials for a in self.arms.values()) + 1) 
                / arm.total_trials
            )
            return exploitation + exploration
        
        return max(self.arms.values(), key=ucb_score)
    
    def update(self, arm_id: str, reward: float, intent_type: str = "unknown"):
        """
        Update arm with observation.
        
        Args:
            arm_id: ID of arm that was used
            reward: Reward signal in [0, 1], typically confidence * verified
            intent_type: Type of intent for stats tracking
        """
        if arm_id not in self.arms:
            return
        
        self.arms[arm_id].update(reward)
        self.stats.record_generation(intent_type, reward > 0.5, reward)
        
        # Persist if enabled
        if self.persistence_path:
            self._save()
    
    def get_arm_stats(self) -> List[dict]:
        """Get statistics for all arms."""
        return [
            {
                "id": arm.id,
                "temperature": arm.temperature,
                "candidate_count": arm.candidate_count,
                "trials": arm.total_trials,
                "mean": round(arm.mean, 3),
                "total_reward": round(arm.total_reward, 2),
            }
            for arm in sorted(self.arms.values(), key=lambda a: a.mean, reverse=True)
        ]
    
    def add_arm(self, arm: Arm):
        """Add a new arm to the bandit."""
        self.arms[arm.id] = arm
    
    def _save(self):
        """Persist state to disk."""
        if not self.persistence_path:
            return
        
        state = {
            "arms": {k: v.to_dict() for k, v in self.arms.items()},
            "stats": asdict(self.stats)
        }
        
        Path(self.persistence_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load(self):
        """Load state from disk."""
        if not self.persistence_path:
            return
        
        path = Path(self.persistence_path)
        if not path.exists():
            return
        
        try:
            with open(path, 'r') as f:
                state = json.load(f)
            
            # Restore arms
            for arm_id, arm_data in state.get("arms", {}).items():
                self.arms[arm_id] = Arm.from_dict(arm_data)
            
            # Restore stats
            stats_data = state.get("stats", {})
            self.stats = GenerationStats(
                total_generations=stats_data.get("total_generations", 0),
                total_verifications=stats_data.get("total_verifications", 0),
                successful_verifications=stats_data.get("successful_verifications", 0),
                avg_confidence=stats_data.get("avg_confidence", 0.0),
                intent_type_stats=stats_data.get("intent_type_stats", {})
            )
        except Exception as e:
            print(f"Failed to load bandit state: {e}")


class SpeculativeExecutor:
    """
    Manages speculative execution with early stopping.
    
    Generates candidates speculatively and stops early if
    high-confidence candidate is found.
    """
    
    def __init__(
        self,
        early_stop_threshold: float = 0.9,
        min_candidates: int = 1,
        max_candidates: int = 5
    ):
        self.early_stop_threshold = early_stop_threshold
        self.min_candidates = min_candidates
        self.max_candidates = max_candidates
    
    async def execute_with_early_stop(
        self,
        generate_fn,  # async callable returning Candidate
        verify_fn,    # async callable returning VerificationResult
        target_count: int = 3
    ) -> List[Tuple]:
        """
        Generate and verify speculatively with early stopping.
        
        Returns:
            List of (candidate, verification_result) tuples
        """
        import asyncio
        
        results = []
        target = min(target_count, self.max_candidates)
        
        for i in range(target):
            # Generate candidate
            candidate = await generate_fn(i)
            if not candidate:
                continue
            
            # Verify
            verification = await verify_fn(candidate)
            results.append((candidate, verification))
            
            # Early stop check
            if (
                len(results) >= self.min_candidates and
                verification.passed and
                verification.confidence >= self.early_stop_threshold
            ):
                break
        
        return results
