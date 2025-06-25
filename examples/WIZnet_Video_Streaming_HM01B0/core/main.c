/**
 * Copyright (c) 2021 WIZnet Co.,Ltd
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

/**
 * ----------------------------------------------------------------------------------------------------
 * Includes
 * ----------------------------------------------------------------------------------------------------
 */
#include <stdio.h>
#include <string.h>

#include "port_common.h"
#include "wizchip_conf.h"
#include "wizchip_spi.h"
#include "socket.h"

#include "pico/time.h"
#include "pico/hm01b0.h"


/**
 * ----------------------------------------------------------------------------------------------------
 * Macros
 * ----------------------------------------------------------------------------------------------------
 */
// select the camera resolution (default is 160x120)
// #define USE_FRAME_320X240
#define USE_FRAME_160X120

// 해상도 정의
#if defined(USE_FRAME_320X240)
  #define FRAME_WIDTH   320
  #define FRAME_HEIGHT  240
#elif defined(USE_FRAME_160X120)
  #define FRAME_WIDTH   160
  #define FRAME_HEIGHT  120
#else
  #error "you must define USE_FRAME_320X240 or USE_FRAME_160X120"
#endif
#ifndef FRAME_RATE
#define FRAME_RATE    30
#endif

#define HEADER_SIZE 4         
#define DATA_BUF_SIZE 2048
#define MAX_UDP_PAYLOAD 1472
#define PAYLOAD_SIZE (MAX_UDP_PAYLOAD - HEADER_SIZE)

#if _WIZCHIP_ >= W6100
    #define SOCK_MODE Sn_MR_UDP4
    #define SOCK_FLAG 1 
#else
    #define SOCK_MODE Sn_MR_UDP
    #define SOCK_FLAG 0
#endif


/* Clock */
#define PLL_SYS_KHZ (133 * 1000)

/* Buffer */
#define ETHERNET_BUF_SIZE (32 * 2)

/* Socket */
#define SOCK_STREAM 0

/* Port */
#define PORT_STREAM 5000
/**
 * ----------------------------------------------------------------------------------------------------
 * Variables
 * ----------------------------------------------------------------------------------------------------
 */
/* Network */
static wiz_NetInfo g_net_info =
    {
        .mac = {0x00, 0x08, 0xDC, 0x12, 0x34, 0x56}, // MAC address
        .ip = {192, 168, 11, 2},                     // IP address
        .sn = {255, 255, 255, 0},                    // Subnet Mask
        .gw = {192, 168, 11, 1},                     // Gateway
        .dns = {8, 8, 8, 8},                         // DNS server
        #if _WIZCHIP_ > W5500
        .lla = {0xfe, 0x80, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x02, 0x08, 0xdc, 0xff,
                0xfe, 0x57, 0x57, 0x25},             // Link Local Address
        .gua = {0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00},             // Global Unicast Address
        .sn6 = {0xff, 0xff, 0xff, 0xff,
                0xff, 0xff, 0xff, 0xff,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00},             // IPv6 Prefix
        .gw6 = {0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00},             // Gateway IPv6 Address
        .dns6 = {0x20, 0x01, 0x48, 0x60,
                0x48, 0x60, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x88, 0x88},             // DNS6 server
        .ipmode = NETINFO_STATIC_ALL
#else
        .dhcp = NETINFO_STATIC        
#endif
};

/* Buffer for Recv Command(START/STOP) */
static uint8_t g_ethernet_buf[ETHERNET_BUF_SIZE] = {
    0,
};
static uint8_t dest_ip[4] = {192, 168, 11, 4};


//--------------------------------------------------------------------+
// USB Video
//--------------------------------------------------------------------+

static unsigned tx_busy = 0;
static unsigned interval_ms = 1000 / FRAME_RATE;

/* YUY2 frame buffer */
static uint8_t frame_buffer[FRAME_WIDTH * FRAME_HEIGHT * 16 / 8];
static uint8_t monochrome_buffer[FRAME_WIDTH * FRAME_HEIGHT];


//--------------------------------------------------------------------+
// MACRO CONSTANT TYPEDEF PROTYPES
//--------------------------------------------------------------------+

void video_task(void);

const struct hm01b0_config hm01b0_config = {
    .i2c           = i2c0,
    .sda_pin       = PICO_DEFAULT_I2C_SDA_PIN,
    .scl_pin       = PICO_DEFAULT_I2C_SCL_PIN,

#ifdef SPARKFUN_MICROMOD
    .vsync_pin     = 25,
    .hsync_pin     = 28,
    .pclk_pin      = 11,
    .data_pin_base = 16,   // Base data pin
    .data_bits     = 8,    // The SparkFun MicroMod ML Carrier Board has all 8 data pins connected
    .pio           = pio0,
    .pio_sm        = 0,
    .reset_pin     = 24,
    .mclk_pin      = 10,
#else
    .vsync_pin     = 6,
    .hsync_pin     = 7,
    .pclk_pin      = 8,
    .data_pin_base = 9,    // Base data pin
    .data_bits     = 1,    // Use only 1 pin for data
    .pio           = pio0,
    .pio_sm        = 0,
    .reset_pin     = -1,   // Not connected
    .mclk_pin      = -1,   // Not connected
#endif

    .width         = FRAME_WIDTH,
    .height        = FRAME_HEIGHT,
};

/**
 * ----------------------------------------------------------------------------------------------------
 * Functions
 * ----------------------------------------------------------------------------------------------------
 */
/* Clock */
static void set_clock_khz(void);
int32_t video_streaming_udps(uint8_t sn, uint8_t *buf, uint16_t port);
static void fill_camera_frame(uint8_t *buffer);
/**
 * ----------------------------------------------------------------------------------------------------
 * Main
 * ----------------------------------------------------------------------------------------------------
 */
