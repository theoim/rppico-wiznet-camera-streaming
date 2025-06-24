# 📡 rppico-wiznet-camera-streaming

**Real-time video streaming with a single embedded board**  
Stream 160X120 or 320x240 YUY2 camera frames via UDP using only RP-PICO + HM01B0 + WIZnet Ethernet chips.


---

## 🧰 Requirements

| Component            | Description                          |
|----------------------|--------------------------------------|
| 🎛️ RP-PICO           | RP2040 or RP2350                     |
| 📷 HM01B0 Camera      | DVP 8-bit interface CMOS sensor      |
| 🌐 WIZnet Ethernet    | W6300, W5500, W5100S (SPI-based)     |
| 💻 Python             | For PC-side viewer (OpenCV required) |

<a name="WIZnet Raspberry Pi Pico Board List"></a>
## Hardware requirements

The Ethernet examples are compatible with the following Raspberry Pi-compatible WIZnet Ethernet I/O modules. These modules integrate [**WIZnet Ethernet chips**][link-wiznet_ethernet_chips] with either the [**RP2040**][link-rp2040] or [**RP2350**][link-rp2350] microcontrollers.

| Board/Module Name              | MCU      | Ethernet Chip  | Interface     | Socket # | TX/RX Buffer  | Notes                                  |
|--------------------------------|----------|----------------|---------------|----------|---------------|----------------------------------------|
| **[WIZnet Ethernet HAT][link-wiznet_ethernet_hat]** |  | W5100S | SPI | 4 | 16KB | RP Pico-compatible |
| **[W5100S-EVB-Pico][link-w5100s-evb-pico]** | RP2040 | W5100S | SPI | 4 | 16KB |  |
| **[W5500-EVB-Pico][link-w5500-evb-pico]** | RP2040 | W5500 | SPI | 8 | 32KB |  |
| **[W55RP20-EVB-Pico][link-w55rp20-evb-pico]** | RP2040 | W5500 | SPI (PIO) | 8 | 32KB | SiP: RP2040 + W5500 |
| **[W6100-EVB-Pico][link-w6100-evb-pico]** | RP2040 | W6100 | SPI | 8 | 32KB | Supports IPv4/IPv6 |
| **[W6300-EVB-Pico][link-w6300-evb-pico]** | RP2040 | W6300 | QSPI (PIO) | 8 | 64KB | Supports IPv4/IPv6 |
| **[W5100S-EVB-Pico2][link-w5100s-evb-pico2]** | RP2350 | W5100S | SPI | 4 | 16KB |  |
| **[W5500-EVB-Pico2][link-w5500-evb-pico2]** | RP2350 | W5500 | SPI | 8 | 32KB |  |
| **[W6100-EVB-Pico2][link-w6100-evb-pico2]** | RP2350 | W6100 | SPI | 8 | 32KB | Supports IPv4/IPv6 |
| **[W6300-EVB-Pico2][link-w6300-evb-pico2]** | RP2350 | W6300 | QSPI (PIO) | 8 | 64KB | Supports IPv4/IPv6 |

---

## 🔌 Pinout

**Total 8 signal pins**

| Function      | GPIO      |
|---------------|-----------|
| VSYNC         | GPIO6     |
| HSYNC         | GPIO7     |
| PCLK          | GPIO8     |
| DATA[0:7]     | GPIO9–16  |
| I2C SDA/SCL   | GPIO4, 5  |
| VCC / GND     | 3.3V / GND|

---

## 🗂️ Project Structure

```
examples/
└── WIZnet_Video_Streaming_HM01B0/
    ├── core/
    │   └── main.c         ← Embedded streaming firmware
    └── stream_viewer/
        └── stream_gui.py  ← Python UDP stream viewer (GUI)
```
---

## 🔄 Operation Flow

- **HM01B0 Camera**: Configured via I2C + 24 MHz MCLK via PWM  
- **RP-PICO**: Captures YUY2 frames using PIO + DMA  
- **WIZnet Chip**: Streams frames over UDP in chunks  
- **PC Viewer**: Receives and reassembles frames via UDP, displays in real time  

---

## 🚀 Embedded Platform Features

| Component | Description |
|----------|-------------|
| **MCU** | RP-PICO (RP2040 or RP2350) |
| **Camera** | Himax HM01B0 (QVGA 8-bit DVP) |
| **Ethernet** | WIZnet W6300 (or W5500/W5100S etc.) |
| **Protocol** | UDP (1532-byte chunks + 4-byte header) |
| **Core Logic** | PIO + DMA for high-speed frame capture + MACRAW/UDP output |

📌 **All-in-one platform – no external breakout boards needed.**  
Everything runs on a single RP-PICO board with camera and Ethernet combined.

---

## 🔧 Technical Highlights

- PIO + DMA based low-level camera frame grabber  
- Real-time YUY2 320×240 (QVGA) UDP frame streaming  
- Compatible with all WIZnet Ethernet chips (MACRAW or UDP modes)  
- 24 MHz MCLK via PWM, I2C configuration for HM01B0  
- Highly optimized for low power + high throughput

---

## 🖥️ WIZnet Stream Viewer (Python GUI)

**📁 Path**: `examples/WIZnet_Video_Streaming_HM01B0/stream_viewer/stream_gui.py`

| Category | Description |
|----------|-------------|
| **Live Streaming** | YUY2 frames decoded and displayed in real time |
| **Frame Reassembly** | Based on FrameID + PacketID logic |
| **GUI Controls** | Connect / Start / Stop / Capture / Record |
| **Robustness** | Handles dropped packets/frames gracefully |
| **Display Pipeline** | YUY2 → BGR → Scaled display via OpenCV |
| **UI Aesthetic** | Modern, macOS-like interface with SF font and status dot |
| **Modular Codebase** | Separated Assembler, GUI, Button logic for maintainability |

