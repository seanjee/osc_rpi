// SPDX-License-Identifier: GPL-2.0-or-later
// High-speed GPIO sampling using libgpiod
// Measures frequency of 10 kHz square wave signal
// Reference: https://forums.raspberrypi.com/viewtopic.php?t=383764

#include <errno.h>
#include <gpiod.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define SAMPLE_DURATION_SEC 1
#define EVENT_BUFFER_SIZE 1024

struct gpiod_line_request *setup_gpio_input(const char *chip_path,
                                       unsigned int offset,
                                       const char *consumer)
{
    struct gpiod_request_config *req_cfg = NULL;
    struct gpiod_line_request *request = NULL;
    struct gpiod_line_settings *settings;
    struct gpiod_line_config *line_cfg;
    struct gpiod_chip *chip;
    int ret;

    chip = gpiod_chip_open(chip_path);
    if (!chip) {
        fprintf(stderr, "Failed to open chip %s: %s\n",
                chip_path, strerror(errno));
        return NULL;
    }

    settings = gpiod_line_settings_new();
    if (!settings)
        goto close_chip;

    gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_INPUT);
    // Set edge detection for BOTH edges to capture all transitions
    gpiod_line_settings_set_edge_detection(settings, GPIOD_LINE_EDGE_BOTH);

    line_cfg = gpiod_line_config_new();
    if (!line_cfg)
        goto free_settings;

    ret = gpiod_line_config_add_line_settings(line_cfg, &offset, 1, settings);
    if (ret) {
        fprintf(stderr, "Failed to add line settings: %s\n", strerror(errno));
        goto free_line_config;
    }

    req_cfg = gpiod_request_config_new();
    if (!req_cfg)
        goto free_line_config;

    gpiod_request_config_set_consumer(req_cfg, consumer);

    request = gpiod_chip_request_lines(chip, req_cfg, line_cfg);
    if (!request) {
        fprintf(stderr, "Failed to request line: %s\n", strerror(errno));
        goto free_req_cfg;
    }

    gpiod_request_config_free(req_cfg);
    gpiod_line_config_free(line_cfg);
    gpiod_line_settings_free(settings);
    gpiod_chip_close(chip);

    return request;

free_req_cfg:
    gpiod_request_config_free(req_cfg);
free_line_config:
    gpiod_line_config_free(line_cfg);
free_settings:
    gpiod_line_settings_free(settings);
close_chip:
    gpiod_chip_close(chip);
    return NULL;
}

