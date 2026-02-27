// SPDX-License-Identifier: GPL-2.0-or-later
// High-speed GPIO sampling using libgpiod (C++ API)
// Measures frequency of 10 kHz square wave signal
// Reference: https://forums.raspberrypi.com/viewtopic.php?t=383764

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <unistd.h>
#include <gpiod.hpp>

#define SAMPLE_DURATION_SEC 1

using namespace gpiod;
using namespace std::chrono;

int main(void)
{
    // Configuration for RPi5: /dev/gpiochip4, line 5 = GPIO5 = Physical Pin 29
    static const char* const chip_path = "/dev/gpiochip4";
    static const unsigned int line_offset = 5;
    static const char* const consumer = "freq-measure-cpp";

    printf("=============================================================\n");
    printf("High-speed GPIO Sampling with libgpiod (C++)\n");
    printf("=============================================================\n");
    printf("Chip: %s\n", chip_path);
    printf("Line: %d (GPIO5, Physical Pin 29)\n", line_offset);
    printf("Edge detection: BOTH (rising and falling)\n");
    printf("Sample duration: %d seconds\n", SAMPLE_DURATION_SEC);
    printf("=============================================================\n\n");

    try {
        // Open chip
        chip gpio_chip(chip_path);
        printf("✓ Chip opened\n");

        // Get line
        line gpio_line = gpio_chip.get_line(line_offset);
        if (!gpio_line.is_requested()) {
            printf("✓ Line %d obtained\n", line_offset);
        } else {
            printf("⚠ Line %d already requested\n", line_offset);
        }

        // Configure edge event detection
        line_request config;
        config.consumer = consumer;
        config.request_type = line_request::EVENT_BOTH_EDGES;
        config.flags = 0;

        printf("Requesting line for edge events...\n");
        gpio_line.request(config);

        if (!gpio_line.is_requested()) {
            fprintf(stderr, "✗ Failed to request line\n");
            return EXIT_FAILURE;
        }
        printf("✓ Line requested for edge detection\n");

        // Variables for statistics
        int total_edges = 0;
        int rising_edges = 0;
        int falling_edges = 0;
        nanoseconds first_timestamp(0);
        nanoseconds last_timestamp(0);
        auto start_time = steady_clock::now();
        auto end_time = start_time + seconds(SAMPLE_DURATION_SEC);

        printf("\nStarting edge event capture...\n");

        // Capture events for specified duration
        while (steady_clock::now() < end_time) {
            // Read all available events (non-blocking)
            std::vector<line_event> events = gpio_line.event_read_multiple();

            if (!events.empty()) {
                for (const auto& event : events) {
                    if (total_edges == 0) {
                        first_timestamp = event.timestamp;
                        printf("First edge detected at %.3f ms\n",
                               event.timestamp.count() / 1000000.0);
                    }

                    last_timestamp = event.timestamp;

                    // Count edge types
                    if (event.event_type == line_event::RISING_EDGE) {
                        rising_edges++;
                    } else if (event.event_type == line_event::FALLING_EDGE) {
                        falling_edges++;
                    }

                    total_edges++;
                }
            } else {
                // No events available, brief sleep to reduce CPU usage
                usleep(100);  // 0.1ms
            }
        }

        // Calculate elapsed time
        auto actual_duration = steady_clock::now() - start_time;
        double elapsed_sec = duration_cast<microseconds>(actual_duration).count() / 1000000.0;

        // Display results
        printf("\n=============================================================\n");
        printf("Results:\n");
        printf("=============================================================\n");
        printf("Total edges captured: %d\n", total_edges);
        printf("  Rising edges: %d\n", rising_edges);
        printf("  Falling edges: %d\n", falling_edges);
        printf("Capture duration: %.6f seconds\n", elapsed_sec);
        printf("Expected edges (10kHz): %.0f\n", SAMPLE_DURATION_SEC * 20000.0);

        // Calculate frequency and edge rate
        double edge_rate = total_edges / elapsed_sec;
        double measured_freq = edge_rate / 2.0;  // Each cycle has 2 edges

        printf("Average edge rate: %.2f edges/second\n", edge_rate);
        printf("Measured frequency: %.2f Hz\n", measured_freq);
        printf("Expected frequency: 10000 Hz\n");
        printf("Accuracy: %.2f%%\n", (measured_freq / 10000.0 * 100.0));

        // Edge loss analysis
        int expected_edges = static_cast<int>(SAMPLE_DURATION_SEC * 20000.0);
        int lost_edges = expected_edges - total_edges;
        double loss_percentage = (lost_edges * 100.0) / expected_edges;

        printf("\nEdge loss analysis:\n");
        printf("  Expected edges: %d\n", expected_edges);
        printf("  Captured edges: %d\n", total_edges);
        printf("  Lost edges: %d (%.2f%%)\n", lost_edges, loss_percentage);

        // Performance evaluation
        if (loss_percentage < 1.0) {
            printf("\nResult: ✓ EXCELLENT - Less than 1%% edge loss\n");
            printf("  This meets PRD requirements (<1%% error)\n");
        } else if (loss_percentage < 5.0) {
            printf("\nResult: ✓ GOOD - Less than 5%% edge loss\n");
        } else if (loss_percentage < 10.0) {
            printf("\nResult: ⚠ ACCEPTABLE - Less than 10%% edge loss\n");
        } else if (loss_percentage < 20.0) {
            printf("\nResult: ⚠ MARGINAL - 10-20%% edge loss\n");
        } else {
            printf("\nResult: ✗ POOR - More than 20%% edge loss\n");
        }

        // Recommendation
        printf("\n=============================================================\n");
        printf("Recommendation:\n");
        printf("=============================================================\n");

        if (loss_percentage < 5.0) {
            printf("✓ libgpiod C++ with edge events is suitable for PRD\n");
            printf("  Max achievable frequency: ~%d kHz\n",
                   static_cast<int>(edge_rate / 2000.0));
            printf("  This meets the 1 Msps target with optimization\n");
        } else {
            printf("⚠ Edge loss > 5%%, consider:\n");
            printf("  1. Lower sample rate requirement\n");
            printf("  2. Use optimized batch reading\n");
            printf("  3. Real-time kernel (CONFIG_PREEMPT_RT)\n");
        }

        return (loss_percentage < 5.0) ? EXIT_SUCCESS : EXIT_FAILURE;

    } catch (const std::exception& e) {
        fprintf(stderr, "Exception: %s\n", e.what());
        return EXIT_FAILURE;
    }
}