---

## 🐍 Python Environment Setup

Before running the **WIZnet Stream Viewer**, make sure to install the required Python packages.

### 📦 Requirements

- Python 3.7 or higher (Recommended: Python 3.10+)
- pip

### 📌 Pinout (Camera to RP-PICO)
| Signal     | GPIO |
|------------|------|
| VSYNC      | 6    |
| HSYNC      | 7    |
| PCLK       | 8    |
| DATA0~7    | 9~16 |
| I2C SDA    | 4    |
| I2C SCL    | 5    |
| VCC        | 3.3V |
| GND        | GND  |

---

### 🛠️ Setup Instructions

#### 1. Connect the camera to the RP-PICO following the pinout.

#### 2. In `CMakeLists.txt` at project root, select your target board:
```cmake
# Example:
set(BOARD_NAME W6300_EVB_PICO2)
```

#### 3. Choose camera resolution in `main.c`:
```c
// examples/WIZnet_Video_Streaming_HM01B0/core/main.c
#define USE_FRAME_320X240
// #define USE_FRAME_160X120
```

#### 4. Build and upload the `.uf2` file to RP-PICO:
```
build/WIZnet_Video_Streaming_HM01B0/core/udp_streaming.uf2
```

#### 5. Install Python dependencies:
```bash
pip install opencv-python Pillow
```

#### 6. Run the Python GUI viewer:
```bash
python examples/WIZnet_Video_Streaming_HM01B0/stream_viewer/stream_gui.py
```

#### 7. Click `Connect` → `Start` to begin streaming.
- Use `Capture` to save a frame
- Use `REC` to save video

> ✅ All files are saved in the current Python script directory.

---

### 📌 Notes
- Use the `STOP` button to close the video window safely.
- Supports all WIZnet chips via SPI (W5500/W5100S/W6300).
- Fully standalone: one RP-PICO board handles everything.




[link-getting_started_with_raspberry_pi_pico]: https://datasheets.raspberrypi.org/pico/getting-started-with-pico.pdf
[link-rp2040]: https://www.raspberrypi.org/products/rp2040/
[link-rp2350]: https://www.raspberrypi.com/products/rp2350/
[link-w5100s]: https://docs.wiznet.io/Product/iEthernet/W5100S/overview
[link-w5500]: https://docs.wiznet.io/Product/iEthernet/W5500/overview
[link-w6100]: https://docs.wiznet.io/Product/iEthernet/W6100/overview
[link-w6300]: https://docs.wiznet.io/Product/iEthernet/W6300/overview
[link-wiznet_ethernet_chips]: https://docs.wiznet.io/Product/iEthernet#product-family
[link-w55rp20-evb-pico]: https://docs.wiznet.io/Product/ioNIC/W55RP20/w55rp20-evb-pico
[link-raspberry_pi_pico]: https://www.raspberrypi.com/products/raspberry-pi-pico/
[link-wiznet_ethernet_hat]: https://docs.wiznet.io/Product/Open-Source-Hardware/wiznet_ethernet_hat
[link-w5100s-evb-pico]: https://docs.wiznet.io/Product/iEthernet/W5100S/w5100s-evb-pico
[link-w5500-evb-pico]: https://docs.wiznet.io/Product/iEthernet/W5500/w5500-evb-pico
[link-w6100-evb-pico]: https://docs.wiznet.io/Product/iEthernet/W6100/w6100-evb-pico
[link-w6300-evb-pico]: https://docs.wiznet.io/Product/iEthernet/W6300/w6300-evb-pico
[link-CAN]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/can
[link-dhcp_dns]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/dhcp_dns
[link-ftp]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/ftp
[link-ftp_client]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/ftp/client
[link-ftp_server]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/ftp/server
[link-http]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/http
[link-http_server]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/http/server
[link-loopback]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/loopback
[link-mqtt]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/mqtt
[link-mqtt_publish]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/mqtt/publish
[link-mqtt_publish_subscribe]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/mqtt/publish_subscribe
[link-mqtt_subscribe]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/mqtt/subscribe
[link-netbios]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/netbios
[link-network_install]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/network_install
[link-pppoe]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/pppoe
[link-sntp]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/sntp
[link-tcp_client_over_ssl]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/tcp_client_over_ssl
[link-tcp_server_multi_socket]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/tcp_server_multi_socket
[link-tftp]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/tftp
[link-UDP]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/udp
[link-UDP_multicast]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/udp_multicast
[link-UDP_multicast_receiver]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/udp_multicast/udp_multicast_receiver
[link-upnp]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/examples/upnp
[link-iolibrary_driver]: https://github.com/Wiznet/ioLibrary_Driver
[link-mbedtls]: https://github.com/ARMmbed/mbedtls
[link-pico_sdk]: https://github.com/raspberrypi/pico-sdk
[link-port_iolibrary_driver]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/port/ioLibrary_Driver
[link-port_mbedtls]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/port/mbedtls
[link-port_timer]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/main/port/timer
[link-wiznet_pico_c_1_0_0_version]: https://github.com/WIZnet-ioNIC/WIZnet-PICO-C/tree/1.0.0
[link-w5100s-evb-pico2]: https://docs.wiznet.io/Product/iEthernet/W5100S/w5100s-evb-pico2
[link-w5500-evb-pico2]: https://docs.wiznet.io/Product/iEthernet/W5500/w5500-evb-pico2
[link-w6100-evb-pico2]: https://docs.wiznet.io/Product/iEthernet/W6100/w6100-evb-pico2
[link-w6300-evb-pico2]: https://docs.wiznet.io/Product/iEthernet/W6300/w6300-evb-pico2
