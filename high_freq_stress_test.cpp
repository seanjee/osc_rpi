// SPDX-License-Identifier: GPL-2.0-or-later
// High-frequency stress test for GPIO sampling
// Tests stability and performance at 100-500 kHz with memory monitoring
// PRD Stage 2 validation
//
// 测试条件说明：
// - 所有4个通道连接到同一信号源（信号发生器）
// - 所有通道测试相同频率，请从外部信号发生器设置
// - 通道连接：GPIO5(Pin29), GPIO6(Pin31), GPIO23(Pin16), GPIO24(Pin18)
// - 测试频率：100 kHz, 200 kHz, 500 kHz（每个频率测试60秒）

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <sys/resource.h>
#include <sys/sysinfo.h>
#include <thread>
#include <unistd.h>
#include <gpiod.hpp>

#define MAX_CHANNELS 4
#define STRESS_TEST_DURATION_SEC 60  // 1 minute per frequency

using namespace gpiod;
using namespace std::chrono;

// Channel configuration
struct ChannelConfig {
    const char* chip_path;
    unsigned int line_offset;
    const char* gpio_name;
};

ChannelConfig channels[MAX_CHANNELS] = {
    {"/dev/gpiochip4", 5,  "GPIO5"},  // Channel 1
    {"/dev/gpiochip4", 6,  "GPIO6"},  // Channel 2
    {"/dev/gpiochip4", 23, "GPIO23"}, // Channel 3
    {"/dev/gpiochip4", 24, "GPIO24"}  // Channel 4
};

// System resource monitoring
struct SystemResources {
    double cpu_usage_percent;
    double memory_usage_mb;
    double memory_percent;
    long page_faults;
    long context_switches;
};

// Performance statistics
struct PerformanceStats {
    double avg_edge_rate;
    double max_edge_rate;
    double min_edge_rate;
    double edge_loss_avg;
    double cpu_usage_avg;
    double memory_avg;
    int total_edges;
    int total_samples;
};

// Get CPU usage percentage
double get_cpu_usage() {
    static unsigned long long prev_idle = 0, prev_total = 0;
    FILE* fp = fopen("/proc/stat", "r");
    if (!fp) return 0.0;

    unsigned long long user, nice, system, idle, iowait, irq, softirq, steal;
    fscanf(fp, "cpu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
           &user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal, &idle);
    fclose(fp);

    unsigned long long total = user + nice + system + idle + iowait + irq + softirq + steal;
    unsigned long long total_diff = total - prev_total;
    unsigned long long idle_diff = idle - prev_idle;

    prev_total = total;
    prev_idle = idle;

    if (total_diff == 0) return 0.0;
    return 100.0 * (1.0 - (double)idle_diff / total_diff);
}

// Get memory usage
SystemResources get_system_resources() {
    SystemResources res = {0};
    struct rusage usage;
    struct sysinfo info;

    getrusage(RUSAGE_SELF, &usage);
    sysinfo(&info);

    res.memory_usage_mb = usage.ru_maxrss / 1024.0;  // Convert to MB
    res.memory_percent = (res.memory_usage_mb / (info.totalram / 1024.0 / 1024.0)) * 100.0;
    res.page_faults = usage.ru_majflt;
    res.context_switches = usage.ru_nvcsw + usage.ru_nivcsw;
    res.cpu_usage_percent = get_cpu_usage();

    return res;
}

