"""HomePLC Web HMI - Flask + pylogix + Simulator"""

import os
import sys
import time
import threading
from flask import Flask, render_template, jsonify, request
from datalogger import DataLogger
from alerts import AlertManager

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
    # Freeze monitoring
    "Freeze_Warning", "Freeze_Critical",
    "Freeze_Warning_SP", "Freeze_Critical_SP",
    # Sump cycle rate
    "Sump_Hourly_Cycle_Count", "Sump_Cycle_Rate_Alarm", "Sump_Cycle_Rate_Max",
    # Leak detection
    "Leak_Zone1", "Leak_Zone2", "Leak_Zone3", "Leak_Any_Alarm",
    # Garage door
    "Garage_Door_Closed", "Garage_Door_Open",
    "Garage_Open_Seconds", "Garage_Open_Alarm", "Garage_Open_Max_Seconds",
    # Well pump / water pressure
    "Water_Pressure_PSI", "Well_Pump_Running",
    "Well_Pump_Cycle_Count", "Well_Pump_Current_Run_Seconds",
    "Well_Pump_Last_Run_Seconds", "Well_Pump_Short_Cycle_Count",
    "Well_Pump_Short_Cycle_Alarm", "Water_Pressure_Low_Alarm",
    "Water_Pressure_Low_SP",
    # Generator exercise schedule
    "Exercise_Schedule_Day", "Exercise_Schedule_Hour", "Exercise_Duration_Minutes",
    # Load shedding
    "Load_Shed_Active", "Load_Shed_Threshold",
    "Load_Shed_HVAC", "Load_Shed_NonCritical1", "Load_Shed_NonCritical2",
    # Maintenance tracking
    "Maint_Gen_Oil_Due", "Maint_Gen_Oil_Hours", "Maint_Gen_Run_Since_Oil",
    "Maint_Sump_Inspect_Due", "Maint_Sump_Inspect_Cycles",
    "Maint_Sump_Cycles_Since_Inspect",
    "Maint_Furnace_Inspect_Due", "Maint_Furnace_Inspect_Hours",
    "Maint_Furnace_Run_Since_Inspect",
    # HVAC efficiency
    "HVAC_Efficiency_Pct", "HVAC_HDD_Runtime_Ratio",
    "HVAC_HDD_Baseline_Ratio", "HVAC_Efficiency_Alarm",
    "HVAC_Efficiency_Threshold", "HVAC_Daily_Run_Seconds",
    "HVAC_HDD_Accumulated",
]

WRITE_TAGS = [
    "HMI_Exercise_Request", "HMI_Gen_Fault_Reset",
    "HMI_Sump_Test_Request", "HMI_Sump_Fault_Reset",
    "HMI_Filter_Reset", "HMI_Temp_MinMax_Reset", "HMI_HVAC_Alarm_Reset",
    "HMI_Elec_Peak_Reset", "HMI_Elec_Alarm_Reset",
    "HMI_Freeze_Alarm_Reset", "HMI_Leak_Alarm_Reset",
    "HMI_Garage_Alarm_Reset", "HMI_Well_Alarm_Reset",
    "HMI_Load_Shed_Reset",
    "HMI_Maint_Gen_Oil_Reset", "HMI_Maint_Sump_Reset",
    "HMI_Maint_Furnace_Reset",
    "HMI_HVAC_Efficiency_Reset",
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
data_logger = DataLogger("data/homeplc_history.db")
alert_manager = AlertManager()


def get_current_tag_data():
    """Return current tag dict for use by data logger."""
    if SIM_MODE:
        return sim.get_all_tags()
    else:
        with lock:
            return dict(tag_data)


@app.route("/")
def index():
    return render_template("index.html", sim_mode=SIM_MODE)


@app.route("/viz")
def viz():
    return render_template("viz.html", sim_mode=SIM_MODE)


@app.route("/history")
def history():
    return render_template("history.html", sim_mode=SIM_MODE)


@app.route("/settings")
def settings():
    return render_template("settings.html", sim_mode=SIM_MODE)


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

    # Maintenance computed values
    maint_gen_oil_sec = data.get("Maint_Gen_Run_Since_Oil", 0) or 0
    data["Maint_Gen_Hours_Since_Oil"] = round(maint_gen_oil_sec / 3600, 1)
    maint_furnace_sec = data.get("Maint_Furnace_Run_Since_Inspect", 0) or 0
    data["Maint_Furnace_Hours_Since_Inspect"] = round(maint_furnace_sec / 3600, 1)

    # Well pump total cycles (pass through from tags)
    data["Well_Pump_Total_Cycles"] = data.get("Well_Pump_Cycle_Count", 0)

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
# HISTORY API
# ============================================================
@app.route("/api/history")
def api_history():
    """Return historical data for a tag. Query params: tag, hours."""
    tag = request.args.get("tag", "")
    hours = int(request.args.get("hours", 24))
    if not tag:
        return jsonify({"error": "tag parameter required"}), 400
    data = data_logger.get_history(tag, hours=hours)
    return jsonify(data)


@app.route("/api/history/tags")
def api_history_tags():
    """Return list of logged tag names."""
    return jsonify(data_logger.get_available_tags())


# ============================================================
# ALERTS API
# ============================================================
@app.route("/api/alerts/config", methods=["GET"])
def api_alerts_config_get():
    """Return alert config (password masked)."""
    return jsonify(alert_manager.get_config_safe())


@app.route("/api/alerts/config", methods=["POST"])
def api_alerts_config_post():
    """Update alert config."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data"}), 400
    alert_manager.update_config(body)
    return jsonify({"success": True})


@app.route("/api/alerts/test", methods=["POST"])
def api_alerts_test():
    """Send a test email."""
    ok = alert_manager.send_test()
    return jsonify({"success": ok})


@app.route("/api/alerts/log")
def api_alerts_log():
    """Return recent alerts."""
    return jsonify(alert_manager.get_log())


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

    # Start data logger background thread
    data_logger.start(get_current_tag_data, interval=60)

    # Start alert checking background thread
    def alert_check_thread():
        while True:
            try:
                tag_dict = get_current_tag_data()
                if tag_dict:
                    alert_manager.check_and_send(tag_dict)
            except Exception as e:
                print(f"Alert check error: {e}")
            time.sleep(10)

    alert_thread = threading.Thread(target=alert_check_thread, daemon=True)
    alert_thread.start()

    print(f"Open browser to: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
