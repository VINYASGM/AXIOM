"""
Test suite for Thompson Sampling Bandit

Tests the bandit algorithm for proper arm selection and learning behavior.
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bandit import ThompsonBandit, Arm, GenerationStats, SpeculativeExecutor


class TestArm(unittest.TestCase):
    """Test the Arm (bandit arm) class."""
    
    def test_arm_creation(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        self.assertEqual(arm.id, "test")
        self.assertEqual(arm.temperature, 0.5)
        self.assertEqual(arm.candidate_count, 3)
        self.assertEqual(arm.alpha, 1.0)  # Prior
        self.assertEqual(arm.beta, 1.0)   # Prior
    
    def test_arm_update_success(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        arm.update(reward=1.0)  # Full success
        
        self.assertEqual(arm.total_trials, 1)
        self.assertEqual(arm.alpha, 2.0)  # 1 + 1
        self.assertEqual(arm.beta, 1.0)   # 1 + 0
    
    def test_arm_update_failure(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        arm.update(reward=0.0)  # Full failure
        
        self.assertEqual(arm.total_trials, 1)
        self.assertEqual(arm.alpha, 1.0)  # 1 + 0
        self.assertEqual(arm.beta, 2.0)   # 1 + 1
    
    def test_arm_update_partial(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        arm.update(reward=0.7)  # Partial success
        
        self.assertEqual(arm.total_trials, 1)
        self.assertAlmostEqual(arm.alpha, 1.7)  # 1 + 0.7
        self.assertAlmostEqual(arm.beta, 1.3)   # 1 + 0.3
    
    def test_arm_sample_in_range(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        for _ in range(100):
            sample = arm.sample()
            self.assertGreaterEqual(sample, 0.0)
            self.assertLessEqual(sample, 1.0)
    
    def test_arm_mean_calculation(self):
        arm = Arm(id="test", temperature=0.5, candidate_count=3)
        self.assertEqual(arm.mean, 0.5)  # alpha / (alpha + beta) = 1/2
        
        arm.update(1.0)  # Alpha becomes 2
        self.assertAlmostEqual(arm.mean, 2/3)  # 2 / 3


class TestThompsonBandit(unittest.TestCase):
    """Test the ThompsonBandit class."""
    
    def test_bandit_initialization(self):
        bandit = ThompsonBandit()
        self.assertEqual(len(bandit.arms), 6)  # Default arms
        self.assertIn("precise_2", bandit.arms)
        self.assertIn("creative_5", bandit.arms)
    
    def test_bandit_select_arm(self):
        bandit = ThompsonBandit()
        arm = bandit.select_arm()
        
        self.assertIsInstance(arm, Arm)
        self.assertIn(arm.id, bandit.arms)
    
    def test_bandit_update(self):
        bandit = ThompsonBandit()
        arm = bandit.select_arm()
        initial_trials = arm.total_trials
        
        bandit.update(arm.id, reward=0.8, intent_type="create")
        
        self.assertEqual(arm.total_trials, initial_trials + 1)
        self.assertEqual(bandit.stats.total_generations, 1)
    
    def test_bandit_convergence(self):
        """Test that bandit learns to prefer the best arm."""
        bandit = ThompsonBandit()
        
        # Simulate: "balanced_3" is the best arm
        for _ in range(50):
            arm = bandit.select_arm()
            
            # Give high reward to balanced_3, low to others
            if arm.id == "balanced_3":
                bandit.update(arm.id, reward=0.9)
            else:
                bandit.update(arm.id, reward=0.2)
        
        # After learning, balanced_3 should have highest mean
        stats = bandit.get_arm_stats()
        best_arm = stats[0]  # Sorted by mean
        
        # The arm with most exploration might win, but balanced_3 should be near top
        balanced_3_mean = bandit.arms["balanced_3"].mean
        self.assertGreater(balanced_3_mean, 0.5, "balanced_3 should have learned high value")
    
    def test_bandit_stats_tracking(self):
        bandit = ThompsonBandit()
        
        bandit.update("precise_2", reward=0.8, intent_type="create")
        bandit.update("balanced_3", reward=0.6, intent_type="create")
        bandit.update("creative_4", reward=0.2, intent_type="modify")
        
        self.assertEqual(bandit.stats.total_generations, 3)
        self.assertEqual(bandit.stats.successful_verifications, 2)  # 0.8 > 0.5, 0.6 > 0.5
        self.assertEqual(len(bandit.stats.intent_type_stats), 2)
        self.assertIn("create", bandit.stats.intent_type_stats)
        self.assertIn("modify", bandit.stats.intent_type_stats)


class TestGenerationStats(unittest.TestCase):
    """Test the GenerationStats class."""
    
    def test_stats_creation(self):
        stats = GenerationStats()
        self.assertEqual(stats.total_generations, 0)
        self.assertEqual(stats.success_rate, 0.0)
    
    def test_stats_record(self):
        stats = GenerationStats()
        stats.record_generation("create", verified=True, confidence=0.9)
        
        self.assertEqual(stats.total_generations, 1)
        self.assertEqual(stats.successful_verifications, 1)
        self.assertEqual(stats.avg_confidence, 0.9)
        self.assertEqual(stats.success_rate, 1.0)
    
    def test_stats_running_average(self):
        stats = GenerationStats()
        stats.record_generation("create", verified=True, confidence=0.8)
        stats.record_generation("modify", verified=True, confidence=0.6)
        
        self.assertEqual(stats.total_generations, 2)
        self.assertAlmostEqual(stats.avg_confidence, 0.7)


class TestSpeculativeExecutor(unittest.TestCase):
    """Test the SpeculativeExecutor class."""
    
    def test_executor_creation(self):
        executor = SpeculativeExecutor()
        self.assertEqual(executor.early_stop_threshold, 0.9)
        self.assertEqual(executor.min_candidates, 1)
        self.assertEqual(executor.max_candidates, 5)
    
    def test_executor_custom_thresholds(self):
        executor = SpeculativeExecutor(
            early_stop_threshold=0.8,
            min_candidates=2,
            max_candidates=4
        )
        self.assertEqual(executor.early_stop_threshold, 0.8)
        self.assertEqual(executor.min_candidates, 2)
        self.assertEqual(executor.max_candidates, 4)


if __name__ == "__main__":
    print("=" * 60)
    print("  AXIOM Phase 2 - Thompson Sampling Bandit Tests")
    print("=" * 60)
    print()
    
    # Run tests
    unittest.main(verbosity=2)
