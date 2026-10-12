cmake_minimum_required(VERSION 3.13)

if(NOT PICO_SDK_PATH)
    set(PICO_SDK_PATH "$ENV{PICO_SDK_PATH}" CACHE PATH "Path to raspberrypi/pico-sdk")
endif()
if(NOT EXISTS "${PICO_SDK_PATH}/external/pico_sdk_import.cmake")
    message(FATAL_ERROR "Set PICO_SDK_PATH to a Pico SDK checkout (tested with 2.3.1).")
endif()

include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(nespico_pio_bringup C CXX ASM)
pico_sdk_init()

set(NESPICO_PIN_A_OUT 2 CACHE STRING "GPIO for loopback lane A output")
set(NESPICO_PIN_A_IN 3 CACHE STRING "GPIO for loopback lane A input")
set(NESPICO_PIN_A_STROBE 4 CACHE STRING "GPIO for loopback lane A sample strobe")
set(NESPICO_PIN_B_OUT 6 CACHE STRING "GPIO for loopback lane B output")
set(NESPICO_PIN_B_IN 7 CACHE STRING "GPIO for loopback lane B input")
set(NESPICO_PIN_B_STROBE 8 CACHE STRING "GPIO for loopback lane B sample strobe")

add_executable(nespico_pio_bringup
    main.c
)

pico_generate_pio_header(nespico_pio_bringup
    ${CMAKE_CURRENT_LIST_DIR}/pio/loopback.pio
)

target_compile_definitions(nespico_pio_bringup PRIVATE
    NESPICO_PIN_A_OUT=${NESPICO_PIN_A_OUT}
    NESPICO_PIN_A_IN=${NESPICO_PIN_A_IN}
    NESPICO_PIN_A_STROBE=${NESPICO_PIN_A_STROBE}
    NESPICO_PIN_B_OUT=${NESPICO_PIN_B_OUT}
    NESPICO_PIN_B_IN=${NESPICO_PIN_B_IN}
    NESPICO_PIN_B_STROBE=${NESPICO_PIN_B_STROBE}
)

target_link_libraries(nespico_pio_bringup PRIVATE
    pico_stdlib
    hardware_clocks
    hardware_pio
)

pico_enable_stdio_usb(nespico_pio_bringup 1)
pico_enable_stdio_uart(nespico_pio_bringup 0)
pico_add_extra_outputs(nespico_pio_bringup)
