#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "hardware/clocks.h"
#include "hardware/pio.h"
#include "hardware/regs/pio.h"
#include "pico/stdio_usb.h"
#include "pico/stdlib.h"
#include "loopback.pio.h"

#ifndef NESPICO_PIN_A_OUT
#define NESPICO_PIN_A_OUT 2
#endif
#ifndef NESPICO_PIN_A_IN
#define NESPICO_PIN_A_IN 3
#endif
#ifndef NESPICO_PIN_A_STROBE
#define NESPICO_PIN_A_STROBE 4
#endif
#ifndef NESPICO_PIN_B_OUT
#define NESPICO_PIN_B_OUT 6
#endif
#ifndef NESPICO_PIN_B_IN
#define NESPICO_PIN_B_IN 7
#endif
#ifndef NESPICO_PIN_B_STROBE
#define NESPICO_PIN_B_STROBE 8
#endif

#define TEST_WORDS 4096u
#define FIFO_DEPTH 4u
#define PIO_CLOCKS_PER_WORD 99u
#define PIO_SM_A 0u
#define PIO_SM_B 1u
#define NESPICO_PIO pio0

// RP2350 FDEBUG field positions differ from RP2040: use this SDK's register
// definitions rather than hard-coding the older field layout.
#define FDEBUG_TXSTALL(sm) (1u << (PIO_FDEBUG_TXSTALL_LSB + (sm)))
#define FDEBUG_RXSTALL(sm) (1u << (PIO_FDEBUG_RXSTALL_LSB + (sm)))

typedef struct {
    uint sm;
    uint out_pin;
    uint in_pin;
    uint strobe_pin;
} lane_t;

static const lane_t lane_a = {
    .sm = PIO_SM_A,
    .out_pin = NESPICO_PIN_A_OUT,
    .in_pin = NESPICO_PIN_A_IN,
    .strobe_pin = NESPICO_PIN_A_STROBE,
};

static const lane_t lane_b = {
    .sm = PIO_SM_B,
    .out_pin = NESPICO_PIN_B_OUT,
    .in_pin = NESPICO_PIN_B_IN,
    .strobe_pin = NESPICO_PIN_B_STROBE,
};

static uint32_t test_word(uint32_t lane, uint32_t index) {
    uint32_t x = (index * 0x9e3779b9u) ^ (lane ? 0xa55a1234u : 0x5aa5edcbu);
    x ^= x >> 16;
    x *= 0x7feb352du;
    x ^= x >> 15;
    return x;
}

static void configure_lane(PIO pio, uint program_offset, const lane_t *lane) {
    pio_sm_config config = loopback_program_get_default_config(program_offset);
    sm_config_set_out_pins(&config, lane->out_pin, 1);
    sm_config_set_in_pins(&config, lane->in_pin);
    sm_config_set_sideset_pins(&config, lane->strobe_pin);
    sm_config_set_out_shift(&config, true, false, 32);
    sm_config_set_in_shift(&config, true, false, 32);
    sm_config_set_fifo_join(&config, PIO_FIFO_JOIN_NONE);
    sm_config_set_clkdiv(&config, 1.0f);

    // Loopback is a low-voltage, isolated GPIO test; no cartridge pin is used.
    pio_gpio_init(pio, lane->out_pin);
    pio_gpio_init(pio, lane->in_pin);
    pio_gpio_init(pio, lane->strobe_pin);
    gpio_pull_down(lane->in_pin);

    pio_sm_init(pio, lane->sm, program_offset, &config);
    pio_sm_set_consecutive_pindirs(pio, lane->sm, lane->out_pin, 1, true);
    pio_sm_set_consecutive_pindirs(pio, lane->sm, lane->strobe_pin, 1, true);
    pio_sm_set_consecutive_pindirs(pio, lane->sm, lane->in_pin, 1, false);
    pio_sm_set_pins_with_mask(pio, lane->sm, 0u,
                              (1u << lane->out_pin) | (1u << lane->strobe_pin));
}

