"""
Direct test: Can we write history to the database?
"""
import asyncio, json

async def test():
    from database import DatabaseService
    from sdo import SDO

    db = DatabaseService()
    await db.initialize()
    print("DB initialized")
    
    # 1. Get the most recent SDO
    import asyncpg
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id::text FROM sdos ORDER BY updated_at DESC LIMIT 1")
    
    if not row:
        print("ERROR: No SDOs found")
        return
    
    sdo_id = row['id']
    print(f"Testing with SDO: {sdo_id}")
    
    # 2. Load it
    sdo_data = await db.get_sdo(sdo_id)
    print(f"SDO loaded. Current history: {json.dumps(sdo_data.get('history', []))}")
    
    # 3. Add a test step
    sdo = SDO(**sdo_data)
    sdo.add_step("test_step", {"message": "direct test"}, 0.99, "test_model")
    print(f"After add_step, history length: {len(sdo.history)}")
    print(f"History: {json.dumps([s.model_dump() for s in sdo.history], default=str)[:500]}")
    
    # 4. Save it
    dump = sdo.model_dump()
    print(f"model_dump history type: {type(dump.get('history'))}")
    print(f"model_dump history: {json.dumps(dump.get('history', []), default=str)[:500]}")
    
    await db.save_sdo(dump)
    print("Saved successfully")
    
    # 5. Re-read it
    sdo_data2 = await db.get_sdo(sdo_id)
    print(f"After re-read, history: {json.dumps(sdo_data2.get('history', []), default=str)[:500]}")
    
    await db.close()

asyncio.run(test())
