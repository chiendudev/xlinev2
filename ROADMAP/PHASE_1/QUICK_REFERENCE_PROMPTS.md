# QUICK REFERENCE: AI AGENT PROMPTS FOR WEEK 1
## 🚀 Copy-paste ready prompts cho từng ngày

---

## 📅 **DAY 1 (Sept 9) - PROJECT FOUNDATION**

```markdown
# 🚀 WEEK 1 DAY 1: PROJECT FOUNDATION IMPLEMENTATION

## 🎯 MISSION CRITICAL:
Today is September 9, 2025. Implement complete development environment setup với Event Bus core interface theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 1.

## 📁 REQUIRED CONTEXT DOCUMENTS:
- `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/WEEK1_DAILY_AI_AGENT_PROMPTS.md` - Day 1 requirements
- `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/WEEK1_IMPLEMENTATION_TEMPLATES.md` - Code templates
- `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md` - Project structure

## 🚀 TODAY'S DELIVERABLES:
1. **Project Structure**: Create 16 directories exactly theo DETAILED_WEEKLY_PLAN.md
2. **pyproject.toml**: Setup với all 20+ required dependencies
3. **EventBusInterface**: File `xline/core/events/bus.py` - Protocol implementation
4. **Development Environment**: Pre-commit hooks, git setup, virtual environment
5. **Basic Tests**: File `tests/core/events/test_bus.py` với 95%+ coverage

## 🔒 MANDATORY VALIDATION (ALL MUST PASS):
```bash
python -c "import xline.core.events.bus; print('✅ Import successful')"
python -m pytest tests/core/events/ --cov=95
mypy xline/core/events/ --strict  
black --check xline/ tests/
flake8 xline/ tests/ --max-complexity=10
./scripts/validate_week1_daily.sh 1
```

## ⚠️ CRITICAL SUCCESS CRITERIA:
- EventBusInterface MUST be Protocol với proper type hints
- All imports MUST work without errors
- Test coverage MUST be ≥95%
- Project structure MUST match specification exactly
- ALL validation commands MUST pass

## 🚨 ZERO TOLERANCE POLICY:
If ANY validation command fails, STOP immediately, fix the issue, and re-run validation. Only proceed when ALL commands pass green.
```

---

## 📅 **DAY 2 (Sept 10) - REDIS STREAMS**

```markdown
# 🚀 WEEK 1 DAY 2: REDIS STREAMS IMPLEMENTATION

## 🎯 MISSION CRITICAL:
Implement production-ready Redis Event Bus với Circuit Breaker và Dead Letter Queue theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 2.

## 📁 REQUIRED CONTEXT:
- WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 2
- WEEK1_IMPLEMENTATION_TEMPLATES.md - Redis patterns
- AI_AGENT_IMPLEMENTATION_ROADMAP.md - Architecture requirements

## 🚀 TODAY'S DELIVERABLES:
1. **RedisEventBus**: File `xline/infrastructure/messaging/redis/bus.py`
2. **CircuitBreaker**: File `xline/core/reliability/circuit_breaker.py`
3. **Dead Letter Queue**: Poison message handling
4. **Connection Retry**: Exponential backoff logic
5. **Redis Tests**: File `tests/infrastructure/messaging/redis/test_redis_bus.py`

## 🔒 MANDATORY VALIDATION:
```bash
python -m pytest tests/infrastructure/messaging/redis/ --cov=95
python -c "
import asyncio
from xline.infrastructure.messaging.redis.bus import RedisEventBus
async def test(): 
    bus = RedisEventBus('redis://localhost:6379')
    result = await bus.health_check()
    print(f'✅ Redis health: {result}')
asyncio.run(test())
"
mypy xline/infrastructure/messaging/redis/ --strict
./scripts/validate_week1_daily.sh 2
```

## ⚠️ PERFORMANCE TARGETS:
- Latency: <50ms for event publishing
- Circuit breaker: Open after 3 consecutive failures
- Retry logic: Exponential backoff với max 3 attempts
- DLQ: Auto-move poison messages after max retries

## 🚨 IMPLEMENTATION REQUIREMENTS:
Use exact code patterns from WEEK1_IMPLEMENTATION_TEMPLATES.md. NO deviations allowed.
```

---

## 📅 **DAY 3 (Sept 11) - NATS ALTERNATIVE**

