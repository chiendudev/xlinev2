# WEEK 3 DAILY IMPLEMENTATION PLAN (Message Bus Infrastructure)

Generated: 2025-09-11  
Week Window (Roadmap Official): 2025-09-22 → 2025-09-28

IMPORTANT: Tuân thủ tuyệt đối `AI_AGENT_IMPLEMENTATION_ROADMAP.md` & `PHASE_1/DETAILED_WEEKLY_PLAN.md`.  
Scope CHÍNH THỨC Tuần 3 = Message Bus (Redis Streams + NATS JetStream) + Serialization + Routing + DLQ + Monitoring + Load/Failover + Production Config.  
Tất cả nội dung Risk / Portfolio / Analytics trong `WEEK3_IMPLEMENTATION_PLAN.md` (cũ) KHÔNG thuộc roadmap tuần 3 → đã đánh dấu Deferred, **KHÔNG triển khai** tuần này.

---

## 0. SPRINT GOAL

Xây dựng hạ tầng Message Bus phân tán sẵn sàng production:

- Dual backend: Redis Streams & NATS JetStream (pluggable factory, failover optional)
- At-least-once delivery, consumer groups, retry + DLQ
- Structured Event Envelope (versioning, correlation, headers)
- Serialization layer (JSON default, optional MsgPack; ProtoBuf-ready abstraction) + conditional compression
- Routing engine (topic mapping, filters, idempotency suppression)
- Metrics + health + observability hooks
- Load test: ≥10K msg/s target (≥3K minimal CI acceptable) p95 < 50ms
- Failover simulation & recovery < 30s
- Production config template + quality gates ≥90% coverage, mypy strict 0 errors

Success = All acceptance criteria (section 11) met & final tag `week3-complete-message-bus` created.

---

## 1. GUARDRAILS (MANDATORY DAILY)

```bash
# Quality Gates (run BEFORE any commit)
mypy xline/ --strict --disallow-any-generics --disallow-incomplete-defs
flake8 xline/ tests/ --max-complexity=10
black --check xline/ tests/
bandit -r xline/ -ll -i
pytest tests/ --cov=90 --cov-fail-under=90 -q
```

Architecture Rules:

- ❌ Không import trực tiếp giữa `enterprise/*` và `freqtrade/*`
- ✅ Giao tiếp liên domain qua event bus / adapter layer
- ✅ Handlers async + idempotent + correlation_id
- ✅ Không blocking IO trong handler (dùng async / to_thread nếu cần)
- ✅ External IO có timeout + circuit breaker

Security Rules:

- Pydantic validation cho các tham số cấu hình bus
- Không log secrets / API keys (mask pattern `[A-Z0-9]{16,}`)
- Event Envelope có `version` + `signature` placeholder (mở rộng backward compat)

Observability Hooks:

- Structured logging (structlog) + correlation_id vào mỗi log
- Metrics: publish_latency_ms, handler_exec_ms, retry_count, dlq_events_total, active_subscriptions, backend_failovers_total, in_flight_events

Rollback Strategy:

- Tag daily milestone; nếu fail chất lượng → reset về tag gần nhất ổn định

---

## 2. HIGH-LEVEL ARCHITECTURE

```text
          +------------------+
          |  Event Producers |
          +---------+--------+
                    |
                    v
        +--------------------------+
        |   EventBus Interface     | (Protocol)
        +-----------+--------------+
                    | Factory
        +-----------+--------------------------+
        |                                      |
        v                                      v
+---------------------+            +----------------------+
| RedisEventBus       |            | NATSEventBus         |
| - Streams/Groups    |            | - JetStream Stream   |
| - Pending Claim     |            | - Durable Consumer   |
| - DLQ Push          |            | - DLQ Subject        |
+----------+----------+            +-----------+----------+
           |                                   |
           v                                   v
   +---------------+                   +---------------+
   | Router        |<------------------>| Monitoring    |
   | - Topic map   |  metrics events     | - Metrics    |
   | - Filters     |-------------------> | - Alerts     |
   | - Idempotency |                     | - Health     |
   +-------+-------+                     +-------+------+
           |                                     |
           v                                     v
      +----------+                         +-----------+
      | Handlers |                         |  DLQ Proc |
      +----------+                         +-----------+
```

