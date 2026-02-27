// SPDX-License-Identifier: GPL-2.0-or-later
// Multi-channel high-frequency GPIO sampling test
// Tests 4 channels simultaneously at various frequencies (50-100 kHz)
// Based on PRD Stage 1 validation requirements

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <thread>
#include <vector>
#include <unistd.h>
#include <gpiod.hpp>

#define MAX_CHANNELS 4
#define SAMPLE_DURATION_SEC 1

using namespace gpiod;
using namespace std::chrono;

// Channel configuration
struct ChannelConfig {
    const char* chip_path;
    unsigned int line_offset;
    const char* gpio_name;
    int physical_pin;
};

// All GPIO pins on /dev/gpiochip4 (RP1 controller)
ChannelConfig channels[MAX_CHANNELS] = {
    {"/dev/gpiochip4", 5,  "GPIO5",  29},  // Channel 1
    {"/dev/gpiochip4", 6,  "GPIO6",  31},  // Channel 2
    {"/dev/gpiochip4", 4,  "GPIO4",   7},  // Channel 3
    {"/dev/gpiochip4", 7,  "GPIO7",  26}   // Channel 4
};

// Channel statistics
struct ChannelStats {
    int total_edges;
    int rising_edges;
    int falling_edges;
    double edge_rate;
    double measured_freq;
    int expected_edges;
    int lost_edges;
    double loss_percentage;
    bool capture_success;
};

// Test frequency configuration
struct TestFreq {
    int frequency_hz;
    const char* name;
};

TestFreq test_frequencies[] = {
    {10000,  "10 kHz (baseline)"},
    {50000,  "50 kHz"},
    {75000,  "75 kHz"},
    {100000, "100 kHz"}
};
const int num_test_frequencies = sizeof(test_frequencies) / sizeof(test_frequencies[0]);

// Capture data from a single channel
ChannelStats capture_channel(int channel_idx, int expected_freq_hz) {
    ChannelConfig& config = channels[channel_idx];
    ChannelStats stats = {0};

    try {
        chip gpio_chip(config.chip_path);
        line gpio_line = gpio_chip.get_line(config.line_offset);

        // Configure edge event detection
        line_request line_cfg;
        line_cfg.consumer = "multi-channel-test";
        line_cfg.request_type = line_request::EVENT_BOTH_EDGES;
        line_cfg.flags = 0;

        gpio_line.request(line_cfg);

        if (!gpio_line.is_requested()) {
            stats.capture_success = false;
            return stats;
        }

        // Capture events
        auto start_time = steady_clock::now();
        auto end_time = start_time + seconds(SAMPLE_DURATION_SEC);

        while (steady_clock::now() < end_time) {
            std::vector<line_event> events = gpio_line.event_read_multiple();

            for (const auto& event : events) {
                if (event.event_type == line_event::RISING_EDGE) {
                    stats.rising_edges++;
                } else if (event.event_type == line_event::FALLING_EDGE) {
                    stats.falling_edges++;
                }
                stats.total_edges++;
            }

            if (events.empty()) {
                usleep(100);
            }
        }

        // Calculate statistics
        auto actual_duration = steady_clock::now() - start_time;
        double elapsed_sec = duration_cast<microseconds>(actual_duration).count() / 1000000.0;

        stats.edge_rate = stats.total_edges / elapsed_sec;
        stats.measured_freq = stats.edge_rate / 2.0;
        stats.expected_edges = static_cast<int>(expected_freq_hz * 2 * elapsed_sec);
        stats.lost_edges = stats.expected_edges - stats.total_edges;
        stats.loss_percentage = (stats.lost_edges * 100.0) / stats.expected_edges;
        stats.capture_success = true;

    } catch (const std::exception& e) {
        fprintf(stderr, "Channel %d exception: %s\n", channel_idx + 1, e.what());
        stats.capture_success = false;
    }

    return stats;
}

// Print a section header
void print_header(const char* title) {
    printf("\n");
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
    printf("%s\n", title);
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
}

