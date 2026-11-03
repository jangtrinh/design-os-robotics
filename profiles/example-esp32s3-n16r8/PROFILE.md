# Example Device Profile (`example-esp32s3-n16r8`)

Template hardware profile for an `ESP32-S3-WROOM-1U-N16R8` (`16MB` Flash, `8MB` Octal PSRAM) + `ST7789 240×320` voice robot board.

- **Serial Port**: Auto-detected via `/dev/cu.usbmodem*` (`ESPPORT` override supported).
- **MAC / LAN IP**: Set `ROBOT_MAC` and `ROBOT_IP` in your local environment when running LAN ARP/ICMP checks with `./tools/robotctl.py`.
- **Local Dumps**: Any real device partition dumps (`profiles/robot-*/`) are git-ignored by default.
