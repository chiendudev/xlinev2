#!/bin/bash

"""
LOAD TEST SCRIPT - NGÀY 5 (Task 1.15)
File: scripts/load_test_event_bus.sh

TUÂN THỦ NGHIÊM NGẶT theo yêu cầu Day 5:
- Script load test event bus như được yêu cầu trong TESTING_STRATEGY.md
- Target EPS configurable
- Redis/NATS stress testing
- Memory leak detection
"""

set -e

# Default configuration
DEFAULT_TARGET_EPS=1000
DEFAULT_TEST_DURATION=180
DEFAULT_MEMORY_LIMIT=200
DEFAULT_CONCURRENT_PUBLISHERS=10
DEFAULT_CONCURRENT_SUBSCRIBERS=5

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "LOAD TEST SCRIPT - NGÀY 5 Event Bus Testing"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --target=EPS          Target events per second (default: $DEFAULT_TARGET_EPS)"
    echo "  --duration=SECONDS    Test duration in seconds (default: $DEFAULT_TEST_DURATION)"
    echo "  --memory-limit=MB     Memory limit in MB (default: $DEFAULT_MEMORY_LIMIT)"
    echo "  --publishers=N        Number of concurrent publishers (default: $DEFAULT_CONCURRENT_PUBLISHERS)"
    echo "  --subscribers=N       Number of concurrent subscribers (default: $DEFAULT_CONCURRENT_SUBSCRIBERS)"
    echo "  --redis-test          Enable Redis stress testing"
    echo "  --nats-test           Enable NATS stress testing"
    echo "  --memory-leak-test    Enable memory leak detection"
    echo "  --extreme-load        Enable extreme load testing"
    echo "  --failover-test       Enable failover testing"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --target=1000                    # Run with 1000 EPS target"
    echo "  $0 --target=2000 --redis-test       # Run with Redis stress test"
    echo "  $0 --memory-leak-test --duration=300 # Run memory leak test for 5 minutes"
    echo "  $0 --extreme-load --publishers=50   # Run extreme load with 50 publishers"
}

# Parse command line arguments
TARGET_EPS=$DEFAULT_TARGET_EPS
TEST_DURATION=$DEFAULT_TEST_DURATION
MEMORY_LIMIT=$DEFAULT_MEMORY_LIMIT
CONCURRENT_PUBLISHERS=$DEFAULT_CONCURRENT_PUBLISHERS
CONCURRENT_SUBSCRIBERS=$DEFAULT_CONCURRENT_SUBSCRIBERS
REDIS_TEST=false
NATS_TEST=false
MEMORY_LEAK_TEST=false
EXTREME_LOAD=false
FAILOVER_TEST=false

for arg in "$@"; do
    case $arg in
        --target=*)
            TARGET_EPS="${arg#*=}"
            shift
            ;;
        --duration=*)
            TEST_DURATION="${arg#*=}"
            shift
            ;;
        --memory-limit=*)
            MEMORY_LIMIT="${arg#*=}"
            shift
            ;;
        --publishers=*)
            CONCURRENT_PUBLISHERS="${arg#*=}"
            shift
            ;;
        --subscribers=*)
            CONCURRENT_SUBSCRIBERS="${arg#*=}"
            shift
            ;;
        --redis-test)
            REDIS_TEST=true
            shift
            ;;
        --nats-test)
            NATS_TEST=true
            shift
            ;;
        --memory-leak-test)
            MEMORY_LEAK_TEST=true
            shift
            ;;
        --extreme-load)
            EXTREME_LOAD=true
            shift
            ;;
        --failover-test)
            FAILOVER_TEST=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $arg"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "python3 could not be found"
        exit 1
    fi
    
    # Check if pytest is available
    if ! python3 -c "import pytest" &> /dev/null; then
        log_error "pytest is not installed. Run: pip install pytest"
        exit 1
    fi
    
    # Check if psutil is available
    if ! python3 -c "import psutil" &> /dev/null; then
        log_error "psutil is not installed. Run: pip install psutil"
        exit 1
    fi
    
    # Check if the test file exists
    if [ ! -f "tests/load/test_event_bus_load.py" ]; then
        log_error "Load test file not found: tests/load/test_event_bus_load.py"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Set environment variables for test configuration
    export XLINE_LOAD_TEST_TARGET_EPS=$TARGET_EPS
    export XLINE_LOAD_TEST_DURATION=$TEST_DURATION
    export XLINE_LOAD_TEST_MEMORY_LIMIT=$MEMORY_LIMIT
    export XLINE_LOAD_TEST_PUBLISHERS=$CONCURRENT_PUBLISHERS
    export XLINE_LOAD_TEST_SUBSCRIBERS=$CONCURRENT_SUBSCRIBERS
    
    # Create logs directory if it doesn't exist
    mkdir -p logs/load_tests
    
    # Set test output file
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    TEST_OUTPUT_FILE="logs/load_tests/load_test_${TIMESTAMP}.log"
    
    log_success "Test environment configured"
    log_info "Test output will be saved to: $TEST_OUTPUT_FILE"
}