// Print channel results
void print_channel_results(int ch_idx, const ChannelStats& stats, int expected_freq) {
    ChannelConfig& config = channels[ch_idx];
    printf("\n  Channel %d (%s, Pin %d):\n", ch_idx + 1, config.gpio_name, config.physical_pin);

    if (!stats.capture_success) {
        printf("    ✗ Failed to capture\n");
        return;
    }

    printf("    Total edges: %d (Rising: %d, Falling: %d)\n",
           stats.total_edges, stats.rising_edges, stats.falling_edges);
    printf("    Measured: %.2f Hz (Expected: %d Hz)\n",
           stats.measured_freq, expected_freq);
    printf("    Edge loss: %d (%.2f%%)\n",
           stats.lost_edges, stats.loss_percentage);

    if (stats.loss_percentage < 1.0) {
        printf("    ✓ EXCELLENT (< 1%% loss)\n");
    } else if (stats.loss_percentage < 5.0) {
        printf("    ✓ GOOD (< 5%% loss)\n");
    } else if (stats.loss_percentage < 10.0) {
        printf("    ⚠ ACCEPTABLE (< 10%% loss)\n");
    } else {
        printf("    ✗ POOR (> 10%% loss)\n");
    }
}

int main(void) {
    print_header("Multi-Channel High-Frequency GPIO Sampling Test");
    printf("PRD Stage 1 Validation: 50-100 kHz range\n");
    printf("Chip: /dev/gpiochip4 (RP1 controller)\n");
    printf("Channels: 4 simultaneous (GPIO4/5/6/7)\n");
    printf("Duration: %d second per test\n", SAMPLE_DURATION_SEC);

    bool all_tests_passed = true;

    // Test each frequency
    for (int f = 0; f < num_test_frequencies; f++) {
        TestFreq& test_freq = test_frequencies[f];

        char title[128];
        snprintf(title, sizeof(title), "Testing at %s", test_freq.name);
        print_header(title);
        printf("Expected frequency: %d Hz\n", test_freq.frequency_hz);
        printf("Expected edges: %d per channel\n",
               test_freq.frequency_hz * 2 * SAMPLE_DURATION_SEC);

        // Capture from all channels simultaneously
        std::vector<ChannelStats> all_stats;
        std::vector<std::thread> threads;

        auto start_time = steady_clock::now();

        // Launch threads for all channels
        for (int ch = 0; ch < MAX_CHANNELS; ch++) {
            all_stats.push_back(ChannelStats());
            threads.push_back(std::thread([ch, test_freq, &all_stats]() {
                all_stats[ch] = capture_channel(ch, test_freq.frequency_hz);
            }));
        }

        // Wait for all threads to complete
        for (auto& t : threads) {
            t.join();
        }

        auto end_time = steady_clock::now();
        auto total_duration = duration_cast<milliseconds>(end_time - start_time);
        printf("\n  Total test time: %ld ms\n", total_duration.count());

        // Print results for each channel
        bool freq_test_passed = true;
        for (int ch = 0; ch < MAX_CHANNELS; ch++) {
            print_channel_results(ch, all_stats[ch], test_freq.frequency_hz);
            if (!stats.capture_success || all_stats[ch].loss_percentage > 5.0) {
                freq_test_passed = false;
                all_tests_passed = false;
            }
        }

        // Summary for this frequency
        printf("\n  Frequency Test Result: ");
        if (freq_test_passed) {
            printf("✓ PASS - All channels < 5%% edge loss\n");
        } else {
            printf("✗ FAIL - Some channels > 5%% edge loss\n");
        }
    }

    // Final summary
    print_header("Test Summary");

    printf("\nOverall Result: ");
    if (all_tests_passed) {
        printf("✓ ALL TESTS PASSED\n");
        printf("\n✓ libgpiod C++ with edge events meets PRD Stage 1 requirements\n");
        printf("  All 4 channels < 5%% edge loss at 50-100 kHz\n");
        printf("  Ready to proceed to Stage 2 (100-500 kHz)\n");
    } else {
        printf("✗ SOME TESTS FAILED\n");
        printf("\n⚠ Some channels exceed 5%% edge loss\n");
        printf("  Recommendations:\n");
        printf("  1. Check signal connections and quality\n");
        printf("  2. Reduce CPU load during test\n");
        printf("  3. Consider lowering target frequency\n");
        printf("  4. Proceed to Stage 2 with caution\n");
    }

    printf("\n");
    return all_tests_passed ? EXIT_SUCCESS : EXIT_FAILURE;
}