static bool run_round(uint round) {
    PIO pio = NESPICO_PIO;
    const uint32_t mask = (1u << lane_a.sm) | (1u << lane_b.sm);
    bool pass = true;
    uint32_t mismatches = 0;
    uint32_t first_expected = 0;
    uint32_t first_actual = 0;
    char first_lane = '?';
    bool first_mismatch_recorded = false;

    // Clear sticky stall indicators immediately before synchronized start.
    pio->fdebug = FDEBUG_TXSTALL(lane_a.sm) | FDEBUG_RXSTALL(lane_a.sm) |
                  FDEBUG_TXSTALL(lane_b.sm) | FDEBUG_RXSTALL(lane_b.sm);

    for (uint32_t i = 0; i < FIFO_DEPTH; ++i) {
        pio_sm_put_blocking(pio, lane_a.sm, test_word(0, i + round * TEST_WORDS));
        pio_sm_put_blocking(pio, lane_b.sm, test_word(1, i + round * TEST_WORDS));
    }

    uint32_t start_us = time_us_32();
    pio_enable_sm_mask_in_sync(pio, mask);

    for (uint32_t i = 0; i < TEST_WORDS; ++i) {
        uint32_t expected_a = test_word(0, i + round * TEST_WORDS);
        uint32_t expected_b = test_word(1, i + round * TEST_WORDS);
        uint32_t actual_a = pio_sm_get_blocking(pio, lane_a.sm);
        uint32_t actual_b = pio_sm_get_blocking(pio, lane_b.sm);

        if (actual_a != expected_a) {
            if (!first_mismatch_recorded) {
                first_expected = expected_a;
                first_actual = actual_a;
                first_lane = 'A';
                first_mismatch_recorded = true;
            }
            ++mismatches;
        }
        if (actual_b != expected_b) {
            if (!first_mismatch_recorded) {
                first_expected = expected_b;
                first_actual = actual_b;
                first_lane = 'B';
                first_mismatch_recorded = true;
            }
            ++mismatches;
        }

        if (i + FIFO_DEPTH < TEST_WORDS) {
            uint32_t next = i + FIFO_DEPTH + round * TEST_WORDS;
            pio_sm_put_blocking(pio, lane_a.sm, test_word(0, next));
            pio_sm_put_blocking(pio, lane_b.sm, test_word(1, next));
        }

        if (stdio_usb_connected() && ((i + 1u) % 1024u == 0u)) {
            printf("round=%u progress=%lu/%u\n", round,
                   (unsigned long)(i + 1u), TEST_WORDS);
        }
    }

    uint32_t elapsed_us = time_us_32() - start_us;
    pio_sm_set_enabled(pio, lane_a.sm, false);
    pio_sm_set_enabled(pio, lane_b.sm, false);

    uint32_t fdebug = pio->fdebug;
    bool tx_stall_a = (fdebug & FDEBUG_TXSTALL(lane_a.sm)) != 0;
    bool tx_stall_b = (fdebug & FDEBUG_TXSTALL(lane_b.sm)) != 0;
    bool rx_stall_a = (fdebug & FDEBUG_RXSTALL(lane_a.sm)) != 0;
    bool rx_stall_b = (fdebug & FDEBUG_RXSTALL(lane_b.sm)) != 0;

    pass = mismatches == 0 && !tx_stall_a && !tx_stall_b && !rx_stall_a && !rx_stall_b;
    printf("round=%u result=%s words_per_lane=%u elapsed_us=%lu "
           "pio_clocks_per_word=%u sys_hz=%lu usb_connected=%u "
           "txstall_a=%u txstall_b=%u rxstall_a=%u rxstall_b=%u mismatches=%lu\n",
           round, pass ? "PASS" : "FAIL", TEST_WORDS,
           (unsigned long)elapsed_us, PIO_CLOCKS_PER_WORD,
           (unsigned long)clock_get_hz(clk_sys), stdio_usb_connected() ? 1u : 0u,
           tx_stall_a ? 1u : 0u, tx_stall_b ? 1u : 0u,
           rx_stall_a ? 1u : 0u, rx_stall_b ? 1u : 0u,
           (unsigned long)mismatches);
    if (mismatches != 0) {
        printf("first mismatch lane=%c expected=%08lx actual=%08lx\n", first_lane,
               (unsigned long)first_expected, (unsigned long)first_actual);
    }
    return pass;
}

int main(void) {
    stdio_init_all();
    sleep_ms(1500);
    printf("NESPICO RP2350 dual-lane PIO loopback bring-up\n");
    printf("Connect only GPIO%u->GPIO%u and GPIO%u->GPIO%u; keep cartridge disconnected.\n",
           lane_a.out_pin, lane_a.in_pin, lane_b.out_pin, lane_b.in_pin);
    printf("PIO program: 99 instruction cycles per 32-bit word, excluding FIFO stalls.\n");

    PIO pio = NESPICO_PIO;
    uint program_offset = pio_add_program(pio, &loopback_program);
    configure_lane(pio, program_offset, &lane_a);
    configure_lane(pio, program_offset, &lane_b);

    for (uint round = 0; ; ++round) {
        bool pass = run_round(round);
        if (!pass) {
            printf("Check the two jumpers, GPIO mapping, and input/output orientation.\n");
        }
        sleep_ms(250);
    }
}