int main()
{
    /* Initialize */
    int retval = 0;

    set_clock_khz();

    stdio_init_all();
    sleep_ms(3000);

    wizchip_spi_initialize();
    wizchip_cris_initialize();

    wizchip_reset();
    wizchip_initialize();
    wizchip_check();

    network_initialize(g_net_info);

    /* Get network information */
    print_network_information(g_net_info);

#if 1
    #ifdef SPARKFUN_MICROMOD
        gpio_set_dir(25, GPIO_IN);
    #endif

    if (hm01b0_init(&hm01b0_config) != 0)
    {
        printf("failed to initialize camera!\n");

        while (1) { tight_loop_contents(); }
    }
#endif

    /* Infinite loop */
    while (1)
    {  
     video_streaming_udps(SOCK_STREAM, g_ethernet_buf, PORT_STREAM);
    }
}

/**
 * ----------------------------------------------------------------------------------------------------
 * Functions
 * ----------------------------------------------------------------------------------------------------
 */
/* Clock */
static void set_clock_khz(void)
{
    // set a system clock frequency in khz
    set_sys_clock_khz(PLL_SYS_KHZ, true);

    // configure the specified clock
    clock_configure(
        clk_peri,
        0,                                                // No glitchless mux
        CLOCKS_CLK_PERI_CTRL_AUXSRC_VALUE_CLKSRC_PLL_SYS, // System PLL on AUX mux
        PLL_SYS_KHZ * 1000,                               // Input frequency
        PLL_SYS_KHZ * 1000                                // Output (must be same as no divider)
    );
}



int32_t video_streaming_udps(uint8_t sn, uint8_t *buf, uint16_t port)
{
    static bool send_mode = false;
    static uint8_t destip[16] = {0};
    static uint16_t destport = 0;
    static uint8_t dest_len = 4;

    static uint64_t last_tick_us = 0;
    static uint8_t frame_id = 0;

    uint8_t status;
    uint16_t received_size;
    int32_t ret;

    getsockopt(sn, SO_STATUS, &status);

    switch (status)
    {
    case SOCK_UDP:
        getsockopt(sn, SO_RECVBUF, &received_size);
        if (received_size) {
            if (received_size > ETHERNET_BUF_SIZE) received_size = ETHERNET_BUF_SIZE;

            ret = recvfrom(sn, buf, received_size, destip, &destport, &dest_len);
            if (ret <= 0) return ret;

            received_size = (uint16_t)ret;

            if (received_size == 5 && !memcmp(buf, "START", 5)) {
                send_mode = true;
                frame_id = 0;
            } else if (received_size == 4 && !memcmp(buf, "STOP", 4)) {
                send_mode = false;
            }
        }

        if (send_mode)
        {
            frame_id++;

            // 1. Capture camera frame
            fill_camera_frame(frame_buffer);

            // 2. send frame data
            uint32_t frame_size = FRAME_WIDTH * FRAME_HEIGHT * 2;
            uint8_t total_packets = (frame_size + PAYLOAD_SIZE - 1) / PAYLOAD_SIZE;
            uint16_t chunk_size;
            for (uint8_t pkt_id = 0; pkt_id < total_packets; pkt_id++) {
                uint32_t offset = (uint32_t)pkt_id * PAYLOAD_SIZE; 
                uint32_t remain = frame_size - offset;
                chunk_size = (remain > PAYLOAD_SIZE) ? PAYLOAD_SIZE : (uint16_t)remain;

                uint8_t packet[MAX_UDP_PAYLOAD];
                packet[0] = frame_id;
                packet[1] = pkt_id;
                packet[2] = total_packets;
                packet[3] = (pkt_id == total_packets - 1) ? 0x01 : 0x00;

                memset(packet + HEADER_SIZE, 0, PAYLOAD_SIZE);
                memcpy(packet + HEADER_SIZE, &frame_buffer[offset], chunk_size);
                ret = sendto(sn, packet, chunk_size + HEADER_SIZE, destip, destport, dest_len);
                if (ret < 0) return ret;
            }
            //delay to control frame rate
        }
        break;

    case SOCK_CLOSED:
        socket(sn, SOCK_MODE, port, SOCK_FLAG);
        break;

    default:
        break;
    }

    return 1;
}

//--------------------------------------------------------------------+
// Device callbacks
//--------------------------------------------------------------------+

static void fill_camera_frame(uint8_t *buffer)
{
  const uint8_t* src = monochrome_buffer;

  // Read frame from camera
  hm01b0_read_frame(monochrome_buffer, sizeof(monochrome_buffer));
  // Copy monochrome frame data to frame buffer as Y value,
  // set U and V values with a fixed value of 128.
  for (int y = 0; y < FRAME_HEIGHT; y++) {
    for (int x = 0; x < FRAME_WIDTH; x++) {
      *buffer++ = *src++;
      *buffer++ = 128;
    }
  }
}

void video_task(void)
{
  static unsigned start_ms = 0;
  static unsigned already_sent = 0;


  if (!already_sent) {
    already_sent = 1;
    start_ms = board_millis();
    tx_busy = 1;
    printf("Filling camera frame...\n");
fill_camera_frame(frame_buffer);
printf("Camera frame filled.\n");
  }

  unsigned cur = board_millis();
  if (cur - start_ms < interval_ms) return; // not enough time
  if (tx_busy) return;
  tx_busy = 1;
  start_ms += interval_ms;

  printf("Filling camera frame...\n");
fill_camera_frame(frame_buffer);
printf("Camera frame filled.\n");
}

