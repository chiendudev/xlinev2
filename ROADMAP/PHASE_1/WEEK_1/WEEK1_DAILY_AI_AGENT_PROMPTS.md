# WEEK 1: EVENT BUS FOUNDATION - DAILY AI AGENT IMPLEMENTATION PROMPTS
## 🎯 Tuần 1: Implement Event Bus Foundation (September 8-14, 2025)

---

## 🔒 **MANDATORY COMPLIANCE FRAMEWORK**

**⚠️ AI AGENT PHẢI TUÂN THỦ NGHIÊM NGẶT:**

### **Quy tắc bắt buộc cho mọi implementation:**
1. **100% Type Coverage**: Tất cả code phải có type hints
2. **90%+ Test Coverage**: Mọi function phải có unit tests
3. **Event-Driven Only**: KHÔNG được có direct imports giữa domains
4. **Security First**: KHÔNG hardcode secrets, credentials
5. **Production Ready**: Mọi component phải có fallback strategy

### **Daily Validation Commands (PHẢI PASS):**
```bash
# Chạy TRƯỚC KHI commit - PHẢI pass 100%
python -m pytest tests/ --cov=90 --cov-fail-under=90
mypy xline/ --strict --disallow-any-generics
black --check xline/ tests/
flake8 xline/ tests/ --max-complexity=10
bandit -r xline/ -ll -i
```

---

# 📅 **NGÀY 1 (September 8, 2025): PROJECT FOUNDATION & EVENT BUS CORE**

## 🤖 **AI AGENT PROMPT - NGÀY 1**

```
NHIỆM VỤ: Khởi tạo Xline Enterprise Project và implement Event Bus Core

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md (lines 162-199)
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/IMPLEMENTATION_TEMPLATES.md 
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/TESTING_STRATEGY.md

YÊU CẦU THỰC HIỆN:

1. TẠO CẤU TRÚC PROJECT (Task 1.1):
   - Tạo đúng cấu trúc thư mục như trong DETAILED_WEEKLY_PLAN.md
   - mkdir -p xline/{core,enterprise,infrastructure,api,web,tests}
   - mkdir -p xline/core/{events,adapters,engine}
   - mkdir -p xline/enterprise/{accounts,auth,risk,analytics,compliance,secrets}
   - mkdir -p xline/infrastructure/{observability,messaging,security,docker,kubernetes}

2. SETUP DEVELOPMENT ENVIRONMENT (Task 1.2):
   - Tạo pyproject.toml với CHÍNH XÁC dependencies từ DETAILED_WEEKLY_PLAN.md
   - Cài đặt pre-commit hooks cho quality gates
   - Setup mypy, black, flake8, bandit với strict config

3. IMPLEMENT EVENT BUS CORE (Task 1.3):
   - File: xline/core/events/bus.py
   - Implement EventBusInterface Protocol từ IMPLEMENTATION_TEMPLATES.md
   - Tất cả methods PHẢI có type hints và docstrings
   - PHẢI follow Universal Component Implementation Pattern

VALIDATION REQUIREMENTS:
- PHẢI pass: python -m pytest tests/core/events/ --cov=95
- PHẢI pass: mypy xline/core/events/ --strict
- PHẢI pass: python -c "import xline.core.events.bus; print('✅ Event bus import successful')"

DELIVERABLES:
- Working dev environment setup
- Project skeleton with correct structure
- Event bus core interface implemented
- All quality gates passing
- Git repository initialized with proper .gitignore

ROLLBACK STRATEGY:
- Nếu validation fail → restore from git tag day1-baseline
- Chỉ proceed sang Day 2 khi ALL validation commands pass
```

---

# 📅 **NGÀY 2 (September 9, 2025): REDIS STREAMS IMPLEMENTATION**

## 🤖 **AI AGENT PROMPT - NGÀY 2**