Serialization Flow:

```text
Domain Event -> Envelope(dataclass) -> Serializer(JSON/MsgPack) -> (Optional gzip) -> Transport Publish
                                                 ^
                                                 | versioned + headers + correlation
```

---

## 3. FILE INVENTORY (CREATE JUST-IN-TIME)

```text
xline/core/events/
  bus_interface.py        # Protocol definitions
  envelope.py             # Event envelope + helpers
  exceptions.py           # Custom exceptions (PublishError, SerializationError ...)

xline/infrastructure/messaging/
  factory.py              # Backend selection (env: XLINE_MESSAGE_BUS)
  router.py               # Routing + filtering + idempotency
  serialization.py        # Serializer registry + compression
  monitoring.py           # Metrics hooks abstraction
  dlq.py                  # DLQ processing & requeue
  utils.py                # Circuit breaker, retry util, timing

xline/infrastructure/messaging/redis/
  bus.py                  # RedisEventBus implementation
  stream_manager.py       # Group creation, pending claim

xline/infrastructure/messaging/nats/
  bus.py                  # NATSEventBus implementation

tests/unit/messaging/
tests/integration/messaging/
tests/load/messaging_performance.py
tests/failover/messaging_failover_test.py
tests/unit/messaging/test_prod_config.py
```

---

## 4. TASK MAPPING (Roadmap Alignment)

| ID  | Roadmap Task                       | Day  | Artefacts |
|-----|------------------------------------|------|-----------|
| 3.1 | Redis Streams Event Bus            | Mon  | redis/bus.py, stream_manager.py |
| 3.2 | NATS JetStream Bus                 | Tue  | nats/bus.py |
| 3.3 | Message Bus Factory                | Tue  | factory.py |
| 3.4 | Serialization & Compression        | Wed  | serialization.py |
| 3.5 | Routing Engine                     | Wed  | router.py |
| 3.6 | Dead Letter Queue                  | Thu  | dlq.py + redis adjustments |
| 3.7 | Monitoring & Metrics               | Thu  | monitoring.py |
| 3.8 | Load Testing                       | Fri  | tests/load/messaging_performance.py |
| 3.9 | Failover Testing                   | Fri  | tests/failover/... |
| 3.10| Production Config + Documentation  | Sat+Sun | production.yaml, doc section |

Deferred (Out-of-scope this week): Risk, Portfolio, Analytics (documented only for traceability).

---

## 5. COMPONENT CONTRACTS

### 5.1 Envelope
- Fields: id (uuid4), type (str), source (str), timestamp (UTC ISO / datetime), version (str default "v1"), correlation_id (uuid4 if missing), data (Dict[str, Any]), headers (Dict[str,str])
- Validation: `type` must contain at least one dot, `version` semantic pattern /^v\d+$/
- Error Modes: InvalidTypeError, SerializationError

### 5.2 EventBusInterface
- publish(Envelope) -> PublishResult(success: bool, error: Optional[str], backend_meta: Dict)
- subscribe(event_type, handler) -> subscription_id
- unsubscribe(subscription_id) -> bool
- health_check() -> bool
- close() -> None
Errors: PublishTimeout, BackendUnavailable, SerializationError

### 5.3 RedisEventBus Specific
- Streams: `xline.events.<event_type>`
- Group: `xline_consumer`
- Delivery: XADD -> XREADGROUP -> XACK
- Pending Reclaim: Claim messages > visibility_timeout

### 5.4 NATSEventBus Specific
- Stream: `XLINE_EVENTS` subjects `xline.events.*`
- Durable consumer: `xline_consumer`
- Pull batch size 50; backoff on empty fetch

### 5.5 Router
- register(event_type, handler, filter=None, idempotency_key_fn=None)
- Idempotency store: in-memory dict {key: expiry_ts}; cleanup every 1000 ops

