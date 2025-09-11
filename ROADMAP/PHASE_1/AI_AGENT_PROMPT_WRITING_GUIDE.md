# AI AGENT PROMPT WRITING GUIDE - WEEK 1 IMPLEMENTATION
## 🎯 Hướng dẫn viết prompt hiệu quả cho AI Agent implement Event Bus Foundation

---

## 📋 **PROMPT STRUCTURE TEMPLATE**

### **🔥 ESSENTIAL PROMPT FRAMEWORK:**

```markdown
# WEEK 1 DAY [X] IMPLEMENTATION - EVENT BUS FOUNDATION

## 🎯 MISSION CRITICAL REQUIREMENTS:
- ✅ **MANDATORY COMPLIANCE**: Follow WEEK1_DAILY_AI_AGENT_PROMPTS.md Day [X] exactly
- ✅ **ZERO TOLERANCE**: All validation commands MUST pass before proceeding
- ✅ **DOCUMENT ADHERENCE**: Strict compliance với AI_AGENT_IMPLEMENTATION_ROADMAP.md
- ✅ **ROLLBACK STRATEGY**: If validation fails, rollback and fix immediately

## 📁 REQUIRED CONTEXT DOCUMENTS:
1. `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/WEEK1_DAILY_AI_AGENT_PROMPTS.md`
2. `/Users/chiendu/XlineV2/AI_AGENT_IMPLEMENTATION_ROADMAP.md`
3. `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/DETAILED_WEEKLY_PLAN.md`
4. `/Users/chiendu/XlineV2/ROADMAP/PHASE_1/WEEK1_IMPLEMENTATION_TEMPLATES.md`

## 🚀 TODAY'S SPECIFIC TASKS:
[Detailed tasks from daily prompt - copy exact requirements]

## 🔒 MANDATORY VALIDATION:
```bash
# Run these commands - ALL MUST PASS:
./scripts/validate_week1_daily.sh [day_number]
```

## ⚠️ CRITICAL SUCCESS CRITERIA:
- Performance targets MUST be met
- Test coverage MUST be ≥95%
- All type hints MUST be present
- No hardcoded values allowed
```

---

## 🎯 **DAY-SPECIFIC PROMPT EXAMPLES**

### **📅 DAY 1 (Sept 9) - PROJECT FOUNDATION PROMPT:**

```markdown
# 🚀 WEEK 1 DAY 1: PROJECT FOUNDATION IMPLEMENTATION

## 🎯 MISSION: Setup complete development environment với Event Bus core

### 📋 TODAY'S DELIVERABLES:
Implement exactly theo WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 1:

1. **Project Structure Setup:**
   - Create 16 directories theo DETAILED_WEEKLY_PLAN.md structure
   - Setup pyproject.toml với 20+ required dependencies
   - Initialize git repository với proper .gitignore

2. **Event Bus Interface:**
   - File: `xline/core/events/bus.py`
   - Implement EventBusInterface Protocol exactly
   - Include all required methods: publish, subscribe, health_check

3. **Development Environment:**
   - Setup pre-commit hooks: black, mypy, flake8, bandit
   - Configure VS Code settings
   - Install all dependencies trong virtual environment

### 🔒 MANDATORY VALIDATION COMMANDS:
```bash
# ALL MUST PASS:
python -c "import xline.core.events.bus; print('✅ Import successful')"
python -m pytest tests/core/events/ --cov=95
mypy xline/core/events/ --strict
black --check xline/ tests/
flake8 xline/ tests/ --max-complexity=10
```

### ⚠️ CRITICAL REQUIREMENTS:
- EventBusInterface MUST be Protocol với proper type hints
- Project structure MUST match DETAILED_WEEKLY_PLAN.md exactly
- All imports MUST work without errors
- Test coverage MUST be ≥95%

### 🚨 FAILURE HANDLING:
If ANY validation command fails:
1. Stop immediately
2. Fix the specific issue
3. Re-run validation
4. Only proceed when ALL commands pass
```

### **📅 DAY 2 (Sept 10) - REDIS IMPLEMENTATION PROMPT:**