```
NHIỆM VỤ: Implement Redis Streams Event Bus với Circuit Breaker Pattern

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md (lines 201-208)
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/IMPLEMENTATION_TEMPLATES.md (Redis EventBus section)

YÊU CẦU THỰC HIỆN:

1. REDIS EVENT BUS IMPLEMENTATION (Task 1.4):
   - File: xline/infrastructure/messaging/redis/bus.py
   - Implement CHÍNH XÁC theo template trong IMPLEMENTATION_TEMPLATES.md
   - PHẢI có CircuitBreaker integration
   - PHẢI có exponential backoff retry logic
   - PHẢI có connection health monitoring

2. DEAD LETTER QUEUE (Task 1.5):
   - Implement poison message handling
   - Move failed messages to DLQ automatically
   - Add DLQ monitoring và alerting

3. EVENT SERIALIZATION (Task 1.6):
   - Type-safe JSON serialization
   - Support for complex data types (Decimal, datetime)
   - Event versioning support
   - Backward compatibility handling

MANDATORY CODE PATTERNS:
```python
class RedisEventBus(EventBusInterface):
    """PHẢI implement theo IMPLEMENTATION_TEMPLATES.md"""
    
    def __init__(self, redis_url: str, max_retries: int = 3):
        # PHẢI có circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=redis.RedisError
        )
    
    async def publish(self, event: Event) -> PublishResult:
        """PHẢI có type hints và error handling"""
        # Implementation từ template
    
    async def subscribe(self, event_type: str, handler: EventHandler) -> SubscriptionId:
        """PHẢI có consumer group management"""
        # Implementation từ template
```

PERFORMANCE REQUIREMENTS:
- Redis event bus PHẢI hoạt động với <50ms latency
- Handle connection failures gracefully
- Support consumer groups với automatic rebalancing

VALIDATION REQUIREMENTS:
- PHẢI pass: ./scripts/validate_redis_integration.sh
- PHẢI test: Connection failure scenarios
- PHẢI test: Message publishing/consuming flows
- Test coverage ≥95% for Redis components

SECURITY REQUIREMENTS:
- NO hardcoded Redis credentials
- Use environment variables for config
- Enable Redis AUTH if available
- Secure connection strings
```

---

# 📅 **NGÀY 3 (September 10, 2025): NATS ALTERNATIVE IMPLEMENTATION**

## 🤖 **AI AGENT PROMPT - NGÀY 3**

```
NHIỆM VỤ: Implement NATS JetStream Event Bus như fallback option

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md (lines 210-213)
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/IMPLEMENTATION_TEMPLATES.md (EventBusFactory section)

YÊU CẦU THỰC HIỆN:

1. NATS EVENT BUS (Task 1.7):
   - File: xline/infrastructure/messaging/nats/bus.py
   - Implement NATSEventBus theo EventBusInterface
   - Support JetStream persistent messaging
   - Auto-create streams cho different event types

2. EVENT BUS FACTORY (Task 1.8):
   - File: xline/core/events/factory.py  
   - Implement EventBusFactory với tiered fallback
   - CHÍNH XÁC theo TieredComponentFactory pattern trong IMPLEMENTATION_TEMPLATES.md
   - Production → Development → Mock fallback chain

3. ERROR RECOVERY (Task 1.9):
   - Comprehensive connection retry logic
   - Automatic failover between Redis và NATS
   - Health check monitoring cho both systems

MANDATORY IMPLEMENTATION PATTERN:
```python
class EventBusFactory(TieredComponentFactory[EventBusInterface]):
    """PHẢI follow pattern từ IMPLEMENTATION_TEMPLATES.md"""
    
    async def _create_production_implementation(self) -> EventBusInterface:
        """Redis-based production implementation"""
        # PHẢI implement theo template
    
    async def _create_development_implementation(self) -> EventBusInterface:
        """NATS-based development implementation"""
        # PHẢI implement theo template
        
    async def _create_mock_implementation(self) -> EventBusInterface:
        """In-memory mock - PHẢI ALWAYS WORK"""
        return InMemoryEventBus()