### 5.6 Circuit Breaker (utils)
- States: CLOSED -> OPEN (after threshold failures) -> HALF_OPEN (after cooldown) -> CLOSED
- Config: failure_threshold=5, recovery_timeout=30s

### 5.7 DLQProcessor
- iterate_dlq(limit) -> async iterator of (Envelope, meta)
- requeue(filter_fn) -> count requeued
- purge(filter_fn)

---

## 6. ENVIRONMENT VARIABLES MATRIX

| Variable | Purpose | Default | Notes |
|----------|---------|---------|-------|
| REDIS_URL | Redis connection | redis://localhost:6379/0 | Required for redis backend |
| NATS_URL | NATS servers | nats://127.0.0.1:4222 | Comma-separated allowed |
| XLINE_MESSAGE_BUS | Backend selector | redis | Values: redis|nats |
| ENABLE_MSGPACK | Enable MsgPack serializer | 0 | If lib not present → ignore |
| ENABLE_FAILOVER | Allow runtime backend failover | 0 | If 1: factory attempts other backend on fatal failures |
| BUS_MAX_RETRIES | Publish retry attempts | 3 | Exponential backoff 100ms * 2^n |
| REDIS_VISIBILITY_TIMEOUT | Pending reclaim threshold (s) | 60 | Reclaim logic in stream_manager |
| DLQ_MAX_RETRIES | Max handler retry before DLQ | 5 | Shared for all backends |
| METRICS_ENABLED | Enable metrics collection | 1 | No-op if 0 |
| COMPRESS_THRESHOLD | Bytes threshold for gzip | 8192 | If > threshold compress |

---

## 7. DAILY EXECUTION BLUEPRINT

Mẫu chung mỗi ngày: Objectives → Preconditions → Steps → Prompts → Tests → Validation → Acceptance → Tag → Rollback.

### DAY 1 – MON (Sep 22) – Task 3.1 Redis Streams Event Bus

Objectives:

- Core RedisEventBus (publish, subscribe, consumer loop, retry, DLQ push stub)
- Circuit breaker + metrics hooks placeholder

Preconditions:

- Confirm `redis` lib import works; ensure no direct enterprise imports

Steps:

1. Implement `bus_interface.py`
2. Implement `envelope.py`
3. Implement `redis/bus.py` (core logic + background task)
4. Implement simple circuit breaker in `utils.py`
5. Add unit tests (fakeredis or patched client)
6. Coverage & mypy validation

Prompts (copy):

```text
Create bus_interface.py with Protocol EventBusInterface (publish, subscribe, unsubscribe, health_check, close) + PublishResult dataclass.
```
```text
Implement RedisEventBus with XADD/XREADGROUP, retry headers[retry_count], DLQ push when > DLQ_MAX_RETRIES.
```

Tests (examples):

```bash
pytest tests/unit/messaging/test_redis_bus.py -v
```

Validation:

```bash
mypy xline/core/events xline/infrastructure/messaging/redis --strict
pytest tests/unit/messaging/ --cov=xline.infrastructure.messaging.redis.bus --cov-fail-under=90
```

Acceptance:

- Publish->consume path works
- Retry increments & DLQ push after threshold (stub DLQ stream exists)
- No blocking calls; mypy strict pass

Tag: `week3-day1-initial-redis-bus`  
Rollback: revert to previous tag on consumer instability

### DAY 2 – TUE (Sep 23) – Tasks 3.2 & 3.3 NATS + Factory

Objectives:

- NATSEventBus (JetStream) + factory backend selection

Steps:

1. Implement `nats/bus.py`
2. Ensure stream creation idempotent
3. Implement pull consume loop with backoff
4. Implement `factory.py` (singleton + async init guard)
5. Add tests (mock nats if server absent, mark xfail integration)

Prompts:

```text
Implement NATSEventBus with js.publish()/pull_subscribe durable consumer; mimic retry → DLQ.
```
```text
Implement factory.get_message_bus() reading XLINE_MESSAGE_BUS and caching instance.
```