```markdown
# 🚀 WEEK 1 DAY 2: REDIS STREAMS IMPLEMENTATION

## 🎯 MISSION: Production-ready Redis Event Bus với Circuit Breaker

### 📋 TODAY'S DELIVERABLES:
Follow WEEK1_DAILY_AI_AGENT_PROMPTS.md Day 2 exactly:

1. **RedisEventBus Implementation:**
   - File: `xline/infrastructure/messaging/redis/bus.py`
   - Implement RedisEventBus class inheriting EventBusInterface
   - Use Redis Streams để publish/subscribe events

2. **Circuit Breaker Integration:**
   - File: `xline/core/reliability/circuit_breaker.py`
   - Integrate với Redis operations
   - Handle connection failures gracefully

3. **Dead Letter Queue:**
   - Implement poison message handling
   - Auto-retry with exponential backoff
   - Move failed messages to DLQ after max retries

### 🔒 MANDATORY VALIDATION:
```bash
# Performance Test - MUST PASS:
python -m pytest tests/infrastructure/messaging/redis/ --cov=95
python -c "
import asyncio
from xline.infrastructure.messaging.redis.bus import RedisEventBus
async def test(): 
    bus = RedisEventBus('redis://localhost:6379')
    await bus.health_check()
    print('✅ Redis connection successful')
asyncio.run(test())
"
```

### ⚠️ PERFORMANCE TARGETS:
- Latency: <50ms cho event publishing
- Reliability: Automatic connection retry
- Error handling: Graceful failure recovery
- Circuit breaker: Open after 3 consecutive failures

### 🚨 IMPLEMENTATION PATTERNS:
Use exact code patterns from WEEK1_IMPLEMENTATION_TEMPLATES.md:
- RedisEventBus class structure
- CircuitBreaker integration
- Connection retry logic
- Dead letter queue implementation
```

---

## 🔧 **PROMPT OPTIMIZATION TECHNIQUES**

### **✅ EFFECTIVE PROMPT ELEMENTS:**

1. **Clear Mission Statement:**
   ```markdown
   ## 🎯 MISSION: [Specific goal for today]
   - What exactly needs to be accomplished
   - Why it's critical for the overall system
   - How it fits into the bigger picture
   ```

2. **Explicit File Requirements:**
   ```markdown
   ## 📁 REQUIRED FILES TO CREATE:
   - `xline/core/events/bus.py` - EventBusInterface Protocol
   - `tests/core/events/test_bus.py` - Test suite với 95%+ coverage
   - `xline/infrastructure/messaging/redis/bus.py` - Redis implementation
   ```

3. **Validation Commands:**
   ```markdown
   ## 🔒 VALIDATION COMMANDS (ALL MUST PASS):
   ```bash
   python -m pytest tests/ --cov=95 --cov-fail-under=95
   mypy xline/ --strict
   black --check xline/ tests/
   ```

4. **Success Criteria:**
   ```markdown
   ## ✅ SUCCESS CRITERIA:
   - [ ] All files created và properly structured
   - [ ] All tests passing với 95%+ coverage
   - [ ] All validation commands pass
   - [ ] Performance targets met
   ```

### **❌ AVOID THESE PROMPT MISTAKES:**

1. **Vague Instructions:**
   ```markdown
   ❌ BAD: "Implement event bus"
   ✅ GOOD: "Implement EventBusInterface Protocol in xline/core/events/bus.py với specific methods: publish, subscribe, health_check"
   ```

2. **Missing Validation:**
   ```markdown
   ❌ BAD: No validation commands
   ✅ GOOD: Specific validation commands that MUST pass
   ```

3. **No Error Handling:**
   ```markdown
   ❌ BAD: No mention of what to do if tasks fail
   ✅ GOOD: Clear rollback strategy và failure handling
   ```

---

## 🎯 **DAILY PROMPT TEMPLATES**

### **📅 DAY 3 - NATS IMPLEMENTATION:**
```markdown
# 🚀 WEEK 1 DAY 3: NATS ALTERNATIVE & FALLBACK SYSTEM

## 🎯 MISSION: Implement NATS Event Bus với tiered fallback strategy

### 📋 CRITICAL DELIVERABLES:
1. **NATSEventBus**: File `xline/infrastructure/messaging/nats/bus.py`
2. **EventBusFactory**: File `xline/core/events/factory.py`
3. **Fallback Chain**: Production (Redis) → Development (NATS) → Mock (InMemory)

### 🔒 MANDATORY IMPLEMENTATION PATTERN:
```python
class EventBusFactory(TieredComponentFactory[EventBusInterface]):
    async def _create_production_implementation(self):
        # Redis - Primary production choice
        
    async def _create_development_implementation(self):
        # NATS - Development/staging choice
        
    async def _create_mock_implementation(self):
        # InMemory - MUST ALWAYS WORK
        return InMemoryEventBus()
```

### 🔒 VALIDATION:
```bash
./scripts/validate_week1_daily.sh 3
python -m pytest tests/integration/events/test_fallback.py
```
```

### **📅 DAY 4 - EVENT TYPES:**
```markdown
# 🚀 WEEK 1 DAY 4: EVENT TYPE SYSTEM & SERIALIZATION

## 🎯 MISSION: Complete type-safe event system với proper serialization