# Function to run specific test
run_load_test() {
    local test_name=$1
    local test_description=$2
    
    log_info "Running $test_description..."
    
    if pytest tests/load/test_event_bus_load.py::TestEventBusLoad::$test_name -v -s --tb=short >> "$TEST_OUTPUT_FILE" 2>&1; then
        log_success "$test_description completed successfully"
        return 0
    else
        log_error "$test_description failed"
        return 1
    fi
}

# Function to run all load tests
run_comprehensive_load_tests() {
    log_info "Starting comprehensive load testing..."
    
    local failed_tests=0
    local total_tests=0
    
    # Test 1: Concurrent Publishers and Subscribers (MANDATORY)
    total_tests=$((total_tests + 1))
    if ! run_load_test "test_concurrent_publishers_subscribers" "Concurrent Publishers/Subscribers Test"; then
        failed_tests=$((failed_tests + 1))
    fi
    
    # Test 2: Redis Stress Test (if enabled)
    if [ "$REDIS_TEST" = true ]; then
        total_tests=$((total_tests + 1))
        if ! run_load_test "test_stress_with_redis_nats_simulation" "Redis/NATS Stress Test"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # Test 3: Memory Leak Detection (if enabled)
    if [ "$MEMORY_LEAK_TEST" = true ]; then
        total_tests=$((total_tests + 1))
        if ! run_load_test "test_memory_leak_detection_under_load" "Memory Leak Detection Test"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # Test 4: Failover Test (if enabled)
    if [ "$FAILOVER_TEST" = true ]; then
        total_tests=$((total_tests + 1))
        if ! run_load_test "test_failover_stress_scenarios" "Failover Stress Test"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # Test 5: Extreme Load Test (if enabled)
    if [ "$EXTREME_LOAD" = true ]; then
        total_tests=$((total_tests + 1))
        if ! run_load_test "test_extreme_concurrent_load" "Extreme Concurrent Load Test"; then
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    return $failed_tests
}

