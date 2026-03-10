# Raspberry Pi 5 Deployment Guide

## What you need
- Raspberry Pi 5 + USB-C power supply
- MicroSD card (32GB+)
- Ethernet cable (Pi to router)

## 1. Flash the SD card
1. Install **Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. Choose OS: **Raspberry Pi OS (64-bit)**
3. Choose your SD card
4. Click gear icon for settings:
   - Enable SSH with password authentication
   - Username: `pi`, set a password
   - Configure WiFi as backup
   - Hostname: `homeplc`
5. Write and wait

## 2. Boot the Pi
1. Insert SD card, plug in Ethernet and power
2. Wait ~60 seconds for first boot

## 3. Connect from your PC
```bash
ping homeplc.local
ssh pi@homeplc.local
```
Enter your password (characters won't show, that's normal).

## 4. Install the HMI
Run these commands on the Pi:
```bash
sudo apt update && sudo apt install -y python3 python3-pip git
pip3 install flask pylogix
git clone https://github.com/tremmelnicholas-ops/Home_PLC.git
cd Home_PLC
```

Edit the PLC IP to match your controller:
```bash
nano app.py
```
Change `PLC_IP = "192.168.1.1"` to your PLC's static IP, then Ctrl+X, Y, Enter to save.

Test it:
```bash
python3 app.py
```
Open `http://homeplc.local:5000` from any device on your network.

## 5. Auto-start on boot
```bash
sudo tee /etc/systemd/system/homeplc-hmi.service << 'EOF'
[Unit]
Description=HomePLC HMI
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Home_PLC/app.py
WorkingDirectory=/home/pi/Home_PLC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable homeplc-hmi
sudo systemctl start homeplc-hmi
```

The HMI now starts automatically on boot and restarts if it crashes.

## 6. Access from any device
Open a browser on your phone, tablet, or PC:
```
http://homeplc.local:5000
```

## Network diagram
```
Router (192.168.1.1)
  |--- PLC 5069-L306ERM (192.168.1.10) - static IP
  |--- Raspberry Pi 5   (192.168.1.50) - runs HMI
  |--- Phone / Tablet / PC             - browser to :5000
```

## Useful commands
```bash
sudo systemctl status homeplc-hmi    # check if running
sudo systemctl restart homeplc-hmi   # restart after changes
sudo journalctl -u homeplc-hmi -f    # view live logs
```
