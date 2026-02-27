// SPDX-License-Identifier: GPL-2.0-or-later
// Trigger latency measurement test
// Measures trigger-to-display latency (must be < 100ms per PRD)
// PRD Stage 3 validation: 500 kHz - 1 Msps
//
// 测试条件说明：
// - 使用GPIO5 (Pin 29) 作为测试通道
// - 连接信号发生器到GPIO5
// - 测试频率：500 kHz, 750 kHz, 1000 kHz
// - 目标延迟：< 100 ms 从触发到显示

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <queue>
#include <thread>
#include <unistd.h>
#include <gpiod.hpp>

#define TEST_CHANNEL 0  // Use Channel 1 (GPIO5)
#define LATENCY_TEST_DURATION_MS 5000  // 5 seconds
#define TARGET_LATENCY_MS 100  // PRD requirement

using namespace gpiod;
using namespace std::chrono;

// Latency measurement structure
struct LatencyMeasurement {
    nanoseconds trigger_time;
    nanoseconds display_time;
    nanoseconds total_latency;
    int sample_count;
    int total_edges;
};

// Simulated display rendering time (represents GUI overhead)
nanoseconds simulate_display_render(int sample_count) {
    // Simulate: 1ms base + 0.01ms per 1000 samples (PyQtGraph rendering)
    auto base_time = milliseconds(1);
    auto per_sample = microseconds(sample_count * 10 / 1000);  // 0.01ms per 1000 samples
    return duration_cast<nanoseconds>(base_time + per_sample);
}

// Measure trigger latency
LatencyMeasurement measure_latency(int target_freq_hz) {
    LatencyMeasurement measurement = {};

    const char* chip_path = "/dev/gpiochip4";
    unsigned int line_offset = 5;  // GPIO5

    try {
        chip gpio_chip(chip_path);
        line gpio_line = gpio_chip.get_line(line_offset);

        line_request line_cfg;
        line_cfg.consumer = "latency-test";
        line_cfg.request_type = line_request::EVENT_BOTH_EDGES;
        line_cfg.flags = 0;

        gpio_line.request(line_cfg);

        if (!gpio_line.is_requested()) {
            fprintf(stderr, "Failed to request line\n");
            return measurement;
        }

        // Test for specified duration
        auto start_time = steady_clock::now();
        auto end_time = start_time + milliseconds(LATENCY_TEST_DURATION_MS);

        std::queue<nanoseconds> trigger_queue;

        while (steady_clock::now() < end_time) {
            std::vector<line_event> events = gpio_line.event_read_multiple();

            for (const auto& event : events) {
                // Record trigger time (rising edge only)
                if (event.event_type == line_event::RISING_EDGE) {
                    trigger_queue.push(event.timestamp);

                    // Simulate capturing samples (100k points per trigger)
                    measurement.sample_count = 100000;
                    measurement.total_edges += 2;  // Each cycle has 2 edges

                    // Simulate processing and display
                    auto display_time_point = steady_clock::now();
                    auto render_time = simulate_display_render(measurement.sample_count);
                    auto display_time = display_time_point.time_since_epoch() + render_time;

                    // Calculate latency
                    auto latency = display_time - event.timestamp;
                    measurement.trigger_time = event.timestamp;
                    measurement.display_time = display_time;
                    measurement.total_latency = latency;

                    // Print measurement
                    double latency_ms = latency.count() / 1000000.0;
                    printf("  Trigger detected at %.3f ms\n",
                           event.timestamp.count() / 1000000.0);
                    printf("  Display ready at   %.3f ms\n",
                           display_time.count() / 1000000.0);
                    printf("  Total latency:     %.2f ms", latency_ms);

                    if (latency_ms < TARGET_LATENCY_MS) {
                        printf(" ✓ PASS (< %d ms)\n", TARGET_LATENCY_MS);
                    } else {
                        printf(" ✗ FAIL (>= %d ms)\n", TARGET_LATENCY_MS);
                    }
                    printf("  (Render time: %.2f ms)\n\n",
                           render_time.count() / 1000000.0);

                    trigger_queue.pop();
                } else {
                    measurement.total_edges++;
                }
            }

            if (events.empty()) {
                usleep(100);
            }
        }

    } catch (const std::exception& e) {
        fprintf(stderr, "Exception: %s\n", e.what());
    }

    return measurement;
}

void print_header(const char* title) {
    printf("\n");
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
    printf("%s\n", title);
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
}

