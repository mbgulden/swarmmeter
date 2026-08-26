import time
from swarmmeter.anomaly import AnomalyDetector
from swarmmeter.types import QuotaPolicy, TokenUsage

def test_anomaly_detection_token_limit():
    policy = QuotaPolicy(per_minute_token_limit=100)
    detector = AnomalyDetector(policy)
    
    usage = TokenUsage(
        agent_id="agent1",
        tokens_in=60,
        tokens_out=50,
        cost_usd=0.01,
        timestamp=time.monotonic(),
        model="test",
        provider="test"
    )
    
    detector.record(usage)
    assert detector.is_anomalous("agent1") is True
    assert "exceeds limit" in detector.check("agent1")[0]

def test_anomaly_detection_cost_limit():
    policy = QuotaPolicy(per_minute_cost_limit_usd=1.0)
    detector = AnomalyDetector(policy)
    
    usage = TokenUsage(
        agent_id="agent2",
        tokens_in=10,
        tokens_out=10,
        cost_usd=1.5,
        timestamp=time.monotonic(),
        model="test",
        provider="test"
    )
    
    detector.record(usage)
    assert detector.is_anomalous("agent2") is True
    assert "exceeds limit" in detector.check("agent2")[0]

def test_anomaly_cleanup():
    policy = QuotaPolicy(per_minute_token_limit=100)
    detector = AnomalyDetector(policy)
    detector._window_size = 0.1 # short window for testing
    
    usage = TokenUsage(
        agent_id="agent3",
        tokens_in=150,
        tokens_out=0,
        cost_usd=0.0,
        timestamp=time.monotonic(),
        model="test",
        provider="test"
    )
    detector.record(usage)
    assert detector.is_anomalous("agent3") is True
    
    time.sleep(0.2)
    assert detector.is_anomalous("agent3") is False