Tests:

```bash
pytest tests/unit/messaging/test_factory.py -v
pytest tests/unit/messaging/test_nats_bus.py -v
```

Validation:

```bash
mypy xline/infrastructure/messaging/nats xline/infrastructure/messaging/factory.py --strict
```

Acceptance:

- Backend switch by env var
- Graceful skip if NATS unavailable (xfail)

Tag: `week3-day2-nats-factory`

### DAY 3 – WED (Sep 24) – Tasks 3.4 & 3.5 Serialization + Routing

Objectives:

- Serializer registry + optional compression
- Router with filters + idempotency

Steps:

1. Implement `serialization.py` (JsonSerializer, optional MsgPackSerializer)
2. Add compression path if size > COMPRESS_THRESHOLD
3. Implement `router.py` (register/unregister/route)
4. Refactor buses to call router for dispatch
5. Tests for serialization (round-trip), compression, filters, idempotency suppression

Prompts:

```text
serialization.py: Serializer interface dumps/loads; default JSON using orjson if present else stdlib json.
```
```text
router.py: Router.register(event_type,..) returns subscription_id; route(envelope) returns list[Awaitable]; add in-memory idempotency store.
```

Tests:

```bash
pytest tests/unit/messaging/test_serialization.py -v
pytest tests/unit/messaging/test_router.py -v
```

Acceptance:

- JSON path stable; MsgPack optional
- Duplicate envelope id suppressed if same idempotency key within TTL

Tag: `week3-day3-serialization-routing`

### DAY 4 – THU (Sep 25) – Tasks 3.6 & 3.7 DLQ + Monitoring

Objectives:

- DLQ processing + metrics + health

Steps:

1. Implement `dlq.py` (iterate, requeue, purge, stats)
2. Implement `monitoring.py` (no-op fallback if metrics disabled)
3. Integrate metrics in publish/handler timing
4. Implement bus `health_check()` logic (loop heartbeat)
5. Tests for DLQ requeue + metrics increments

Prompts:

```text
dlq.py: DLQProcessor with async requeue(filter_fn) returning count; events stored with reason & retry_count metadata.
```

Tests:

```bash
pytest tests/unit/messaging/test_dlq.py -v
pytest tests/unit/messaging/test_monitoring.py -v
```

Acceptance:

- DLQ requeue returns event to main stream
- Metrics counters/histograms updated

Tag: `week3-day4-dlq-monitoring`

### DAY 5 – FRI (Sep 26) – Tasks 3.8 & 3.9 Load + Failover

Objectives:

- Performance & failover validation

Steps:

1. Implement load test generator (batched async publishes)
2. Record latency percentiles (p50/p95)
3. Simulate Redis outage (close connection) expect retries -> optional failover if ENABLE_FAILOVER=1
4. Validate message integrity counts

Tests:

```bash
pytest tests/load/messaging_performance.py -v
pytest tests/failover/messaging_failover_test.py -v
```

Acceptance:

- Throughput >= target minimal 3K msg/s (log actual, aim 10K)
- p95 latency < 50ms (log actual)
- Failover engaged (if flag) or clean degradation

Tag: `week3-day5-performance-failover`

### DAY 6 – SAT (Sep 27) – Task 3.10 Production Config (Part 1)

Objectives:

- Production YAML + schema test + security sanity

Steps:

1. Create `infrastructure/messaging/production.yaml`
2. Include sections: redis, nats, dlq, metrics, tuning, failover
3. Add test validating required keys present
4. Manual review for secrets absence

Acceptance:

- YAML loads; all required keys validated

Tag: `week3-day6-production-config`

### DAY 7 – SUN (Sep 28) – Task 3.10 Documentation & Final Validation

Objectives:

- Consolidated docs + completion report + final quality gate

Steps:

1. Append Week 3 results to `WEEK3_COMPLETION_REPORT.md`
2. Add OPERATIONS QUICK GUIDE section (restart, DLQ drain, health probe commands)
3. Full test + coverage + type check + security scan
4. Tag release `week3-complete-message-bus`

