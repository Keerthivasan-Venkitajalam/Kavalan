"""
Property-based test for chain-of-custody tracking

Feature: production-ready-browser-extension
Property 19: Chain-of-Custody Metadata

For any evidence item in a Digital FIR, chain-of-custody metadata should track
all access and modifications with timestamps and actor identities.

Validates: Requirements 12.6
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from datetime import datetime
from app.db.mongodb import MongoDB


# Fixtures
@pytest.fixture
async def mongodb():
    """Create MongoDB client for testing"""
    db = MongoDB()
    await db.connect()
    yield db
    await db.disconnect()


# Custom strategies
@st.composite
def fir_data(draw):
    """Generate FIR test data with unique FIR ID"""
    unique_id = str(uuid4())[:8]
    return {
        "fir_id": f"FIR-{unique_id}-{draw(st.text(min_size=8, max_size=8, alphabet='0123456789abcdef'))}",
        "session_id": str(uuid4()),
        "user_id": str(uuid4()),
        "summary": {"max_threat_score": draw(st.floats(min_value=7.0, max_value=10.0))},
        "evidence": {"transcripts": [], "frames": []},
        "legal": {"chain_of_custody": []}
    }


@st.composite
def actor_name(draw):
    """Generate actor name"""
    actor_types = ["user", "system", "admin", "service"]
    actor_type = draw(st.sampled_from(actor_types))
    actor_id = draw(st.text(min_size=4, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'))
    return f"{actor_type}_{actor_id}"


@st.composite
def action_name(draw):
    """Generate action name"""
    actions = ["FIR_ACCESSED", "FIR_MODIFIED", "FIR_EXPORTED", "FIR_DELETED"]
    return draw(st.sampled_from(actions))


# Property Tests
@pytest.mark.asyncio
@given(
    fir=fir_data(),
    actor=actor_name(),
    action=action_name()
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=5000
)
async def test_chain_of_custody_tracks_access(mongodb, fir, actor, action):
    """
    Property: For any FIR access or modification, chain-of-custody should record
    the action with timestamp and actor identity.
    
    This test verifies that:
    1. Chain-of-custody entries are created for all operations
    2. Each entry contains action, timestamp, and actor
    3. Timestamps are in chronological order
    """
    # Create FIR
    await mongodb.create_digital_fir(
        fir_id=fir["fir_id"],
        session_id=UUID(fir["session_id"]),
        user_id=UUID(fir["user_id"]),
        summary=fir["summary"],
        evidence=fir["evidence"],
        legal=fir["legal"]
    )
    
    # Record action in chain-of-custody
    before_action = datetime.utcnow()
    success = await mongodb.append_chain_of_custody(
        fir_id=fir["fir_id"],
        action=action,
        actor=actor
    )
    after_action = datetime.utcnow()
    
    assert success, "Chain-of-custody entry should be appended successfully"
    
    # Retrieve FIR and verify chain-of-custody
    retrieved_fir = await mongodb.get_digital_fir(fir["fir_id"], track_access=False)
    assert retrieved_fir is not None, "FIR should exist"
    
    chain = retrieved_fir["legal"]["chain_of_custody"]
    assert len(chain) > 0, "Chain-of-custody should have at least one entry"
    
    # Find the entry we just added
    last_entry = chain[-1]
    
    # Verify required fields exist (Req 12.6)
    assert "action" in last_entry, "Chain-of-custody entry must have action"
    assert "timestamp" in last_entry, "Chain-of-custody entry must have timestamp"
    assert "actor" in last_entry, "Chain-of-custody entry must have actor identity"
    
    # Verify values
    assert last_entry["action"] == action, "Action should match"
    assert last_entry["actor"] == actor, "Actor should match"
    
    # Verify timestamp is within reasonable range (allow 1 second tolerance)
    entry_timestamp = last_entry["timestamp"]
    # Convert to timestamps for comparison (handles microsecond precision issues)
    before_ts = before_action.timestamp()
    after_ts = after_action.timestamp()
    entry_ts = entry_timestamp.timestamp()
    
    assert before_ts - 1 <= entry_ts <= after_ts + 1, \
        f"Timestamp should be within reasonable range: {before_action} <= {entry_timestamp} <= {after_action}"
    
    # Cleanup
    await mongodb.delete_digital_fir(fir["fir_id"])


@pytest.mark.asyncio
@given(
    fir=fir_data(),
    actors=st.lists(actor_name(), min_size=2, max_size=5),
    actions=st.lists(action_name(), min_size=2, max_size=5)
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=5000
)
async def test_chain_of_custody_chronological_order(mongodb, fir, actors, actions):
    """
    Property: For any sequence of FIR operations, chain-of-custody entries
    should be in chronological order.
    
    This test verifies that:
    1. Multiple operations are tracked in order
    2. Timestamps are monotonically increasing
    3. All operations are preserved
    """
    # Create FIR
    await mongodb.create_digital_fir(
        fir_id=fir["fir_id"],
        session_id=UUID(fir["session_id"]),
        user_id=UUID(fir["user_id"]),
        summary=fir["summary"],
        evidence=fir["evidence"],
        legal=fir["legal"]
    )
    
    # Perform multiple operations
    num_operations = min(len(actors), len(actions))
    for i in range(num_operations):
        await mongodb.append_chain_of_custody(
            fir_id=fir["fir_id"],
            action=actions[i],
            actor=actors[i]
        )
    
    # Retrieve FIR and verify chain-of-custody
    retrieved_fir = await mongodb.get_digital_fir(fir["fir_id"], track_access=False)
    chain = retrieved_fir["legal"]["chain_of_custody"]
    
    # Verify all operations were recorded
    assert len(chain) >= num_operations, \
        f"Chain should have at least {num_operations} entries"
    
    # Verify chronological order
    for i in range(1, len(chain)):
        prev_timestamp = chain[i-1]["timestamp"]
        curr_timestamp = chain[i]["timestamp"]
        assert prev_timestamp <= curr_timestamp, \
            "Chain-of-custody timestamps must be in chronological order"
    
    # Cleanup
    await mongodb.delete_digital_fir(fir["fir_id"])


@pytest.mark.asyncio
@given(
    fir=fir_data(),
    actor=actor_name()
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=5000
)
async def test_chain_of_custody_tracks_read_access(mongodb, fir, actor):
    """
    Property: For any FIR read operation with an actor, chain-of-custody
    should automatically track the access.
    
    This test verifies that:
    1. Read operations are tracked when actor is provided
    2. FIR_ACCESSED action is recorded
    3. Actor identity is preserved
    """
    # Create FIR
    await mongodb.create_digital_fir(
        fir_id=fir["fir_id"],
        session_id=UUID(fir["session_id"]),
        user_id=UUID(fir["user_id"]),
        summary=fir["summary"],
        evidence=fir["evidence"],
        legal=fir["legal"]
    )
    
    # Access FIR with actor tracking
    retrieved_fir = await mongodb.get_digital_fir(
        fir["fir_id"],
        actor=actor,
        track_access=True
    )
    
    assert retrieved_fir is not None, "FIR should be retrieved"
    
    # Fetch again to get the updated chain-of-custody
    # (the first call returns the document before updating the chain)
    updated_fir = await mongodb.get_digital_fir(fir["fir_id"], track_access=False)
    chain = updated_fir["legal"]["chain_of_custody"]
    
    # Should have at least one entry (the access we just performed)
    assert len(chain) > 0, "Chain should have access entry"
    
    # Find FIR_ACCESSED entry
    access_entries = [e for e in chain if e["action"] == "FIR_ACCESSED"]
    assert len(access_entries) > 0, "Should have at least one FIR_ACCESSED entry"
    
    # Verify the most recent access entry
    last_access = access_entries[-1]
    assert last_access["actor"] == actor, "Actor should match"
    assert "timestamp" in last_access, "Access should have timestamp"
    
    # Cleanup
    await mongodb.delete_digital_fir(fir["fir_id"])


@pytest.mark.asyncio
@given(
    fir=fir_data(),
    actor=actor_name(),
    details=st.text(min_size=10, max_size=100)
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=5000
)
async def test_chain_of_custody_tracks_modifications_with_details(mongodb, fir, actor, details):
    """
    Property: For any FIR modification, chain-of-custody should track
    the modification with optional details about what was changed.
    
    This test verifies that:
    1. Modifications are tracked with FIR_MODIFIED action
    2. Optional details field is preserved
    3. Actor and timestamp are recorded
    """
    # Create FIR
    await mongodb.create_digital_fir(
        fir_id=fir["fir_id"],
        session_id=UUID(fir["session_id"]),
        user_id=UUID(fir["user_id"]),
        summary=fir["summary"],
        evidence=fir["evidence"],
        legal=fir["legal"]
    )
    
    # Modify FIR with actor tracking
    updated = await mongodb.update_digital_fir(
        fir_id=fir["fir_id"],
        summary={"max_threat_score": 9.5, "alert_count": 3},
        actor=actor
    )
    
    assert updated, "FIR should be updated"
    
    # Retrieve and verify chain-of-custody
    retrieved_fir = await mongodb.get_digital_fir(fir["fir_id"], track_access=False)
    chain = retrieved_fir["legal"]["chain_of_custody"]
    
    # Find FIR_MODIFIED entry
    modified_entries = [e for e in chain if e["action"] == "FIR_MODIFIED"]
    assert len(modified_entries) > 0, "Should have FIR_MODIFIED entry"
    
    # Verify the modification entry
    last_modified = modified_entries[-1]
    assert last_modified["actor"] == actor, "Actor should match"
    assert "timestamp" in last_modified, "Modification should have timestamp"
    assert "details" in last_modified, "Modification should have details"
    assert "summary" in last_modified["details"], "Details should mention modified section"
    
    # Cleanup
    await mongodb.delete_digital_fir(fir["fir_id"])


@pytest.mark.asyncio
@given(
    fir=fir_data()
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=5000
)
async def test_chain_of_custody_no_tracking_without_actor(mongodb, fir):
    """
    Property: For any FIR read operation without an actor, chain-of-custody
    should not be updated (track_access=False or no actor).
    
    This test verifies that:
    1. Operations without actor don't create chain entries
    2. track_access flag is respected
    """
    # Create FIR
    await mongodb.create_digital_fir(
        fir_id=fir["fir_id"],
        session_id=UUID(fir["session_id"]),
        user_id=UUID(fir["user_id"]),
        summary=fir["summary"],
        evidence=fir["evidence"],
        legal=fir["legal"]
    )
    
    # Get initial chain length
    initial_fir = await mongodb.get_digital_fir(fir["fir_id"], track_access=False)
    initial_chain_length = len(initial_fir["legal"]["chain_of_custody"])
    
    # Access FIR without tracking
    retrieved_fir = await mongodb.get_digital_fir(
        fir["fir_id"],
        actor=None,
        track_access=True
    )
    
    assert retrieved_fir is not None, "FIR should be retrieved"
    
    # Verify chain-of-custody was NOT updated
    final_chain_length = len(retrieved_fir["legal"]["chain_of_custody"])
    assert final_chain_length == initial_chain_length, \
        "Chain should not grow when actor is None"
    
    # Access with track_access=False
    retrieved_fir2 = await mongodb.get_digital_fir(
        fir["fir_id"],
        actor="some_actor",
        track_access=False
    )
    
    # Verify chain still hasn't grown
    final_chain_length2 = len(retrieved_fir2["legal"]["chain_of_custody"])
    assert final_chain_length2 == initial_chain_length, \
        "Chain should not grow when track_access=False"
    
    # Cleanup
    await mongodb.delete_digital_fir(fir["fir_id"])
