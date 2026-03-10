# HomePLC HMI

Web-based HMI for a residential CompactLogix PLC monitoring generator/ATS, sump pump, HVAC, outdoor temperature, and whole-house electrical.

## Screenshots

### Dashboard (Simulation Mode)
![Dashboard](screenshots/dashboard.png)

### PLC Logic Visualization
![Visualization](screenshots/visualization.png)

## What it does
- Polls PLC tags over EtherNet/IP using pylogix
- Displays live status, alarms, and runtime statistics in a dark-theme dashboard
- HMI write commands for exercise triggers, fault resets, and filter hour resets
- Built-in PLC simulator (no hardware needed) with adjustable I/O and timer speed

## Hardware
- Allen-Bradley 5069-L306ERM CompactLogix
- 5069-IB16 (digital in), 5069-OB16 (digital out), 5069-IF8 (analog in)
- 4-20mA sensors on 0-20mA range for outdoor temp and house current

## Running

**Simulation mode** (no PLC required):
```
python app.py --sim
```
Or double-click `run_sim.bat`.

**Live mode** (connected to PLC):
```
python app.py
```
Edit `PLC_IP` in `app.py` to match your controller.

Open `http://localhost:5000` in any browser.

## Requirements
- Python 3
- Flask (`pip install flask`)
- pylogix (`pip install pylogix`) - only needed for live mode