// Capture from a single channel for a duration
PerformanceStats capture_channel_stress(int channel_idx, int expected_freq_hz, int duration_sec) {
    ChannelConfig& config = channels[channel_idx];
    PerformanceStats stats = {0};

    std::vector<double> edge_rates;
    std::vector<double> edge_losses;
    std::vector<double> cpu_usages;
    std::vector<double> memory_usages;

    try {
        chip gpio_chip(config.chip_path);
        line gpio_line = gpio_chip.get_line(config.line_offset);

        line_request line_cfg;
        line_cfg.consumer = "stress-test";
        line_cfg.request_type = line_request::EVENT_BOTH_EDGES;
        line_cfg.flags = 0;

        gpio_line.request(line_cfg);

        if (!gpio_line.is_requested()) {
            return stats;
        }

        // Sampling intervals
        auto start_time = steady_clock::now();
        auto end_time = start_time + seconds(duration_sec);
        auto sample_interval = milliseconds(100);  // Sample every 100ms
        auto next_sample = start_time + sample_interval;

        int edges_this_sample = 0;
        int sample_count = 0;

        while (steady_clock::now() < end_time) {
            std::vector<line_event> events = gpio_line.event_read_multiple();

            for (const auto& event : events) {
                stats.total_edges++;
                edges_this_sample++;
            }

            // Sample performance metrics
            if (steady_clock::now() >= next_sample) {
                auto interval_end = steady_clock::now();
                auto interval_duration = duration_cast<milliseconds>(interval_end - start_time);
                double elapsed_sec = interval_duration.count() / 1000.0;

                double edge_rate = edges_this_sample / 0.1;  // edges per second in last 100ms
                edge_rates.push_back(edge_rate);

                int expected_edges_in_interval = static_cast<int>(expected_freq_hz * 2 * 0.1);
                double loss = (expected_edges_in_interval - edges_this_sample) * 100.0 / expected_edges_in_interval;
                edge_losses.push_back(loss);

                SystemResources res = get_system_resources();
                cpu_usages.push_back(res.cpu_usage_percent);
                memory_usages.push_back(res.memory_usage_mb);

                edges_this_sample = 0;
                sample_count++;
                next_sample += sample_interval;

                // Print progress
                if (sample_count % 10 == 0) {
                    printf("\r  Progress: %d/%d samples (%.1f%%) - Edge rate: %.0f/s",
                           sample_count, duration_sec * 10,
                           100.0 * sample_count / (duration_sec * 10),
                           edge_rate);
                    fflush(stdout);
                }
            }

            if (events.empty()) {
                usleep(100);
            }
        }

        printf("\n");  // New line after progress

        // Calculate statistics
        stats.total_samples = sample_count;

        if (!edge_rates.empty()) {
            stats.max_edge_rate = *std::max_element(edge_rates.begin(), edge_rates.end());
            stats.min_edge_rate = *std::min_element(edge_rates.begin(), edge_rates.end());

            double sum = std::accumulate(edge_rates.begin(), edge_rates.end(), 0.0);
            stats.avg_edge_rate = sum / edge_rates.size();
        }

        if (!edge_losses.empty()) {
            double sum = std::accumulate(edge_losses.begin(), edge_losses.end(), 0.0);
            stats.edge_loss_avg = sum / edge_losses.size();
        }

        if (!cpu_usages.empty()) {
            double sum = std::accumulate(cpu_usages.begin(), cpu_usages.end(), 0.0);
            stats.cpu_usage_avg = sum / cpu_usages.size();
        }

        if (!memory_usages.empty()) {
            double sum = std::accumulate(memory_usages.begin(), memory_usages.end(), 0.0);
            stats.memory_avg = sum / memory_usages.size();
        }

    } catch (const std::exception& e) {
        fprintf(stderr, "Channel %d exception: %s\n", channel_idx + 1, e.what());
    }

    return stats;
}

void print_header(const char* title) {
    printf("\n");
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
    printf("%s\n", title);
    for (int i = 0; i < 70; i++) printf("=");
    printf("\n");
}