Validation:

```bash
pytest -q --cov=xline --cov-report=term-missing
mypy xline/ --strict
flake8 xline/ tests/
bandit -r xline/ -ll -i
```

Acceptance:

- All checklist items ticked
- Coverage ≥ 90%; zero critical security issues

Tag: `week3-complete-message-bus`

---

## 8. TEST STRATEGY

Unit: envelope, serialization, router, circuit breaker, redis bus logic, nats bus logic, dlq, monitoring.  
Integration: publish→consume end-to-end for each backend.  
Load: high-volume synthetic events (randomized event types).  
Failover: force backend exception -> factory switch (if enabled).  
Idempotency: replay same envelope id + key -> suppressed count.

Edge Cases:

- Payload > threshold compress/decompress round-trip
- Handler timeout -> retry
- Redis pending claim after simulated crash
- NATS stream absent (auto-create)
- Corrupted envelope (trigger SerializationError)

---

## 9. METRICS

- events_published_total
- events_consumed_total
- publish_latency_ms (histogram)
- handler_exec_ms (histogram)
- retry_attempts_total
- dlq_events_total
- active_subscriptions
- backend_failovers_total
- compression_ratio (optional)

---

## 10. QUALITY GATES

Fail Build If:

- Coverage < 90%
- Any mypy error
- Any bandit HIGH
- Latency p95 test regression > 20% vs previous day (warn -> manual review)

---

## 11. WEEK ACCEPTANCE CRITERIA

- Redis + NATS backends functional (or graceful degrade if NATS not available locally)
- Retry + DLQ + requeue implemented & tested
- Router filtering + idempotency working
- Serialization + compression validated
- Metrics + health_check available
- Load & failover tests executed with recorded metrics
- Production config delivered & validated
- All guardrails green

---

## 12. FINAL CHECKLIST

- [ ] RedisEventBus stable
- [ ] NATSEventBus stable / gracefully degraded
- [ ] Factory backend selection
- [ ] Serialization & compression
- [ ] Router functional
- [ ] DLQ & requeue path
- [ ] Metrics recording
- [ ] Load test executed (log throughput)
- [ ] Failover test executed
- [ ] Production config validated
- [ ] Coverage ≥ 90%
- [ ] Mypy strict 0 errors
- [ ] Security scan 0 HIGH issues
- [ ] Completion report updated

---

## 13. DAILY QUICK PROMPTS

Day1: "Implement RedisEventBus (publish/subscribe, retry→DLQ stub, circuit breaker util, tests for publish/consume/retry)."

Day2: "Add NATSEventBus + factory; durable pull consumer; env-based selection; tests with mock nats."

Day3: "Add serialization registry + compression + router (filters + idempotency) + unit tests."

Day4: "Implement DLQ processor + monitoring metrics + health_check + tests for requeue & metrics."

Day5: "Implement load & failover tests (throughput, p95 latency, redis failure → optional failover)."

Day6: "Add production messaging config YAML + schema validation test (no secrets)."

Day7: "Finalize docs, operations guide, full quality gates, tag week3-complete-message-bus."

---

## 14. NOTES

- Không mở rộng scope sang Risk/Portfolio/Analytics tuần này
- Ưu tiên correctness trước tối ưu hóa
- Deterministic tests (seed RNG, freeze time if needed)
- Keep patches minimal; no unrelated refactors

---

# END OF WEEK 3 PLAN

### DAY 2 – TUE (Sep 23) – Tasks 3.2 & 3.3 NATS + Factory

Objectives:

- Implement JetStream-backed NATSEventBus (durable consumer, subject naming: `xline.events.<event_type>`).
- Implement `factory.py` returning RedisEventBus or NATSEventBus via env var `XLINE_MESSAGE_BUS` (values: redis|nats, default redis).

Preconditions:

- Day 1 RedisEventBus stable.
- Add dependency `nats-py` (already in roadmap list).

Implementation Steps:

