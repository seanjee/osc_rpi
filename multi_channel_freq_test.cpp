// SPDX-License-Identifier: GPL-2.0-or-later
// Multi-channel high-frequency GPIO sampling test
// Tests 4 channels simultaneously at various frequencies (50-100 kHz)
// Based on PRD Stage 1 validation requirements
//
// 测试条件说明：
// - 所有4个通道连接到同一信号源（信号发生器）
// - 所有通道测试相同频率，请从外部信号发生器设置
// - 通道连接：GPIO5(Pin29), GPIO6(Pin31), GPIO23(Pin16), GPIO24(Pin18)
// - 测试频率：10 kHz (baseline), 50 kHz, 75 kHz, 100 kHz

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
    {"/dev/gpiochip4", 23, "GPIO23", 16},  // Channel 3
    {"/dev/gpiochip4", 24, "GPIO24", 18}   // Channel 4
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
    {20000,  "20 kHz"},
    {30000,  "30 kHz"},
    {35000,  "35 kHz"},
    {40000,  "40 kHz"},
    {45000,  "45 kHz"},
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

void run_test(int freq_idx) {
    TestFreq& test_freq = test_frequencies[freq_idx];

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
        if (!all_stats[ch].capture_success || all_stats[ch].loss_percentage > 5.0) {
            freq_test_passed = false;
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

int main(int argc, char* argv[]) {
    print_header("Multi-Channel High-Frequency GPIO Sampling Test");
    printf("PRD Stage 1 Validation: 10-100 kHz frequency boundary\n");
    printf("Status: 10-30 kHz PASS, 40 kHz FAIL (CH3: 10.78%% loss)\n");
    printf("Issue: CH3 (GPIO23) underperforms other channels\n");
    printf("Chip: /dev/gpiochip4 (RP1 controller)\n");
    printf("Channels: 4 simultaneous (GPIO5/6/23/24)\n");
    printf("Duration: %d second per test\n", SAMPLE_DURATION_SEC);
    printf("\n");

    int selected_freq_idx = -1;

    // Parse command line or interactive selection
    if (argc > 1) {
        // Command line argument: frequency index or value
        if (strcmp(argv[1], "--list") == 0) {
            printf("Available test frequencies:\n");
            for (int i = 0; i < num_test_frequencies; i++) {
                printf("  [%d] %s (%d Hz)\n", i, test_frequencies[i].name, test_frequencies[i].frequency_hz);
            }
            return 0;
        }

        // Try to parse as frequency value
        int freq_value = atoi(argv[1]);
        for (int i = 0; i < num_test_frequencies; i++) {
            if (test_frequencies[i].frequency_hz == freq_value) {
                selected_freq_idx = i;
                break;
            }
        }

        if (selected_freq_idx == -1 && freq_value >= 0 && freq_value < num_test_frequencies) {
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
        for (int i = 0; i < num_test_frequencies; i++) {
            printf("  [%d] %s (%d Hz)\n", i, test_frequencies[i].name, test_frequencies[i].frequency_hz);
        }

        printf("\nSelect frequency to test (0-%d): ", num_test_frequencies - 1);
        fflush(stdout);

        char input[32];
        if (fgets(input, sizeof(input), stdin) == NULL) {
            printf("Error reading input\n");
            return 1;
        }

        selected_freq_idx = atoi(input);
        if (selected_freq_idx < 0 || selected_freq_idx >= num_test_frequencies) {
            printf("Error: Invalid selection\n");
            return 1;
        }
    }

    printf("\n");
    printf("=============================================================\n");
    printf("请设置信号发生器频率: %d Hz (%s)\n",
           test_frequencies[selected_freq_idx].frequency_hz,
           test_frequencies[selected_freq_idx].name);
    printf("=============================================================\n");
    printf("所有4个通道连接到同一信号源:\n");
    printf("  - GPIO5 (Pin 29)  通道1\n");
    printf("  - GPIO6 (Pin 31)  通道2\n");
    printf("  - GPIO23 (Pin 16) 通道3\n");
    printf("  - GPIO24 (Pin 18) 通道4\n");
    printf("=============================================================\n");
    printf("\n按回车键开始测试 (或 Ctrl+C 取消)...");
    fflush(stdout);

    getchar();

    printf("\n");
    run_test(selected_freq_idx);

    return 0;
}
