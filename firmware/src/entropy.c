/* entropy.c */

#include "drbg.h"
#include "entropy.h"
#include "event.h"
#include "uart.h"

#define ENTROPY_PER_SAMPLE 4

/* Defined on page 35 of ANS X9.82 as ceil(1 + (-log_2(W)) / H)
   Where W is the acceptable false positive rate (2^30 by default) and H is
   the entropy per sample.
   This is pre-computed, and needs to be changed whenever ENTROPY_PER_SAMPLE
   is changed.
*/
#define ENTROPY_MAX_REPETITIONS 8

#define ENTROPY_WINDOW 16
/* The following value is from the table on page 39, indexed by entropy per
   sample and window size.
*/
#define ENTROPY_ADAPTIVE_CUTOFF 8

/* This represents a number of samples that should be read, to have a
   reasonably high chance that the run-time entropy tests will fail. This
   depends on the window size, percent of entropy lost, and desired probability
   of detecting the problem, if calculated. Here, it's simply asserted as a
   value that will cause the test to be run numerous times, catching any
   catastrophic loss of entropy with rather high probability.
*/
#define ENTROPY_FAILURE_DETECT_SAMPLES 1024

typedef struct {
    uint32_t entropy_sample;
    uint32_t entropy_previous_sample;
    uint32_t entropy_adaptive_sample;
    uint16_t entropy_failures;
    uint8_t entropy_adaptive_seen;
    uint8_t entropy_adaptive_sample_count;
    uint8_t entropy_repetitions;
    bool entropy_available;
} entropy_t;

entropy_t entropy = {
        .entropy_sample = 0,
        .entropy_previous_sample = 0,
        .entropy_adaptive_sample = 0,
        .entropy_failures = 0,
        .entropy_adaptive_seen = 0,
        .entropy_adaptive_sample_count = 0,
        .entropy_repetitions = 1,
        .entropy_available = 0,
};

int32_t entropy_per_sample(void) {
    return ENTROPY_PER_SAMPLE;
}

/* The magical numbers other than entropy_per_sample are fairly arbitrary.
   The return value of this is "enough" entropy samples. */
int32_t entropy_samples_til_ready(void) {
    int32_t eps = 512 / ENTROPY_PER_SAMPLE;
    int32_t efds = ENTROPY_FAILURE_DETECT_SAMPLES;
    return eps > efds ? eps : efds;
}

void entropy_register(uint32_t entropy_sample) {
    entropy.entropy_sample = entropy_sample;
    entropy.entropy_available = 1;
}

void entropy_test_failed(void) {
    event_log(EVENT_ENTROPY_FAIL);
    entropy.entropy_failures++;
    drbg_error();
}

void entropy_repetition_test(void) {
    if (entropy.entropy_previous_sample == entropy.entropy_sample) {
        entropy.entropy_repetitions += 1;
    } else {
        entropy.entropy_previous_sample = entropy.entropy_sample;
        entropy.entropy_repetitions = 1;
    }

    if (entropy.entropy_repetitions >= ENTROPY_MAX_REPETITIONS) {
        entropy_test_failed();
    }
}

void entropy_adaptive_test(void) {
    if (!entropy.entropy_adaptive_sample_count) {
        entropy.entropy_adaptive_sample = entropy.entropy_sample;
        entropy.entropy_adaptive_sample_count = 1;
        entropy.entropy_adaptive_seen = 1;
        return;
    }

    if (entropy.entropy_sample == entropy.entropy_adaptive_sample) {
        entropy.entropy_adaptive_seen++;
        if (entropy.entropy_adaptive_seen == ENTROPY_ADAPTIVE_CUTOFF) {
            entropy_test_failed();
            entropy.entropy_adaptive_sample_count = 0;
        }
    }
    entropy.entropy_adaptive_sample_count++;

    if (entropy.entropy_adaptive_sample_count == ENTROPY_WINDOW) {
        entropy.entropy_adaptive_sample_count = 0;
        return;
    }
}

void entropy_poll(void) {
    if (!entropy.entropy_available)
        return;

    entropy_repetition_test();
    entropy_adaptive_test();
    drbg_update(entropy.entropy_sample);
    entropy.entropy_available = 0;
}