int main(void)
{
    // Configuration for RPi5: /dev/gpiochip4, line 5 = GPIO5 = Physical Pin 29
    static const char *const chip_path = "/dev/gpiochip4";
    static const unsigned int line_offset = 5;

    struct gpiod_edge_event_buffer *event_buffer;
    struct gpiod_line_request *request;
    struct gpiod_edge_event *event;
    int i, ret;
    int total_edges = 0;
    long long first_timestamp_ns = 0;
    long long last_timestamp_ns = 0;
    long long start_time_ns = 0;
    long long end_time_ns = 0;
    struct timespec ts;

    printf("=============================================================\n");
    printf("High-speed GPIO Sampling with libgpiod (C)\n");
    printf("=============================================================\n");
    printf("Chip: %s\n", chip_path);
    printf("Line: %d (GPIO5, Physical Pin 29)\n", line_offset);
    printf("Edge detection: BOTH (rising and falling)\n");
    printf("Sample duration: %d seconds\n", SAMPLE_DURATION_SEC);
    printf("=============================================================\n\n");

    // Setup GPIO line
    request = setup_gpio_input(chip_path, line_offset, "freq-measure-c");
    if (!request) {
        return EXIT_FAILURE;
    }

    // Create event buffer for efficient batch reading
    event_buffer = gpiod_edge_event_buffer_new(EVENT_BUFFER_SIZE);
    if (!event_buffer) {
        fprintf(stderr, "Failed to create event buffer: %s\n", strerror(errno));
        gpiod_line_request_release(request);
        return EXIT_FAILURE;
    }

    // Get start time
    clock_gettime(CLOCK_MONOTONIC, &ts);
    start_time_ns = ts.tv_sec * 1000000000LL + ts.tv_nsec;

    printf("Starting edge event capture...\n\n");

    // Capture events for specified duration
    int elapsed_ms = 0;
    while (elapsed_ms < SAMPLE_DURATION_SEC * 1000) {
        ret = gpiod_line_request_read_edge_events(request, event_buffer,
                                                EVENT_BUFFER_SIZE);
        if (ret == -1) {
            fprintf(stderr, "Error reading edge events: %s\n", strerror(errno));
            break;
        }

        // Process captured events
        for (i = 0; i < ret; i++) {
            event = gpiod_edge_event_buffer_get_event(event_buffer, i);

            // Get edge type
            enum gpiod_edge_event_type event_type =
                gpiod_edge_event_get_event_type(event);

            // Get timestamp in nanoseconds
            long long timestamp_ns = gpiod_edge_event_get_timestamp_ns(event);

            if (total_edges == 0) {
                first_timestamp_ns = timestamp_ns;
                printf("First edge detected at %.3f ms\n",
                       timestamp_ns / 1000000.0);
            }

            last_timestamp_ns = timestamp_ns;
            total_edges++;
        }

        // Check elapsed time
        clock_gettime(CLOCK_MONOTONIC, &ts);
        long long current_time_ns = ts.tv_sec * 1000000000LL + ts.tv_nsec;
        elapsed_ms = (current_time_ns - start_time_ns) / 1000000LL;
    }

    // Get end time
    clock_gettime(CLOCK_MONOTONIC, &ts);
    end_time_ns = ts.tv_sec * 1000000000LL + ts.tv_nsec;

    printf("\n=============================================================\n");
    printf("Results:\n");
    printf("=============================================================\n");
    printf("Total edges captured: %d\n", total_edges);
    printf("Expected edges (10kHz): %d\n", SAMPLE_DURATION_SEC * 20000);
    printf("Capture duration: %.3f seconds\n",
           (end_time_ns - start_time_ns) / 1000000000.0);
    printf("Average edge rate: %.2f edges/second\n",
           total_edges / ((end_time_ns - start_time_ns) / 1000000000.0));
    printf("Measured frequency: %.2f Hz\n",
           total_edges / ((end_time_ns - start_time_ns) / 1000000000.0) / 2.0);
    printf("Expected frequency: 10000 Hz\n");
    printf("Accuracy: %.2f%%\n",
           (total_edges / ((end_time_ns - start_time_ns) / 1000000000.0) / 2.0 / 10000.0 * 100.0);

    // Calculate edge loss
    int expected_edges = SAMPLE_DURATION_SEC * 20000; // 10kHz = 20000 edges/sec
    int lost_edges = expected_edges - total_edges;
    double loss_percentage = (lost_edges * 100.0) / expected_edges;
    printf("\nEdge loss analysis:\n");
    printf("  Expected edges: %d\n", expected_edges);
    printf("  Captured edges: %d\n", total_edges);
    printf("  Lost edges: %d (%.2f%%)\n", lost_edges, loss_percentage);

    if (loss_percentage < 1.0) {
        printf("\nResult: ✓ EXCELLENT - Less than 1%% edge loss\n");
    } else if (loss_percentage < 5.0) {
        printf("\nResult: ✓ GOOD - Less than 5%% edge loss\n");
    } else if (loss_percentage < 10.0) {
        printf("\nResult: ⚠ ACCEPTABLE - Less than 10%% edge loss\n");
    } else if (loss_percentage < 20.0) {
        printf("\nResult: ⚠ MARGINAL - 10-20%% edge loss\n");
    } else {
        printf("\nResult: ✗ POOR - More than 20%% edge loss\n");
    }

    // Cleanup
    gpiod_edge_event_buffer_free(event_buffer);
    gpiod_line_request_release(request);

    return (loss_percentage < 5.0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