```

NATS SPECIFIC REQUIREMENTS:
- JetStream streams for: TRADING, RISK, ACCOUNTS, SYSTEM
- Subject-based routing: trading.*, risk.*, accounts.*, system.*
- Stream persistence and retention policies
- Consumer group support

VALIDATION REQUIREMENTS:
- PHẢI test: NATS connection và failover
- PHẢI test: EventBusFactory fallback chain
- PHẢI test: Both Redis và NATS working simultaneously
- Performance: Handle same throughput as Redis
- PHẢI pass all existing Event Bus tests với NATS backend

FAILOVER TESTING:
- Test Redis down → automatic NATS failover
- Test NATS down → continue with Redis
- Test both down → InMemory fallback works
- Recovery testing when services come back online
```

---

# 📅 **NGÀY 4 (September 11, 2025): EVENT TYPES & SERIALIZATION**

## 🤖 **AI AGENT PROMPT - NGÀY 4**

```
NHIỆM VỤ: Define comprehensive event type system với type safety

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/AI_AGENT_IMPLEMENTATION_ROADMAP.md (Event Types section)
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/TESTING_STRATEGY.md (Event serialization tests)

YÊU CẦU THỰC HIỆN:

1. EVENT TYPE DEFINITIONS (Task 1.10):
   - File: xline/core/events/types.py
   - Define CHÍNH XÁC event types từ AI_AGENT_IMPLEMENTATION_ROADMAP.md:
     * OrderEvent, TradeEvent, RiskEvent, AccountEvent, SystemEvent
   - Use Pydantic models cho type safety
   - Include correlation_id cho tracing

2. EVENT VERSIONING (Task 1.11):
   - File: xline/core/events/versioning.py
   - Semantic versioning cho events (v1.0, v1.1, etc.)
   - Backward compatibility handling
   - Schema evolution support

3. EVENT VALIDATION (Task 1.12):
   - File: xline/core/events/validation.py
   - Pydantic validation cho all event fields
   - Custom validators cho business rules
   - Error handling cho invalid events

MANDATORY EVENT MODELS:
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from uuid import UUID

@dataclass
class Event:
    """Base event class - PHẢI có all required fields"""
    id: str
    type: str  
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    version: str = "1.0"

@dataclass  
class OrderEvent(Event):
    """Trading order event - PHẢI match AI_AGENT_IMPLEMENTATION_ROADMAP.md"""
    order_id: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    order_type: str
    status: str

@dataclass
class TradeEvent(Event):
    """Trade execution event"""
    trade_id: str
    order_id: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    commission: Decimal

@dataclass
class RiskEvent(Event):
    """Risk management event"""
    account_id: str
    rule_type: str
    severity: str
    threshold: Decimal
    current_value: Decimal
    message: str
```

SERIALIZATION REQUIREMENTS:
- JSON serialization với custom encoders
- Handle Decimal, datetime, UUID types properly
- Compression support for large events
- Event size optimization
- Schema validation on deserialize

VALIDATION REQUIREMENTS:
- PHẢI pass: All event types properly typed
- PHẢI pass: Event serialization roundtrip tests
- PHẢI pass: Schema validation tests
- PHẢI pass: Backward compatibility tests
- Test coverage ≥95% cho event system

TYPE SAFETY REQUIREMENTS:
- 100% mypy compliance với strict mode
- All event fields properly typed
- Generic event handlers with proper typing
- No Any types except in data field
```

---

# 📅 **NGÀY 5 (September 12, 2025): INTEGRATION TESTING & PERFORMANCE**

## 🤖 **AI AGENT PROMPT - NGÀY 5**

```
NHIỆM VỤ: Comprehensive integration testing và performance validation

TUÂN THỦ NGHIÊM NGẶT:
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/TESTING_STRATEGY.md (Integration Testing section)
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md (Performance requirements)

YÊU CẦU THỰC HIỆN:

1. INTEGRATION TEST SUITE (Task 1.13):
   - File: tests/integration/events/test_event_bus_integration.py
   - PHẢI test all scenarios từ TESTING_STRATEGY.md
   - Test Redis + NATS + InMemory implementations
   - Test failover scenarios completely