1. Create `xline/infrastructure/messaging/nats/bus.py`.
2. JetStream setup: create stream `XLINE_EVENTS` subjects = `xline.events.*`.
3. Durable consumer naming: `xline_consumer`.
4. Methods mirror RedisEventBus signature.
5. Backpressure: pull-based consume with batch size 50.
6. Implement exponential backoff for publish failure.
7. Create `factory.py` with lazy singleton pattern.
8. Add unit tests: factory selects correct backend, publish/subscribe works (mock nats).

Prompts:

```text
Implement NATSEventBus with:
- connect(): await nats.connect(url); js = nc.jetstream()
- ensure stream existence (js.add_stream)
- publish(): js.publish(subject, bytes)
- subscribe(): create pull subscription js.pull_subscribe(subject, durable=group)
- consumer loop: sub.fetch(batch=50, timeout=1) then ack()
- Retry & DLQ semantics mimic Redis (DLQ subject: xline.dlq)
```

```text
factory.py:
get_message_bus(): reads env var XLINE_MESSAGE_BUS; caches instance; ensures connect() called once (async init guard). Provide close_message_bus() to close backend.
```

Tests:

```bash
pytest tests/unit/messaging/test_factory.py -v
pytest tests/unit/messaging/test_nats_bus.py -v
```

Validation:

```bash
mypy xline/infrastructure/messaging/nats xline/infrastructure/messaging/factory.py --strict
```

Acceptance:

- Swappable backend by env.
- NATS path functional or gracefully skipped if server unreachable in test (mark xfail).

Tag: `week3-day2-nats-factory`

### DAY 3 – WED (Sep 24) – Tasks 3.4 & 3.5 Serialization + Routing

Objectives:

- Abstraction for serializers (JSON default, MessagePack optional flag `ENABLE_MSGPACK=1`).
- Router with topic registry + predicate filters and subscription metadata.

Steps:

1. `serialization.py`: SerializerRegistry (register, get). Default JSON implementation with dataclass→dict conversion. Optional msgpack (if installed) fallback to JSON.
2. Compression: if payload size > 8KB → gzip compress (header `compressed=true`).
3. `router.py`: maintain mapping event_type -> list[RouteEntry]. Each RouteEntry: handler, filter: Optional[Callable[[Envelope], bool]], idempotency_key_fn.
4. Integrate router into existing buses (refactor to delegate handler iteration to router.route(envelope)).
5. Tests for: registry, compression threshold, filter predicate, idempotent skip (simulate duplicate id via in-memory set TTL).

Prompts:
```
serialization.py: implement interface Serializer with methods dumps(envelope: Envelope)->bytes, loads(b:bytes)->Envelope. Implement JsonSerializer. Optional MsgPackSerializer guarded by ImportError.
```
```
router.py: class Router with register(event_type, handler, filter=None, idempotency_key_fn=None) -> subscription_id; unregister(subscription_id); route(envelope) -> list[Awaitable]. Provide in-memory idempotency registry (dict with timestamp cleanup every 1000 ops).
```
Tests:
```bash
pytest tests/unit/messaging/test_serialization.py -v
pytest tests/unit/messaging/test_router.py -v
```
Acceptance:
- JSON path stable; msgpack optional.
- Filters working; duplicates suppressed.
Tag: `week3-day3-serialization-routing`

### DAY 4 – THU (Sep 25) – Tasks 3.6 & 3.7 DLQ + Monitoring
Objectives:
- Implement DLQ consumer + reprocessing logic.
- Expose metrics & health endpoints skeleton (no full HTTP server—just collector objects).

Steps:
1. `dlq.py`: DLQProcessor with methods: start(), requeue(criteria), purge(), stats(). Processes stream/subject `xline.dlq`.
2. Add structured error record: {original_subject/stream, reason, retry_count, first_seen, last_seen}.
3. `monitoring.py`: metrics registry using simple counters/histograms (wrap prometheus_client if installed else no-op). Expose functions record_publish_latency(ms), inc_dlq(), etc.
4. Integrate metrics hooks into Redis/NATS bus.
5. Add health_check: returns True only if last publish < 60s and consumer loop alive.
6. Tests: simulate DLQ insertion, reprocess path, metric increments.