### 📋 EVENT TYPES TO IMPLEMENT:
1. **Base Event**: `xline/core/events/types.py`
2. **OrderEvent**: Trading order events
3. **TradeEvent**: Trade execution events
4. **RiskEvent**: Risk management events

### 🔒 TYPE SAFETY REQUIREMENTS:
```python
@dataclass
class OrderEvent(Event):
    order_id: str
    account_id: str
    symbol: str
    quantity: Decimal  # MUST use Decimal for precision
    price: Decimal
    timestamp: datetime
```

### 🔒 VALIDATION:
```bash
mypy xline/core/events/types.py --strict --disallow-any-generics
python -m pytest tests/core/events/test_types.py --cov=100
```
```

### **📅 DAY 5 - TESTING & PERFORMANCE:**
```markdown
# 🚀 WEEK 1 DAY 5: COMPREHENSIVE TESTING & PERFORMANCE VALIDATION

## 🎯 MISSION: Complete test suite với performance benchmarks

### 📋 TEST SUITE REQUIREMENTS:
1. **Integration Tests**: `tests/integration/events/test_event_bus_integration.py`
2. **Performance Tests**: `tests/performance/test_event_bus_performance.py`
3. **Load Tests**: `tests/load/test_event_bus_load.py`

### 🔒 PERFORMANCE BENCHMARKS:
```python
async def test_throughput():
    # Target: ≥1000 events/second sustained
    
async def test_latency():
    # Target: <100ms (95th percentile)
```

### 🔒 FINAL VALIDATION:
```bash
./scripts/validate_week1_complete.sh
python -m pytest tests/ --cov=95 --cov-fail-under=95
```
```

---

## 🚀 **PROMPT EXECUTION STRATEGY**

### **📋 STEP-BY-STEP EXECUTION:**

1. **Pre-Flight Check:**
   ```markdown
   Before starting, AI Agent should:
   - ✅ Read all required documents
   - ✅ Understand today's specific deliverables
   - ✅ Check current project state
   - ✅ Verify development environment ready
   ```

2. **Implementation Phase:**
   ```markdown
   During implementation:
   - ✅ Follow exact file structure from templates
   - ✅ Use exact code patterns provided
   - ✅ Implement all required methods
   - ✅ Add comprehensive type hints
   ```

3. **Validation Phase:**
   ```markdown
   After implementation:
   - ✅ Run ALL validation commands
   - ✅ Ensure ALL commands pass
   - ✅ Fix any issues immediately
   - ✅ Document any deviations
   ```

4. **Quality Gate:**
   ```markdown
   Before proceeding to next day:
   - ✅ Complete validation checklist
   - ✅ Confirm performance targets met
   - ✅ Update implementation documentation
   - ✅ Commit changes với proper messages
   ```

---

## 🎯 **SUCCESS METRICS FOR PROMPTS**

### **📊 Effective Prompt Indicators:**

1. **Clear Deliverables**: AI Agent knows exactly what to build
2. **Validation Commands**: Specific commands to verify success
3. **Error Handling**: Clear guidance on what to do when things fail
4. **Performance Targets**: Specific metrics to achieve
5. **Documentation Links**: Easy access to all required context

### **⚠️ Warning Signs of Poor Prompts:**

1. **Vague Instructions**: AI Agent has to guess requirements
2. **Missing Validation**: No way to verify if implementation is correct
3. **No Error Handling**: AI Agent stuck when encountering issues
4. **Missing Context**: Required documents not specified
5. **No Success Criteria**: Unclear when task is considered complete

---

## 🔥 **FINAL PROMPT CHECKLIST**

### ✅ **Before Sending Prompt to AI Agent:**

- [ ] **Specific Day**: Clear which day of Week 1 to implement
- [ ] **Required Documents**: All necessary document paths provided
- [ ] **Deliverables**: Exact files và features to implement
- [ ] **Validation Commands**: Specific commands AI Agent must run
- [ ] **Success Criteria**: Clear definition of completion
- [ ] **Error Handling**: What to do if validation fails
- [ ] **Performance Targets**: Specific metrics to achieve
- [ ] **Code Patterns**: Reference to exact implementation templates

### 🚀 **Prompt Quality Score:**

**Grade A Prompt (90-100%):**
- All checklist items present
- Specific validation commands
- Clear success criteria
- Proper error handling

**Grade B Prompt (80-89%):**
- Most checklist items present
- Some validation commands
- Basic success criteria

**Grade C Prompt (70-79%):**
- Basic requirements only
- Minimal validation
- Vague success criteria

**Minimum Acceptable: Grade B+** để ensure successful implementation!

---

**🎯 REMEMBER: The quality of your prompt directly determines the success rate of AI Agent implementation. Invest time in crafting detailed, specific prompts!**