void print_performance_results(int ch_idx, const PerformanceStats& stats, int expected_freq) {
    ChannelConfig& config = channels[ch_idx];

    printf("\n  Channel %d (%s):\n", ch_idx + 1, config.gpio_name);
    printf("    Total edges: %d\n", stats.total_edges);
    printf("    Total samples: %d\n", stats.total_samples);
    printf("    Expected edge rate: %.0f edges/s\n", expected_freq * 2.0);
    printf("    Average edge rate: %.0f edges/s\n", stats.avg_edge_rate);
    printf("    Edge rate range: %.0f - %.0f edges/s\n", stats.min_edge_rate, stats.max_edge_rate);
    printf("    Average edge loss: %.2f%%\n", stats.edge_loss_avg);
    printf("    Average CPU usage: %.1f%%\n", stats.cpu_usage_avg);
    printf("    Average memory: %.2f MB\n", stats.memory_avg);

    // Stability check
    double rate_variation = (stats.max_edge_rate - stats.min_edge_rate) / stats.avg_edge_rate * 100.0;
    printf("    Edge rate variation: %.2f%%\n", rate_variation);

    if (stats.edge_loss_avg < 10.0 && stats.cpu_usage_avg < 90.0 && rate_variation < 20.0) {
        printf("    ✓ STABLE - Meets Stage 2 criteria\n");
    } else if (stats.edge_loss_avg < 15.0 && stats.cpu_usage_avg <= 90.0) {
        printf("    ⚠ MARGINAL - Approaching limits\n");
    } else {
        printf("    ✗ UNSTABLE - Exceeds Stage 2 criteria\n");
    }
}

void run_stress_test(int freq_idx, int freq, const char* freq_name) {
    char title[128];
    snprintf(title, sizeof(title), "Stress Testing at %s", freq_name);
    print_header(title);
    printf("Expected frequency: %d Hz\n", freq);
    printf("Test duration: %d seconds\n", STRESS_TEST_DURATION_SEC);

    std::vector<PerformanceStats> all_stats;
    std::vector<std::thread> threads;

    auto start_time = steady_clock::now();

    // Launch all channels
    for (int ch = 0; ch < MAX_CHANNELS; ch++) {
        all_stats.push_back(PerformanceStats());
        threads.push_back(std::thread([ch, freq, &all_stats]() {
            all_stats[ch] = capture_channel_stress(ch, freq, STRESS_TEST_DURATION_SEC);
        }));
    }

    // Wait for all threads
    for (auto& t : threads) {
        t.join();
    }

    auto end_time = steady_clock::now();
    auto total_duration = duration_cast<seconds>(end_time - start_time);
    printf("\n  Total test time: %ld seconds\n", total_duration.count());

    // Print results
    bool freq_test_passed = true;
    for (int ch = 0; ch < MAX_CHANNELS; ch++) {
        print_performance_results(ch, all_stats[ch], freq);

        if (all_stats[ch].edge_loss_avg > 10.0 ||
            all_stats[ch].cpu_usage_avg > 90.0) {
            freq_test_passed = false;
        }
    }

    printf("\n  Stress Test Result: ");
    if (freq_test_passed) {
        printf("✓ PASS - All channels meet Stage 2 criteria\n");
    } else {
        printf("✗ FAIL - Some channels exceed Stage 2 criteria\n");
    }
}

int main(int argc, char* argv[]) {
    print_header("High-Frequency Stress Test");
    printf("PRD Stage 2 Validation: 100-500 kHz range\n");
    printf("Duration: %d seconds per frequency\n", STRESS_TEST_DURATION_SEC);
    printf("Metrics: Edge loss, CPU usage, Memory, Stability\n");
    printf("\n");

    // Test frequencies for Stage 2
    int test_frequencies[] = {100000, 200000, 500000};
    const char* freq_names[] = {"100 kHz", "200 kHz", "500 kHz"};
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
    printf("所有4个通道连接到同一信号源:\n");
    printf("  - GPIO5  通道1\n");
    printf("  - GPIO6  通道2\n");
    printf("  - GPIO23 通道3\n");
    printf("  - GPIO24 通道4\n");
    printf("=============================================================\n");
    printf("\n按回车键开始测试 (或 Ctrl+C 取消)...");
    fflush(stdout);

    getchar();

    printf("\n");
    run_stress_test(selected_freq_idx, test_frequencies[selected_freq_idx], freq_names[selected_freq_idx]);

    return 0;
}