Prompts:
```
dlq.py: class DLQProcessor(event_bus, backend_type) supporting async iterate_dlq(limit: int) -> AsyncIterator[Envelope+meta]; method requeue(filter_fn) pushing back to main bus.
```
Tests:
```bash
pytest tests/unit/messaging/test_dlq.py -v
pytest tests/unit/messaging/test_monitoring.py -v
```
Acceptance:
- DLQ count increments.
- Requeue returns event to main stream.
Tag: `week3-day4-dlq-monitoring`

### DAY 5 – FRI (Sep 26) – Tasks 3.8 & 3.9 Load + Failover Testing
Objectives:
- Performance harness & failover scenarios.

Steps:
1. `tests/load/messaging_performance.py`: generate 50K envelopes (batched) measure throughput & latency distribution.
2. `tests/failover/messaging_failover_test.py`: simulate Redis outage (close connection mid-run) expect automatic retry/backoff; switch environment to NATS (factory) on persistent failure (simulate by raising ConnectionError after threshold) verifying continuity.
3. Add simple benchmark script `scripts/bench_message_bus.py` (OPTIONAL if scripts dir allowed; else keep inside test harness only—Respect "no extra files" → embed benchmark in test). => Skip adding new script to avoid clutter.
4. Collect metrics summary -> print JSON at end.

Performance Targets (assert or mark xfail with warning):
- >= 10,000 messages/second (aggregate) (allow local variability—log actual, assert >3,000 minimum to not block CI).
- p95 latency < 50ms.

Tests Commands:
```bash
pytest tests/load/messaging_performance.py -v
pytest tests/failover/messaging_failover_test.py -v
```
Acceptance:
- Failover path triggers factory fallback (flag `ENABLE_FAILOVER=1`).
Tag: `week3-day5-performance-failover`

### DAY 6 – SAT (Sep 27) – Task 3.10 Production Configuration (Part 1)
Objectives:
- Provide production-ready configuration templates (YAML or env doc) w/out adding excess code.

Steps:
1. Create `infrastructure/messaging/production.yaml` with sections: redis (urls, consumer_concurrency, retry), nats (servers, jetstream: retention limits), dlq policy, metrics export toggles.
2. Document env var matrix in section inside this file (no separate doc file to avoid spam).
3. Add test validating schema of yaml (load & basic required keys) in `tests/unit/messaging/test_prod_config.py`.
4. Security review: ensure no sample secrets.

Acceptance:
- YAML loads, required keys present.
Tag: `week3-day6-production-config`

### DAY 7 – SUN (Sep 28) – Task 3.10 Documentation & Final Validation
Objectives:
- Consolidate docs + final quality gate + weekly report stub.

Steps:
1. Append Week 3 section into existing `WEEK3_COMPLETION_REPORT.md` (if exists) else create inside root roadmap folder? (REUSE existing `WEEK3_COMPLETION_REPORT.md` in main root—NO duplicate). Include metrics (throughput, p95, coverage, failover result).
2. Create internal doc block inside this SAME file (avoid new file): "OPERATIONS QUICK GUIDE" describing restart, DLQ drain, health probe.
3. Run full test + coverage + type check.
4. Tag release: `week3-complete-message-bus`.

Validation Commands:
```bash
pytest -q --cov=xline --cov-report=term-missing
mypy xline/ --strict
flake8 xline/ tests/
```
Success Checklist:
- [ ] All tasks 3.1–3.10 done
- [ ] p95 latency < 50ms (record actual)
- [ ] Failover test passed
- [ ] DLQ requeue works
- [ ] Coverage ≥ 90%
- [ ] No architecture violations (AST scan optional)

Rollback:
- If final failover not stable → revert to tag `week3-day4-dlq-monitoring` and create issue ticket.