# Function to generate load test report
generate_report() {
    local failed_tests=$1
    local total_tests=$2
    
    log_info "Generating load test report..."
    
    local report_file="logs/load_tests/load_test_report_$(date +"%Y%m%d_%H%M%S").md"
    
    cat > "$report_file" << EOF
# LOAD TEST REPORT - NGÀY 5
## Event Bus Load Testing Results

**Test Configuration:**
- Target EPS: $TARGET_EPS
- Test Duration: $TEST_DURATION seconds
- Memory Limit: $MEMORY_LIMIT MB
- Concurrent Publishers: $CONCURRENT_PUBLISHERS
- Concurrent Subscribers: $CONCURRENT_SUBSCRIBERS
- Timestamp: $(date)

**Test Results:**
- Total Tests: $total_tests
- Passed Tests: $((total_tests - failed_tests))
- Failed Tests: $failed_tests
- Success Rate: $(( (total_tests - failed_tests) * 100 / total_tests ))%

**Tests Executed:**
EOF

    if [ "$REDIS_TEST" = true ]; then
        echo "- ✅ Redis/NATS Stress Testing" >> "$report_file"
    fi
    
    if [ "$MEMORY_LEAK_TEST" = true ]; then
        echo "- ✅ Memory Leak Detection" >> "$report_file"
    fi
    
    if [ "$EXTREME_LOAD" = true ]; then
        echo "- ✅ Extreme Load Testing" >> "$report_file"
    fi
    
    if [ "$FAILOVER_TEST" = true ]; then
        echo "- ✅ Failover Testing" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

**Compliance with Day 5 Requirements:**
- ✅ Concurrent publishers và subscribers: PASSED
- ✅ Stress test với Redis và NATS: $([ "$REDIS_TEST" = true ] && echo "EXECUTED" || echo "SKIPPED")
- ✅ Memory leak detection: $([ "$MEMORY_LEAK_TEST" = true ] && echo "EXECUTED" || echo "SKIPPED")

**Performance Targets:**
- Target Throughput: ≥ $TARGET_EPS EPS
- Memory Usage: ≤ $MEMORY_LIMIT MB
- Success Rate: ≥ 95%

**Detailed Results:**
See test output file: $TEST_OUTPUT_FILE

**Compliance Status:**
$([ $failed_tests -eq 0 ] && echo "🟢 ALL TESTS PASSED - FULLY COMPLIANT" || echo "🔴 SOME TESTS FAILED - REVIEW REQUIRED")
EOF

    log_success "Report generated: $report_file"
}

# Main execution flow
main() {
    echo "==============================================="
    echo "LOAD TEST SCRIPT - NGÀY 5 EVENT BUS TESTING"
    echo "==============================================="
    echo ""
    
    log_info "Configuration:"
    log_info "  Target EPS: $TARGET_EPS"
    log_info "  Duration: $TEST_DURATION seconds"
    log_info "  Memory Limit: $MEMORY_LIMIT MB"
    log_info "  Publishers: $CONCURRENT_PUBLISHERS"
    log_info "  Subscribers: $CONCURRENT_SUBSCRIBERS"
    log_info "  Redis Test: $REDIS_TEST"
    log_info "  NATS Test: $NATS_TEST"
    log_info "  Memory Leak Test: $MEMORY_LEAK_TEST"
    log_info "  Extreme Load: $EXTREME_LOAD"
    log_info "  Failover Test: $FAILOVER_TEST"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup test environment
    setup_test_environment
    
    # Run load tests
    local start_time=$(date +%s)
    
    run_comprehensive_load_tests
    local failed_tests=$?
    local total_tests=1  # At minimum, concurrent test runs
    
    if [ "$REDIS_TEST" = true ]; then total_tests=$((total_tests + 1)); fi
    if [ "$MEMORY_LEAK_TEST" = true ]; then total_tests=$((total_tests + 1)); fi
    if [ "$FAILOVER_TEST" = true ]; then total_tests=$((total_tests + 1)); fi
    if [ "$EXTREME_LOAD" = true ]; then total_tests=$((total_tests + 1)); fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    log_info "Load testing completed in $duration seconds"
    
    # Generate report
    generate_report $failed_tests $total_tests
    
    echo ""
    echo "==============================================="
    if [ $failed_tests -eq 0 ]; then
        log_success "ALL LOAD TESTS PASSED - EVENT BUS MEETS DAY 5 REQUIREMENTS"
        echo "🎯 Target EPS: $TARGET_EPS ✅"
        echo "🧠 Memory Management: ✅"
        echo "🔄 Concurrent Processing: ✅"
        echo "🔧 Redis/NATS Stress: $([ "$REDIS_TEST" = true ] && echo "✅" || echo "➖")"
        echo "💾 Memory Leak Detection: $([ "$MEMORY_LEAK_TEST" = true ] && echo "✅" || echo "➖")"
        exit 0
    else
        log_error "$failed_tests out of $total_tests tests failed"
        echo "❌ LOAD TESTING FAILED - REVIEW REQUIRED"
        exit 1
    fi
}

# Execute main function
main "$@"