2. PERFORMANCE TESTING (Task 1.14):
   - File: tests/performance/test_event_bus_performance.py
   - Target: 1000+ events/second sustained throughput
   - Latency: <100ms for event publishing (95th percentile)
   - Memory usage: <100MB under load

3. LOAD TESTING (Task 1.15):
   - File: tests/load/test_event_bus_load.py
   - Concurrent publishers và subscribers
   - Stress test với Redis và NATS
   - Memory leak detection

MANDATORY TEST SCENARIOS:
```python
@pytest.mark.asyncio
class TestEventBusIntegration:
    """PHẢI test ALL scenarios từ TESTING_STRATEGY.md"""
    
    async def test_redis_nats_failover_complete_flow(self):
        """Test complete failover chain"""
        # 1. Start with Redis
        # 2. Kill Redis → should failover to NATS
        # 3. Kill NATS → should failover to InMemory
        # 4. Restart Redis → should failover back
        # PHẢI verify data integrity through all transitions
    
    async def test_event_ordering_guarantees(self):
        """Test event ordering under load"""
        # PHẢI ensure events processed in order
    
    async def test_at_least_once_delivery(self):
        """Test delivery guarantees"""
        # PHẢI ensure no event loss
    
    async def test_poison_message_handling(self):
        """Test DLQ functionality"""
        # PHẢI handle malformed messages properly
```

PERFORMANCE REQUIREMENTS:
- Throughput: ≥1000 events/second sustained
- Latency: <100ms (95th percentile) for publish
- Memory: <100MB under normal load
- CPU: <70% under load
- No memory leaks after 1 hour sustained load

LOAD TEST VALIDATION:
```bash
# PHẢI pass these commands
./scripts/load_test_event_bus.sh --target=1000eps
# Expected output: ✅ Sustained 1000+ events/second
# Expected output: ✅ 95th percentile latency <100ms
# Expected output: ✅ Memory usage stable
```

INTEGRATION REQUIREMENTS:
- Test with Docker containers for Redis/NATS
- Test network partitions và recovery
- Test concurrent publishers/subscribers
- Test large event payloads (>1MB)
- Test event bus restart scenarios

MANDATORY VALIDATIONS:
- ALL tests PHẢI pass with ≥95% coverage
- Performance benchmarks PHẢI meet targets
- No flaky tests allowed
- All error scenarios properly handled
- Load test report với detailed metrics
```

---

# 📅 **WEEKEND (September 13-14, 2025): DOCUMENTATION & VALIDATION**

## 🤖 **AI AGENT PROMPT - WEEKEND**

```
NHIỆM VỤ: Complete documentation và week 1 final validation

TUÂN THỦ NGHIÊM NGẶT:
- Reference: ALL previous documents trong Phase 1
- Reference: /Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md (Week 1 success metrics)

YÊU CẦU THỰC HIỆN:

1. TECHNICAL DOCUMENTATION (Task 1.16):
   - File: docs/event-bus/architecture.md
   - Complete architecture documentation với diagrams
   - API documentation cho all public interfaces
   - Configuration guide cho Redis/NATS/InMemory
   - Troubleshooting guide

2. DEPLOYMENT GUIDES (Task 1.17):
   - File: docs/deployment/event-bus-setup.md
   - Docker compose configurations
   - Kubernetes deployment manifests
   - Production configuration examples
   - Monitoring setup guide

3. END-TO-END VALIDATION (Task 1.18):
   - File: scripts/validate_week1_complete.sh
   - Comprehensive validation script
   - Test ALL components together
   - Validate ALL success criteria met