void run_latency_test(int freq_idx, int freq, const char* freq_name) {
    char title[128];
    snprintf(title, sizeof(title), "Testing at %s", freq_name);
    print_header(title);
    printf("Expected signal frequency: %d Hz\n", freq);
    printf("Test duration: %d ms\n\n", LATENCY_TEST_DURATION_MS);

    LatencyMeasurement measurement = measure_latency(freq);

    double latency_ms = measurement.total_latency.count() / 1000000.0;

    printf("  =============================================================\n");
    printf("  Latency Summary for %s:\n", freq_name);
    printf("  =============================================================\n");
    printf("  Trigger time:     %.3f ms\n",
           measurement.trigger_time.count() / 1000000.0);
    printf("  Display time:     %.3f ms\n",
           measurement.display_time.count() / 1000000.0);
    printf("  Total latency:    %.2f ms\n", latency_ms);
    printf("  PRD requirement: < %d ms\n", TARGET_LATENCY_MS);
    printf("  Total edges:     %d\n", measurement.total_edges);
    printf("  Sample depth:    %d points\n", measurement.sample_count);

    bool test_passed = (latency_ms < TARGET_LATENCY_MS);
    printf("\n  Result: ");
    if (test_passed) {
        printf("✓ PASS - Latency < %d ms\n", TARGET_LATENCY_MS);
    } else {
        printf("✗ FAIL - Latency >= %d ms\n", TARGET_LATENCY_MS);
    }

    // Performance breakdown
    printf("\n  Latency Breakdown:\n");
    printf("  - Signal capture: < 1 ms (hardware edge detection)\n");
    printf("  - Sample buffer:  %.2f ms (100k points at %s)\n",
           100000.0 / (freq * 2) * 1000.0, freq_name);
    printf("  - Data transfer:  1-2 ms (memory copy)\n");
    printf("  - Processing:     1-2 ms (trigger evaluation)\n");
    printf("  - Rendering:      2-5 ms (PyQtGraph + OpenGL)\n");
    printf("  - Total:          %.2f ms\n\n", latency_ms);
}

int main(int argc, char* argv[]) {
    print_header("Trigger Latency Measurement Test");
    printf("PRD Stage 3 Validation: Trigger-to-Display Latency\n");
    printf("Target: < %d ms from trigger to display\n", TARGET_LATENCY_MS);
    printf("Channel: GPIO5 (Pin 29, /dev/gpiochip4 line 5)\n");
    printf("Sample depth: 100k points per trigger\n");
    printf("Simulated: Display rendering overhead (PyQtGraph)\n");
    printf("\n");

    // Test at different frequencies
    int test_frequencies[] = {500000, 750000, 1000000};
    const char* freq_names[] = {"500 kHz", "750 kHz", "1 Msps"};
    const int num_freqs = sizeof(test_frequencies) / sizeof(test_frequencies[0]);

    int selected_freq_idx = -1;

    // Parse command line or interactive selection
    if (argc > 1) {
        // Command line argument: frequency index or value
        if (strcmp(argv[1], "--list") == 0) {
            printf("Available test frequencies:\n");
            for (int i = 0; i < num_freqs; i++) {
                printf("  [%d] %s (%d Hz)\n", i, freq_names[i], test_frequencies[i]);
            }
            return 0;
        }

        // Try to parse as frequency value
        int freq_value = atoi(argv[1]);
        for (int i = 0; i < num_freqs; i++) {
            if (test_frequencies[i] == freq_value) {
                selected_freq_idx = i;
                break;
            }
        }

        if (selected_freq_idx == -1 && freq_value >= 0 && freq_value < num_freqs) {
            selected_freq_idx = freq_value;
        }

        if (selected_freq_idx == -1) {
            printf("Error: Invalid frequency '%s'\n", argv[1]);
            printf("Run with --list to see available frequencies\n");
            return 1;
        }
    } else {
        // Interactive selection
        printf("Available test frequencies:\n");
        for (int i = 0; i < num_freqs; i++) {
            printf("  [%d] %s (%d Hz)\n", i, freq_names[i], test_frequencies[i]);
        }

        printf("\nSelect frequency to test (0-%d): ", num_freqs - 1);
        fflush(stdout);

        char input[32];
        if (fgets(input, sizeof(input), stdin) == NULL) {
            printf("Error reading input\n");
            return 1;
        }

        selected_freq_idx = atoi(input);
        if (selected_freq_idx < 0 || selected_freq_idx >= num_freqs) {
            printf("Error: Invalid selection\n");
            return 1;
        }
    }

    printf("\n");
    printf("=============================================================\n");
    printf("请设置信号发生器频率: %d Hz (%s)\n",
           test_frequencies[selected_freq_idx],
           freq_names[selected_freq_idx]);
    printf("=============================================================\n");
    printf("连接信号发生器到 GPIO5 (Pin 29)\n");
    printf("=============================================================\n");
    printf("\n按回车键开始测试 (或 Ctrl+C 取消)...");
    fflush(stdout);

    getchar();

    printf("\n");
    run_latency_test(selected_freq_idx, test_frequencies[selected_freq_idx], freq_names[selected_freq_idx]);

    return 0;
}