---
## 6. TEST STRATEGY SUMMARY
Unit: Serialization, router, circuit breaker, retry, dlq, metrics.  
Integration: End-to-end publish→consume (Redis & NATS).  
Load: Synthetic high-volume benchmark with timing capture.  
Failover: Transport disruption simulation + automatic factory fallback.

Edge Cases:
- Large payload (>8KB) compression toggle.
- Handler timeout (simulate sleep > timeout) → retry path.
- Duplicate event id (idempotency suppression).
- Redis pending messages claim after consumer restart.
- NATS stream missing (auto-create). 

---
## 7. METRICS TO CAPTURE (LOG OR METRICS REGISTRY)
- events_published_total
- events_consumed_total
- publish_latency_ms (histogram)
- handler_exec_ms (histogram)
- retry_attempts_total
- dlq_events_total
- active_subscriptions
- backend_failovers_total

---
## 8. QUALITY GATES (AUTOMATED)
Failure Conditions (STOP & FIX IMMEDIATELY):
- Coverage < 90%
- Any mypy error
- Any bandit HIGH severity
- Event handler synchronous blocking detected (use lint rule or manual review)

---
## 9. DEFERRED ITEMS (From WEEK3_IMPLEMENTATION_PLAN.md)
These belong to later roadmap weeks (Risk / Portfolio / Analytics). Only perform architecture compatibility notes if absolutely required.
- Risk Manager (Week 8)
- Portfolio Optimizer (Week 8+)
- Analytics Engine (Week 5/4 Observability + later extension)
Action This Week: NONE (avoid scope creep). Documented here for traceability.

---
## 10. DAILY COPY-PASTE MINI PROMPTS
Use đúng ngày, không chạy trước để tránh drift.

Day1 Quick Prompt:
"Implement RedisEventBus per spec: at-least-once, retries→DLQ, circuit breaker, async consumer loop, tests for publish/consume/retry/correlation id. Maintain type hints + mypy strict."

Day2 Quick Prompt:
"Add NATSEventBus (JetStream) + factory selection. Durable consumer, pull batch, retry semantics mimic Redis, unit tests mock nats." 

Day3 Quick Prompt:
"Add serialization registry (JSON default, optional msgpack) + compression >8KB + router with filters & idempotency suppression + tests." 

Day4 Quick Prompt:
"Implement DLQ processor + monitoring metrics hooks + health check integration + tests for dlq requeue + metrics increments." 

Day5 Quick Prompt:
"Create load & failover tests: measure throughput, p95 latency, simulate Redis failure and fallback to NATS via factory. Ensure assertions + performance logging." 

Day6 Quick Prompt:
"Add production.yaml for messaging config (redis, nats, dlq, metrics). Write schema validation test. No secrets." 

Day7 Quick Prompt:
"Finalize docs & completion report section; run full quality gates; tag release `week3-complete-message-bus`." 

---
## 11. ACCEPTANCE CRITERIA (WEEK SUMMARY)
- Dual backend operational (Redis + NATS) with transparent factory.
- Robust retry + DLQ + requeue.
- Routing + filtering + idempotency.
- Metrics & basic health signals.
- Performance & failover validated.
- Production config delivered.
- All guardrails passed.

---
## 12. FINAL CHECKLIST (TICK BEFORE TAG)
- [ ] RedisEventBus stable
- [ ] NATSEventBus stable / or gracefully degraded
- [ ] Factory selection via env
- [ ] Serialization & compression done
- [ ] Router functional
- [ ] DLQ & requeue path tested
- [ ] Monitoring counters/histograms update
- [ ] Load test executed, results logged
- [ ] Failover test executed
- [ ] Production config validated
- [ ] Coverage ≥ 90%
- [ ] Mypy strict 0 errors
- [ ] Security scan 0 high issues
- [ ] Documentation updated

---
## 13. NOTES
- Nếu thiếu Redis/NATS service trong local: tests nên mock / mark xfail integration gracefully.
- Ưu tiên deterministic tests (seed random, fixed time provider if needed).
- Đừng tối ưu Premature. Tập trung correctness + resilience.

---
# END OF WEEK 3 PLAN
