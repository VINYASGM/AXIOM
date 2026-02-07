import pytest
import asyncio
from unittest.mock import MagicMock, patch
from verification.tier3 import Tier3Verifier
from verification.orchestra import VerificationOrchestra
from verification.result import VerificationTier

@pytest.mark.asyncio
async def test_tier3_smt_integration():
    """
    Test that Tier3Verifier correctly calls SMTVerifier when contracts are provided.
    """
    # Mock code and contracts
    code = "def add(x, y): return x + y"
    contracts = [{"type": "precondition", "expression": "x > 0", "description": "Positive input"}]
    
    # Initialize Verifier
    verifier = Tier3Verifier()
    
    # Mock get_smt_verifier to avoid Z3 dependency issues
    with patch("verification.tier3.get_smt_verifier") as mock_get_smt:
        mock_smt = MagicMock()
        mock_get_smt.return_value = mock_smt
        
        # Mock async return value
        future = asyncio.Future()
        mock_result = MagicMock()
        mock_result.status = "sat"
        mock_result.solve_time_ms = 100.0
        mock_result.assertions = []
        future.set_result(mock_result)
        mock_smt.verify_contracts.return_value = future
        
        # Run Verification
        results = await verifier.verify_all(code, language="python", contracts=contracts)
        
        # Assertions
        assert len(results) == 3 # Security, Fuzz, SMT
        
        smt_result = results[2]
        assert smt_result.name == "smt_solver"
        assert smt_result.passed == True
        
        # Verify call arguments
        mock_smt.verify_contracts.assert_called_once_with(code, contracts, "python")

@pytest.mark.asyncio
async def test_orchestra_contract_passing():
    """
    Test that Orchestra passes contracts to Tier 3.
    """
    # Mock LLM service
    orchestra = VerificationOrchestra(None)
    
    # Mock Tier 3
    orchestra.tier3 = MagicMock()
    future = asyncio.Future()
    future.set_result([MagicMock(passed=True)])
    orchestra.tier3.verify_all.return_value = future
    
    # Mock Tier 1 & 2 to pass
    orchestra.tier1 = MagicMock()
    t1_future = asyncio.Future()
    t1_future.set_result([MagicMock(passed=True)])
    orchestra.tier1.verify_all.return_value = t1_future
    
    orchestra.tier2 = MagicMock()
    t2_future = asyncio.Future()
    t2_future.set_result([MagicMock(passed=True)])
    orchestra.tier2.verify_all.return_value = t2_future

    code = "pass"
    contracts = [{"test": "contract"}]
    
    await orchestra.verify(
        code=code, 
        sdo_id="test", 
        run_tier3=True, 
        contracts=contracts
    )
    
    # Check if contracts were passed to Tier 3
    orchestra.tier3.verify_all.assert_called_once()
    args = orchestra.tier3.verify_all.call_args
    assert args[1]['contracts'] == contracts or args[0][2] == contracts # Handle keyword vs positional
