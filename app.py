"""HomePLC Web HMI - Flask + pylogix + Simulator"""

import os
import sys
import time
import threading
from flask import Flask, render_template, jsonify, request

# ============================================================
# CONFIGURATION
# ============================================================
PLC_IP = "192.168.1.1"  # Change to your CompactLogix IP
POLL_RATE = 1.0

# Check for --sim flag or environment variable
SIM_MODE = "--sim" in sys.argv or os.environ.get("HOMEPLC_SIM", "0") == "1"

if not SIM_MODE:
    from pylogix import PLC

# ============================================================
# TAG LISTS
# ============================================================
READ_TAGS = [
    "Gen_State", "Gen_Running", "Gen_Fault", "Gen_Ready",
    "Gen_On_Utility", "Gen_On_Generator", "Gen_Start_Cmd", "ATS_Transfer_Cmd",
    "Gen_Exercise_Active", "Gen_Start_Fail", "Gen_Stop_Fail",
    "Gen_Crank_Attempts", "Gen_Total_Run_Seconds",
    "Utility_Power_Present", "ATS_Utility_Pos", "ATS_Generator_Pos",
    "Exercise_Trigger",
    "Sump_State", "Sump_Pump_Run", "Sump_Float_High",
    "Sump_Test_Active", "Sump_Last_Test_OK", "Sump_Max_Run_Fault",
    "Sump_Cycle_Count", "Sump_Total_Run_Seconds",
    "Sump_Last_Run_Seconds", "Sump_Current_Run_Seconds",
    "HVAC_Furnace_Running", "HVAC_Cycle_Count",
    "HVAC_Total_Run_Seconds", "HVAC_Last_Run_Seconds",
    "HVAC_Current_Run_Seconds", "HVAC_Filter_Run_Seconds",
    "HVAC_Filter_Change_Due", "HVAC_Short_Cycle_Alarm",
    "HVAC_Short_Cycle_Count", "Thermostat_W_Call",
    "Outdoor_Temp_F", "House_Current_Amps",
    "Elec_Current_Amps", "Elec_Peak_Amps", "Elec_Total_kWh",
    "Elec_Overload_Alarm", "Elec_Gen_Overload_Alarm",
    "Elec_Gen_Max_Amps",
    "HVAC_Outdoor_Temp_Min", "HVAC_Outdoor_Temp_Max",
]

WRITE_TAGS = [
    "HMI_Exercise_Request", "HMI_Gen_Fault_Reset",
    "HMI_Sump_Test_Request", "HMI_Sump_Fault_Reset",
    "HMI_Filter_Reset", "HMI_Temp_MinMax_Reset", "HMI_HVAC_Alarm_Reset",
    "HMI_Elec_Peak_Reset", "HMI_Elec_Alarm_Reset",
]

# ============================================================
# SIMULATOR (when --sim flag is used)
# ============================================================
sim = None
if SIM_MODE:
    from simulator import PLCSimulator
    sim = PLCSimulator()

# ============================================================
# PLC COMMUNICATION (live mode)
# ============================================================
tag_data = {}
plc_connected = False
plc_error = ""
lock = threading.Lock()


def plc_poll_thread():
    global tag_data, plc_connected, plc_error
    while True:
        try:
            with PLC() as comm:
                comm.IPAddress = PLC_IP
                comm.SocketTimeout = 3.0
                results = comm.Read(READ_TAGS)
                with lock:
                    if isinstance(results, list):
                        for r in results:
                            if r.Status == "Success":
                                tag_data[r.TagName] = r.Value
                            else:
                                tag_data[r.TagName] = None
                    else:
                        if results.Status == "Success":
                            tag_data[results.TagName] = results.Value
                    plc_connected = True
                    plc_error = ""
        except Exception as e:
            with lock:
                plc_connected = False
                plc_error = str(e)
        time.sleep(POLL_RATE)


def write_tag(tag_name, value):
    try:
        with PLC() as comm:
            comm.IPAddress = PLC_IP
            comm.SocketTimeout = 3.0
            result = comm.Write(tag_name, value)
            return result.Status == "Success"
    except Exception:
        return False


# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", sim_mode=SIM_MODE)


@app.route("/viz")
def viz():
    return render_template("viz.html", sim_mode=SIM_MODE)


@app.route("/api/data")
def api_data():
    if SIM_MODE:
        data = sim.get_all_tags()
        data["_plc_connected"] = True
        data["_plc_error"] = ""
        data["_sim_mode"] = True
        data["_sim_inputs"] = sim.get_sim_inputs()
    else:
        with lock:
            data = dict(tag_data)
            data["_plc_connected"] = plc_connected
            data["_plc_error"] = plc_error
        data["_sim_mode"] = False

    gen_sec = data.get("Gen_Total_Run_Seconds", 0) or 0
    data["Gen_Total_Run_Hours"] = round(gen_sec / 3600, 1)
    sump_sec = data.get("Sump_Total_Run_Seconds", 0) or 0
    data["Sump_Total_Run_Hours"] = round(sump_sec / 3600, 1)
    hvac_sec = data.get("HVAC_Total_Run_Seconds", 0) or 0
    data["HVAC_Total_Run_Hours"] = round(hvac_sec / 3600, 1)
    filter_sec = data.get("HVAC_Filter_Run_Seconds", 0) or 0
    data["HVAC_Filter_Run_Hours"] = round(filter_sec / 3600, 1)
    return jsonify(data)


@app.route("/api/write", methods=["POST"])
def api_write():
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data"}), 400
    tag = body.get("tag")
    value = body.get("value", True)
    if tag not in WRITE_TAGS:
        return jsonify({"error": f"Tag '{tag}' not allowed"}), 403
    if SIM_MODE:
        ok = sim.write_tag(tag, value)
    else:
        ok = write_tag(tag, value)
    return jsonify({"success": ok, "tag": tag})


@app.route("/api/sim/timers")
def api_sim_timers():
    """Return timer states from the simulator."""
    if not SIM_MODE:
        return jsonify({"error": "Not in simulation mode"}), 400
    return jsonify(sim.get_timer_states())


@app.route("/api/sim", methods=["POST"])
def api_sim():
    """Set simulator inputs."""
    if not SIM_MODE:
        return jsonify({"error": "Not in simulation mode"}), 400
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data"}), 400
    name = body.get("input")
    value = body.get("value")
    if name == "speed_multiplier":
        sim.speed_multiplier = max(1, min(50, int(value)))
        return jsonify({"success": True})
    sim.set_sim_input(name, value)
    return jsonify({"success": True})


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    if SIM_MODE:
        print("=" * 50)
        print("  HomePLC HMI - SIMULATION MODE")
        print("  All PLC logic running locally")
        print("  Timers at 10x speed for demo")
        print("=" * 50)
        sim.start()
    else:
        print(f"HomePLC HMI - LIVE MODE (PLC: {PLC_IP})")
        t = threading.Thread(target=plc_poll_thread, daemon=True)
        t.start()

    print(f"Open browser to: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