```markdown
# 🚀 WEEK 1 DAY 3: NATS ALTERNATIVE & FALLBACK SYSTEM

## 🎯 MISSION CRITICAL:
Implement NATS Event Bus và EventBusFactory với tiered fallback strategy theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 3.

## 📁 REQUIRED CONTEXT:
- WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 3
- WEEK1_IMPLEMENTATION_TEMPLATES.md - Factory patterns
- AI_AGENT_IMPLEMENTATION_ROADMAP.md - Fallback strategy

## 🚀 TODAY'S DELIVERABLES:
1. **NATSEventBus**: File `xline/infrastructure/messaging/nats/bus.py`
2. **EventBusFactory**: File `xline/core/events/factory.py`
3. **InMemoryEventBus**: File `xline/infrastructure/messaging/memory/bus.py`
4. **Fallback Tests**: File `tests/integration/events/test_fallback.py`
5. **Factory Tests**: File `tests/core/events/test_factory.py`

## 🔒 MANDATORY VALIDATION:
```bash
python -m pytest tests/integration/events/test_fallback.py --cov=95
python -c "
import asyncio
from xline.core.events.factory import EventBusFactory
async def test():
    factory = EventBusFactory()
    bus = await factory.create()
    print(f'✅ Factory created: {type(bus).__name__}')
asyncio.run(test())
"
./scripts/validate_week1_daily.sh 3
```

## ⚠️ FALLBACK CHAIN REQUIREMENTS:
1. **Production**: Redis Streams (primary choice)
2. **Development**: NATS JetStream (fallback)
3. **Mock**: InMemory (MUST ALWAYS WORK)

## 🚨 CRITICAL PATTERN:
```python
class EventBusFactory(TieredComponentFactory[EventBusInterface]):
    async def _create_production_implementation(self):
        # Redis implementation
    async def _create_development_implementation(self):
        # NATS implementation  
    async def _create_mock_implementation(self):
        return InMemoryEventBus()  # MUST NEVER FAIL
```
```

---

## 📅 **DAY 4 (Sept 12) - EVENT TYPES**

```markdown
# 🚀 WEEK 1 DAY 4: EVENT TYPE SYSTEM & SERIALIZATION

## 🎯 MISSION CRITICAL:
Implement complete type-safe event system với proper serialization theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 4.

## 📁 REQUIRED CONTEXT:
- WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 4
- WEEK1_IMPLEMENTATION_TEMPLATES.md - Event type patterns
- AI_AGENT_IMPLEMENTATION_ROADMAP.md - Type requirements

## 🚀 TODAY'S DELIVERABLES:
1. **Base Event**: File `xline/core/events/types.py`
2. **OrderEvent**: Trading order events
3. **TradeEvent**: Trade execution events
4. **RiskEvent**: Risk management events
5. **AccountEvent**: Account management events
6. **SystemEvent**: System-level events
7. **Serializers**: File `xline/core/events/serializers.py`

## 🔒 MANDATORY VALIDATION:
```bash
python -m pytest tests/core/events/test_types.py --cov=100
mypy xline/core/events/types.py --strict --disallow-any-generics
python -c "
from xline.core.events.types import OrderEvent
from decimal import Decimal
event = OrderEvent(
    event_id='test-123',
    timestamp=datetime.now(),
    order_id='order-456',
    account_id='acc-789',
    symbol='BTCUSDT',
    side='BUY',
    quantity=Decimal('1.5'),
    price=Decimal('50000.00'),
    order_type='LIMIT',
    status='NEW'
)
print(f'✅ OrderEvent created: {event.event_id}')
"
./scripts/validate_week1_daily.sh 4
```

## ⚠️ TYPE SAFETY REQUIREMENTS:
- ALL events MUST inherit from base Event class
- Use Decimal for all financial amounts (NO floats)
- 100% type hints coverage
- Pydantic validation models
- JSON serialization support

## 🚨 EXACT PATTERN REQUIRED:
```python
@dataclass
class OrderEvent(Event):
    order_id: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal  # MANDATORY: Use Decimal
    price: Decimal
    order_type: str
    status: str
```
```

---

## 📅 **DAY 5 (Sept 13) - TESTING & PERFORMANCE**

```markdown
# 🚀 WEEK 1 DAY 5: COMPREHENSIVE TESTING & PERFORMANCE

## 🎯 MISSION CRITICAL:
Complete comprehensive test suite với performance benchmarks theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 5.

## 📁 REQUIRED CONTEXT:
- WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 5
- WEEK1_IMPLEMENTATION_TEMPLATES.md - Test patterns
- WEEK1_IMPLEMENTATION_CHECKLIST.md - Performance targets

## 🚀 TODAY'S DELIVERABLES:
1. **Integration Tests**: File `tests/integration/events/test_event_bus_integration.py`
2. **Performance Tests**: File `tests/performance/test_event_bus_performance.py`
3. **Load Tests**: File `tests/load/test_event_bus_load.py`
4. **Failover Tests**: Complete failover scenarios
5. **Memory Tests**: Memory leak detection

## 🔒 MANDATORY VALIDATION:
```bash
python -m pytest tests/integration/events/ --cov=95
python -m pytest tests/performance/ --benchmark-only
python -m pytest tests/load/
./scripts/validate_week1_complete.sh
```

## ⚠️ PERFORMANCE BENCHMARKS (MUST MEET):
```python
async def test_throughput():
    # Target: ≥1000 events/second sustained
    
async def test_latency():
    # Target: <100ms (95th percentile)
    
