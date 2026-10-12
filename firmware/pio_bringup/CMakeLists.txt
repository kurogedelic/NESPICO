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

# The fixture targets the standard, non-wireless Raspberry Pi Pico 2. Permit
# only header GPIOs; GPIO23/24/25/29 are used by on-board functions. GPIO26-28
# (ADC0-ADC2) are permitted here only for the isolated 3.3 V test fixture. The
# NESPICO board design reserves them for analog inputs; this check does not
# establish product pin allocation or external electrical safety.
set(_nespico_pico2_header_gpios
    0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 26 27 28
)
set(_nespico_pin_names
    NESPICO_PIN_A_OUT
    NESPICO_PIN_A_IN
    NESPICO_PIN_A_STROBE
    NESPICO_PIN_B_OUT
    NESPICO_PIN_B_IN
    NESPICO_PIN_B_STROBE
)
set(_nespico_assigned_pins)
foreach(_pin_name IN LISTS _nespico_pin_names)
    set(_pin_value "${${_pin_name}}")
    if(NOT "${_pin_value}" MATCHES "^[0-9]+$")
        message(FATAL_ERROR "${_pin_name} must be an integer GPIO number; got '${_pin_value}'.")
    endif()
    if("${_pin_value}" MATCHES "^0[0-9]+$")
        message(FATAL_ERROR "${_pin_name} must not use leading zeros; use canonical decimal GPIO notation.")
    endif()
    if(_pin_value LESS 0 OR _pin_value GREATER 29)
        message(FATAL_ERROR "${_pin_name}=${_pin_value} is outside the RP2350 GPIO range 0..29.")
    endif()
    if(NOT _pin_value IN_LIST _nespico_pico2_header_gpios)
        message(FATAL_ERROR
            "${_pin_name}=${_pin_value} is not a Raspberry Pi Pico 2 header GPIO. "
            "Use GP0..GP22 or GP26..GP28; GP23/24/25/29 are reserved for on-board functions. "
            "GP26..GP28 are ADC-capable and require input-voltage care."
        )
    endif()
    list(FIND _nespico_assigned_pins "${_pin_value}" _duplicate_index)
    if(NOT _duplicate_index EQUAL -1)
        message(FATAL_ERROR "duplicate GPIO assignment: ${_pin_name} uses GPIO${_pin_value} already assigned to another loopback signal.")
    endif()
    list(APPEND _nespico_assigned_pins "${_pin_value}")
endforeach()

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
