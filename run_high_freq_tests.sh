#!/bin/bash
# High-frequency test runner
# Runs all three stages of high-frequency validation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "======================================================================"
    echo "$1"
    echo "======================================================================"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Main test script
print_header "High-Frequency Validation Test Suite"
echo "PRD High-Frequency Testing Plan"
echo ""
echo "This script runs all three stages of validation:"
echo "  Stage 1: 50-100 kHz (multi-channel)"
echo "  Stage 2: 100-500 kHz (stress test)"
echo "  Stage 3: 500 kHz-1 Msps (latency test)"
echo ""
echo "Requirements:"
echo "  - sudo access (GPIO access requires root)"
echo "  - libgpiod-dev installed"
echo "  - Signal generator connected to GPIO5 (Pin 29)"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (sudo)"
    echo "Run with: sudo ./run_high_freq_tests.sh"
    exit 1
fi

print_success "Running as root"

# Check if test binaries exist
print_header "Checking test binaries"

BINARIES=("multi_channel_freq_test" "high_freq_stress_test" "latency_test")
MISSING_BINS=()

for bin in "${BINARIES[@]}"; do
    if [ -f "./$bin" ]; then
        print_success "$bin exists"
    else
        print_warning "$bin not found"
        MISSING_BINS+=("$bin")
    fi
done

# Compile missing binaries
if [ ${#MISSING_BINS[@]} -gt 0 ]; then
    echo ""
    print_warning "Some binaries missing, compiling..."
    echo ""

    for bin in "${MISSING_BINS[@]}"; do
        case "$bin" in
            "multi_channel_freq_test")
                ./compile_multi_channel_test.sh || exit 1
                ;;
            "high_freq_stress_test")
                ./compile_stress_test.sh || exit 1
                ;;
            "latency_test")
                ./compile_latency_test.sh || exit 1
                ;;
        esac
    done

    echo ""
    print_success "All binaries compiled"
fi

# Ask user which stages to run
print_header "Select Test Stages"
echo "Select which stages to run:"
echo "  1) Stage 1 only (50-100 kHz, ~1 minute)"
echo "  2) Stage 2 only (100-500 kHz, ~5 minutes)"
echo "  3) Stage 3 only (500 kHz-1 Msps, ~1 minute)"
echo "  4) All stages (recommended, ~7 minutes)"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1) STAGES=(1) ;;
    2) STAGES=(2) ;;
    3) STAGES=(3) ;;
    4) STAGES=(1 2 3) ;;
    5) echo "Exiting..."; exit 0 ;;
    *) print_error "Invalid choice"; exit 1 ;;
esac

# Run selected stages
STAGE1_PASSED=false
STAGE2_PASSED=false
STAGE3_PASSED=false

for stage in "${STAGES[@]}"; do
    case $stage in
        1)
            print_header "Running Stage 1: 50-100 kHz Multi-Channel Test"
            echo "This tests all 4 channels simultaneously at 50, 75, and 100 kHz"
            echo "Expected duration: ~1 minute"
            echo ""
            read -p "Press Enter to continue or Ctrl+C to cancel..."
            echo ""

            if ./multi_channel_freq_test; then
                STAGE1_PASSED=true
                print_success "Stage 1 PASSED"
            else
                print_error "Stage 1 FAILED"
            fi
            ;;

        2)
            print_header "Running Stage 2: 100-500 kHz Stress Test"
            echo "This tests stability and performance at 100, 200, and 500 kHz"
            echo "Expected duration: ~5 minutes"
            echo ""
            read -p "Press Enter to continue or Ctrl+C to cancel..."
            echo ""

            if ./high_freq_stress_test; then
                STAGE2_PASSED=true
                print_success "Stage 2 PASSED"
            else
                print_error "Stage 2 FAILED"
            fi
            ;;

        3)
            print_header "Running Stage 3: 500 kHz-1 Msps Latency Test"
            echo "This tests trigger-to-display latency at 500 kHz, 750 kHz, and 1 Msps"
            echo "Expected duration: ~1 minute"
            echo ""
            read -p "Press Enter to continue or Ctrl+C to cancel..."
            echo ""

            if ./latency_test; then
                STAGE3_PASSED=true
                print_success "Stage 3 PASSED"
            else
                print_error "Stage 3 FAILED"
            fi
            ;;
    esac
done

# Print final summary
print_header "Test Summary"

echo ""
echo "Results:"
echo "  Stage 1 (50-100 kHz):     $([ "$STAGE1_PASSED" = true ] && echo "✓ PASS" || echo "✗ FAIL / NOT RUN")"
echo "  Stage 2 (100-500 kHz):   $([ "$STAGE2_PASSED" = true ] && echo "✓ PASS" || echo "✗ FAIL / NOT RUN")"
echo "  Stage 3 (500 kHz-1 Msps): $([ "$STAGE3_PASSED" = true ] && echo "✓ PASS" || echo "✗ FAIL / NOT RUN")"
echo ""

# Determine overall result
if [ "$STAGE1_PASSED" = true ] && [ "$STAGE2_PASSED" = true ] && [ "$STAGE3_PASSED" = true ]; then
    print_success "ALL TESTS PASSED"
    echo ""
    echo "✓ libgpiod C++ with edge events meets all PRD requirements"
    echo "✓ Ready for production deployment of oscilloscope"
    echo "✓ 1 Msps sampling rate achievable"
    echo "✓ < 100 ms trigger-to-display latency achievable"
    echo "✓ 4-channel simultaneous sampling verified"
    exit 0
elif [ "$STAGE1_PASSED" = true ] && [ "$STAGE2_PASSED" = true ]; then
    print_warning "Stage 3 FAILED but Stages 1-2 PASSED"
    echo ""
    echo "⚠ 1 Msps sampling rate may not be achievable with < 100 ms latency"
    echo "⚠ Consider:"
    echo "  1. Relaxing latency requirement to 150 ms"
    echo "  2. Reducing sample depth from 100k to 50k points"
    echo "  3. Implementing advanced GUI optimization (GPU acceleration)"
    echo "  4. Alternative: Deploy with 500 kHz max sampling rate"
    exit 1
elif [ "$STAGE1_PASSED" = true ]; then
    print_warning "Stage 2 FAILED but Stage 1 PASSED"
    echo ""
    echo "⚠ Sampling rate > 100 kHz may not be stable"
    echo "⚠ Consider:"
    echo "  1. Lowering PRD target to 100 ksps"
    echo "  2. Implementing memory mapping for higher performance (complex)"
    echo "  3. Alternative: Deploy with 100 kHz max sampling rate"
    exit 1
else
    print_error "Stage 1 FAILED - CRITICAL ISSUE"
    echo ""
    echo "✗ Basic multi-channel sampling at 50-100 kHz is failing"
    echo "✗ Check:"
    echo "  1. Signal connections to GPIO4/5/6/7"
    echo "  2. Signal generator frequency and amplitude (3.3V)"
    echo "  3. System load (run tests with minimal load)"
    echo "  4. GPIO access permissions (running as root)"
    echo ""
    echo "✗ Cannot proceed to Stage 2 or 3"
    exit 1
fi