async def test_memory_usage():
    # Target: <100MB under normal load
    
async def test_concurrent_load():
    # Target: 100+ concurrent publishers/subscribers
```

## 🚨 LOAD TESTING SCENARIOS:
- 100+ concurrent publishers
- 100+ concurrent subscribers  
- >1MB event payloads
- 1 hour sustained load
- Memory leak detection

## ✅ SUCCESS CRITERIA:
ALL performance targets met và documented in benchmark results.
```

---

## 📅 **WEEKEND (Sept 14-15) - DOCUMENTATION**

```markdown
# 🚀 WEEK 1 WEEKEND: DOCUMENTATION & FINAL VALIDATION

## 🎯 MISSION CRITICAL:
Complete all documentation và final validation theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Weekend.

## 🚀 TODAY'S DELIVERABLES:
1. **Architecture Docs**: File `docs/event-bus/architecture.md`
2. **API Documentation**: OpenAPI specs với examples
3. **Deployment Guide**: File `docs/deployment/event-bus-setup.md`
4. **Troubleshooting**: File `docs/troubleshooting/event-bus.md`
5. **Performance Report**: Benchmark results documentation

## 🔒 FINAL VALIDATION:
```bash
./scripts/validate_week1_complete.sh
python -m pytest tests/ --cov=95 --cov-fail-under=95
mypy xline/ --strict --disallow-any-generics  
black --check xline/ tests/
flake8 xline/ tests/ --max-complexity=10
bandit -r xline/ -ll -i
```

## ✅ WEEK 1 COMPLETION CRITERIA:
- [ ] All 5 daily implementations complete
- [ ] All quality gates passing consistently
- [ ] Performance targets met và documented
- [ ] Complete test suite với 95%+ coverage
- [ ] All documentation complete và accurate
- [ ] Production deployment ready
```

---

## 🔥 **EMERGENCY TROUBLESHOOTING PROMPTS**

### **🚨 IF VALIDATION FAILS:**

```markdown
## 🆘 VALIDATION FAILURE - IMMEDIATE ACTION REQUIRED

**Current Issue**: [Specific validation command that failed]

**Required Action**: 
1. STOP all development immediately
2. Analyze the specific error message
3. Fix ONLY the failing issue
4. Re-run the failed validation command
5. Ensure it passes before continuing

**Rollback Strategy**:
If unable to fix quickly, rollback to last working state:
```bash
git reset --hard HEAD~1
./scripts/validate_week1_daily.sh [current_day]
```

**Success Criteria**: ALL validation commands must pass green before proceeding.
```

### **🚨 IF PERFORMANCE TARGETS NOT MET:**

```markdown
## ⚡ PERFORMANCE FAILURE - OPTIMIZATION REQUIRED

**Current Issue**: Performance benchmark below target

**Required Analysis**:
1. Run performance profiler
2. Identify bottlenecks
3. Apply specific optimizations
4. Re-run performance tests
5. Document optimization changes

**Common Issues**:
- Blocking calls in async functions
- Missing connection pooling
- Inefficient serialization
- Memory leaks in long-running tests
```

---

## 🎯 **COPY-PASTE QUICK COMMANDS**

### **📋 Daily Validation Commands:**
```bash
# Day 1
./scripts/validate_week1_daily.sh 1

# Day 2  
./scripts/validate_week1_daily.sh 2

# Day 3
./scripts/validate_week1_daily.sh 3

# Day 4
./scripts/validate_week1_daily.sh 4

# Day 5
./scripts/validate_week1_daily.sh 5

# Final Validation
./scripts/validate_week1_complete.sh
```

### **📋 Quick Health Checks:**
```bash
# Test imports
python -c "import xline.core.events.bus; print('✅ Core events import OK')"
python -c "import xline.infrastructure.messaging.redis.bus; print('✅ Redis import OK')"
python -c "import xline.infrastructure.messaging.nats.bus; print('✅ NATS import OK')"

# Test coverage
python -m pytest tests/ --cov=95 --cov-report=term-missing

# Type checking
mypy xline/ --strict --disallow-any-generics

# Code quality
black --check xline/ tests/
flake8 xline/ tests/ --max-complexity=10
bandit -r xline/ -ll -i
```

---

## 🚀 **SUCCESS INDICATORS**

### ✅ **Daily Success Checklist:**
- [ ] All required files created
- [ ] All validation commands pass
- [ ] Test coverage ≥95%
- [ ] Type checking passes
- [ ] Code quality checks pass
- [ ] Performance targets met
- [ ] Documentation updated

### 🎯 **Week 1 Completion Indicators:**
- [ ] Event Bus Foundation complete
- [ ] Redis + NATS implementations working
- [ ] Fallback system functional
- [ ] Complete event type system
- [ ] Comprehensive test suite
- [ ] Performance benchmarks met
- [ ] Complete documentation

**🎉 Week 1 Success Rate Target: 95%**

Ready để proceed to Week 2: Freqtrade Integration!
