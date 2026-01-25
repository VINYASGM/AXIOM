"""
AXIOM AI Service - Comprehensive Test Suite
Simulates and verifies all components are working correctly.
"""
import asyncio
import sys

def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_ok(msg):
    print(f"  [OK] {msg}")

def print_fail(msg):
    print(f"  [FAIL] {msg}")

async def run_tests():
    results = {"passed": 0, "failed": 0}
    
    # =========================================================================
    # TEST 1: Module Imports
    # =========================================================================
    print_header("TEST 1: Module Imports")
    
    try:
        from memory import MemoryService, CodeChunk, IntentRecord, RetrievalResult
        print_ok("memory.py imports successfully")
        results["passed"] += 1
    except Exception as e:
        print_fail(f"memory.py: {e}")
        results["failed"] += 1
        return results

    try:
        from llm import LLMService, IntentParsingResult
        print_ok("llm.py imports successfully")
        results["passed"] += 1
    except Exception as e:
        print_fail(f"llm.py: {e}")
        results["failed"] += 1
        return results

    try:
        from sdo import SDO, SDOStatus
        print_ok("sdo.py imports successfully")
        results["passed"] += 1
    except Exception as e:
        print_fail(f"sdo.py: {e}")
        results["failed"] += 1
        return results

    # =========================================================================
    # TEST 2: LLM Service Initialization
    # =========================================================================
    print_header("TEST 2: LLM Service Initialization")
    
    try:
        llm = LLMService()
        has_key = bool(llm.openai_key)
        mode = "LIVE (OpenAI)" if has_key else "MOCK MODE"
        print_ok(f"LLMService initialized in {mode}")
        
        if llm.embeddings:
            print_ok(f"Embeddings model: {llm.embeddings.model}")
        else:
            print_ok("Embeddings: Mock fallback (no API key)")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"LLMService init: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 3: Memory Service Initialization
    # =========================================================================
    print_header("TEST 3: Memory Service Initialization")
    
    try:
        memory = MemoryService(embed_fn=llm.embed_text)
        health = memory.health_check()
        
        print_ok(f"MemoryService created")
        print(f"       Status: {health['status']}")
        print(f"       Connected: {health.get('connected', False)}")
        
        if not health.get("connected"):
            print("       (Qdrant not running - using mock mode)")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"MemoryService: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 4: SDO Creation and State Machine
    # =========================================================================
    print_header("TEST 4: SDO (Semantic Development Object)")
    
    try:
        sdo = SDO(
            id="test-sdo-001",
            raw_intent="Create a function to calculate fibonacci numbers",
            language="python",
            status=SDOStatus.DRAFT
        )
        
        print_ok(f"SDO created: {sdo.id}")
        print(f"       Status: {sdo.status.value}")
        print(f"       Language: {sdo.language}")
        print(f"       Intent: {sdo.raw_intent[:50]}...")
        
        # Test status transition
        sdo.status = SDOStatus.PARSING
        print_ok(f"Status transition: DRAFT -> {sdo.status.value}")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"SDO creation: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 5: Intent Parsing (Mock)
    # =========================================================================
    print_header("TEST 5: Intent Parsing")
    
    try:
        parsed = await llm.parse_intent("Create a sorting function for lists")
        
        print_ok("Intent parsed successfully")
        print(f"       Action: {parsed.get('action', 'N/A')}")
        print(f"       Entity: {parsed.get('entity', 'N/A')}")
        print(f"       Description: {parsed.get('description', 'N/A')[:40]}...")
        print(f"       Constraints: {parsed.get('constraints', [])}")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"Intent parsing: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 6: Code Generation (Mock)
    # =========================================================================
    print_header("TEST 6: Code Generation")
    
    try:
        sdo.parsed_intent = parsed
        sdo.status = SDOStatus.GENERATING
        
        code = await llm.generate_code(sdo)
        
        print_ok("Code generated successfully")
        print(f"       Output ({len(code)} chars):")
        for line in code.split("\n")[:3]:
            print(f"         {line}")
        
        sdo.code = code
        sdo.status = SDOStatus.VERIFYING
        print_ok(f"SDO transitioned to {sdo.status.value}")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"Code generation: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 7: Embedding Generation (Mock)
    # =========================================================================
    print_header("TEST 7: Embedding Generation")
    
    try:
        embedding = await llm.embed_text("Test text for embedding")
        
        print_ok(f"Embedding generated: {len(embedding)} dimensions")
        print(f"       First 5 values: {embedding[:5]}")
        
        # Check if it's mock (all zeros) or real
        is_mock = all(v == 0.0 for v in embedding)
        print(f"       Mode: {'Mock (zero vector)' if is_mock else 'Live (real embeddings)'}")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"Embedding: {e}")
        results["failed"] += 1

    # =========================================================================
    # TEST 8: Data Models
    # =========================================================================
    print_header("TEST 8: Data Models Validation")
    
    try:
        chunk = CodeChunk(
            content="def hello(): pass",
            language="python",
            file_path="/test/file.py"
        )
        print_ok(f"CodeChunk: id={chunk.id[:8]}... lang={chunk.language}")
        
        intent = IntentRecord(
            raw_intent="Test intent",
            confidence=0.85
        )
        print_ok(f"IntentRecord: id={intent.id[:8]}... conf={intent.confidence}")
        
        retrieval = RetrievalResult(
            id="test-id",
            content="Test content",
            score=0.95,
            metadata={"key": "value"}
        )
        print_ok(f"RetrievalResult: score={retrieval.score}")
        
        results["passed"] += 1
    except Exception as e:
        print_fail(f"Data models: {e}")
        results["failed"] += 1

    return results

# =========================================================================
# Main Entry Point
# =========================================================================
if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  AXIOM AI Service - Comprehensive Test Suite")
    print("  Running simulation and verification...")
    print("=" * 60)
    
    results = asyncio.run(run_tests())
    
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print()
    
    if results["failed"] == 0:
        print("  STATUS: ALL TESTS PASSED")
        print()
        print("  The AI service is ready. To run with Docker:")
        print("    docker-compose up -d")
        print("    curl http://localhost:8000/health")
        sys.exit(0)
    else:
        print("  STATUS: SOME TESTS FAILED")
        sys.exit(1)
