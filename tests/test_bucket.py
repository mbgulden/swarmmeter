import time

from swarmmeter.bucket import TokenBucket


def test_bucket_consume():
    bucket = TokenBucket(capacity=10, refill_rate=1, refill_interval=1.0)
    assert bucket.consume(5) is True
    assert bucket.remaining() == 5
    assert bucket.consume(6) is False
    assert bucket.remaining() == 5

def test_bucket_refill():
    bucket = TokenBucket(capacity=10, refill_rate=5, refill_interval=0.1)
    bucket.consume(10)
    assert bucket.remaining() == 0
    time.sleep(0.15)
    assert bucket.remaining() == 5

def test_bucket_wait_and_consume():
    bucket = TokenBucket(capacity=10, refill_rate=10, refill_interval=0.2)
    bucket.consume(10)
    start = time.time()
    wait_time = bucket.wait_and_consume(5)
    end = time.time()
    # It should wait at least 0.2s for the next refill
    assert wait_time >= 0
    assert (end - start) >= 0.1