DOCUMENTATION REQUIREMENTS:
```markdown
# docs/event-bus/architecture.md
## Event Bus Architecture

### Overview
- Event-driven architecture pattern
- Multiple implementation support (Redis/NATS/InMemory)
- Tiered fallback strategy

### Components
- EventBusInterface: Core interface
- RedisEventBus: Production implementation
- NATSEventBus: Alternative implementation  
- InMemoryEventBus: Fallback implementation
- EventBusFactory: Factory with fallback chain

### Event Types
- OrderEvent: Trading order events
- TradeEvent: Trade execution events
- RiskEvent: Risk management events
- AccountEvent: Account management events
- SystemEvent: System-level events

### Configuration
[Detailed configuration examples]

### Performance Characteristics
[Benchmarking results]

### Troubleshooting
[Common issues và solutions]
```

FINAL VALIDATION CHECKLIST:
- [ ] Event bus core architecture implemented và tested
- [ ] Redis Streams integration với circuit breaker pattern  
- [ ] NATS alternative implementation với automatic failover
- [ ] Comprehensive error handling và recovery mechanisms
- [ ] Performance targets met (1000+ events/second, <100ms latency)
- [ ] Integration tests covering all failure scenarios
- [ ] 95%+ test coverage với strict type checking
- [ ] Complete documentation với examples
- [ ] Production deployment ready

WEEK 1 SUCCESS SCRIPT:
```bash
#!/bin/bash
# scripts/validate_week1_complete.sh

echo "🔍 Validating Week 1 Implementation..."

# Code Quality Gates
echo "📊 Running quality gates..."
python -m pytest tests/ --cov=95 --cov-fail-under=95 || exit 1
mypy xline/ --strict --disallow-any-generics || exit 1
black --check xline/ tests/ || exit 1
flake8 xline/ tests/ --max-complexity=10 || exit 1
bandit -r xline/ -ll -i || exit 1

# Performance Tests
echo "⚡ Running performance tests..."
python -m pytest tests/performance/ || exit 1

# Integration Tests  
echo "🔗 Running integration tests..."
python -m pytest tests/integration/ || exit 1

# Load Tests
echo "📈 Running load tests..."
./tests/load/run_load_tests.sh || exit 1

echo "✅ Week 1 Implementation Complete!"
echo "✅ Ready for Week 2: Freqtrade Integration"
```

DELIVERABLES CHECKLIST:
- [ ] Production-ready event bus với Redis/NATS
- [ ] Comprehensive test suite với 95%+ coverage
- [ ] Complete documentation set
- [ ] Deployment automation scripts
- [ ] Performance benchmarking results
- [ ] All quality gates passing
- [ ] Week 2 preparation complete
```

---

## 🎯 **TUẦN 1 SUCCESS CRITERIA**

### ✅ **TECHNICAL DELIVERABLES:**
1. **Event Bus Core**: Production-ready với multiple implementations
2. **Redis Integration**: Streams + Circuit breaker + DLQ
3. **NATS Integration**: JetStream + Automatic failover  
4. **Event Types**: Complete type system với validation
5. **Testing**: 95%+ coverage với integration/performance tests
6. **Documentation**: Complete technical documentation

### 📊 **PERFORMANCE TARGETS:**
- **Throughput**: ≥1000 events/second sustained
- **Latency**: <100ms (95th percentile)
- **Memory**: <100MB under normal load
- **Reliability**: 99.9% message delivery
- **Failover**: <30 seconds recovery time

### 🔒 **QUALITY GATES:**
- **Type Coverage**: 100% mypy compliance
- **Test Coverage**: ≥95% line coverage
- **Security**: Zero hardcoded credentials
- **Architecture**: Event-driven only, no direct imports
- **Documentation**: All APIs documented với examples

### 🚨 **MANDATORY VALIDATIONS:**
- ALL daily validation commands PHẢI pass
- Performance benchmarks PHẢI meet targets  
- Integration tests PHẢI cover all scenarios
- Documentation PHẢI be complete và accurate
- Production deployment PHẢI work end-to-end

---

**🚀 CHỈ KHI TẤT CẢ REQUIREMENTS ĐÃ ĐẦY ĐỦ THÌ MỚI PROCEED SANG WEEK 2**
