#!/usr/bin/env python3
"""Build the HomePLC.L5X file for Studio 5000."""

# Read original file to extract modules section
with open(r"C:\Users\tremmen\Desktop\HomePLC_backup.L5X", "r", encoding="utf-8") as f:
    original = f.readlines()

# Extract lines 1-1103 (header through </AddOnInstructionDefinitions>)
# That's the XML header, Controller open tag, RedundancyInfo, Security, SafetyInfo,
# DataTypes, Modules (all module configs), and AddOnInstructionDefinitions
header_lines = original[:1103]  # lines 1-1103 (0-indexed: 0-1102)
header = "".join(header_lines)

# ============================================================
# TAGS SECTION
# ============================================================

def bool_tag(name, desc, val="0"):
    return f'''<Tag Name="{name}" TagType="Base" DataType="BOOL" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description><![CDATA[{desc}]]></Description>
<Data Format="L5K"><![CDATA[{val}]]></Data>
<Data Format="Decorated"><DataValue DataType="BOOL" Radix="Decimal" Value="{val}"/></Data>
</Tag>'''

def dint_tag(name, desc, val="0"):
    return f'''<Tag Name="{name}" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="Read/Write">
<Description><![CDATA[{desc}]]></Description>
<Data Format="L5K"><![CDATA[{val}]]></Data>
<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="{val}"/></Data>
</Tag>'''

def real_tag(name, desc, val="0.0"):
    fval = float(val)
    if fval == 0.0:
        l5k_val = "0.00000000e+000"
    else:
        l5k_val = f"{fval:.8e}"
        # Fix Python's e notation to match L5X format (e+001 not e+01)
        parts = l5k_val.split('e')
        sign = '+' if not parts[1].startswith('-') else '-'
        exp = abs(int(parts[1]))
        l5k_val = f"{parts[0]}e{sign}{exp:03d}"
    return f'''<Tag Name="{name}" TagType="Base" DataType="REAL" Radix="Float" Constant="false" ExternalAccess="Read/Write">
<Description><![CDATA[{desc}]]></Description>
<Data Format="L5K"><![CDATA[{l5k_val}]]></Data>
<Data Format="Decorated"><DataValue DataType="REAL" Radix="Float" Value="{val}"/></Data>
</Tag>'''

def timer_tag(name, desc, preset):
    return f'''<Tag Name="{name}" TagType="Base" DataType="TIMER" Constant="false" ExternalAccess="Read/Write">
<Description><![CDATA[{desc}]]></Description>
<Data Format="L5K"><![CDATA[[0,{preset},0]]]></Data>
<Data Format="Decorated">
<Structure DataType="TIMER">
<DataValueMember Name="PRE" DataType="DINT" Radix="Decimal" Value="{preset}"/>
<DataValueMember Name="ACC" DataType="DINT" Radix="Decimal" Value="0"/>
<DataValueMember Name="EN" DataType="BOOL" Value="0"/>
<DataValueMember Name="TT" DataType="BOOL" Value="0"/>
<DataValueMember Name="DN" DataType="BOOL" Value="0"/>
</Structure>
</Data>
</Tag>'''

tags = []

# === BOOL TAGS ===
bool_tags = [
    ("Utility_Power_Present", "Utility power present signal"),
    ("Gen_Running", "Generator running feedback"),
    ("Gen_Fault", "Generator fault signal"),
    ("Gen_Ready", "Generator ready signal"),
    ("ATS_Utility_Pos", "ATS in utility position"),
    ("ATS_Generator_Pos", "ATS in generator position"),
    ("Sump_Float_High", "Sump pit float switch high water"),
    ("Gen_Start_Cmd", "Generator start command output"),
    ("ATS_Transfer_Cmd", "ATS transfer to generator command"),
    ("Sump_Pump_Run", "Sump pump run output"),
    ("Thermostat_W_Call", "Thermostat heat demand 24V signal"),
    ("Gen_On_Utility", "System on utility power"),
    ("Gen_On_Generator", "System on generator power"),
    ("Gen_Start_Fail", "Generator failed to start"),
    ("Gen_Stop_Fail", "Generator failed to stop"),
    ("Gen_Exercise_Active", "Weekly exercise in progress"),
    ("Exercise_Trigger", "Trigger to start exercise"),
    ("HMI_Exercise_Request", "HMI manual exercise request"),
    ("HMI_Gen_Fault_Reset", "HMI generator fault reset"),
    ("Sump_Max_Run_Fault", "Pump max run time exceeded"),
    ("Sump_Test_Active", "Test run in progress"),
    ("Sump_Last_Test_OK", "Last test completed OK"),
    ("Sump_Test_Trigger", "Trigger to start sump test"),
    ("HMI_Sump_Test_Request", "HMI manual sump test request"),
    ("HMI_Sump_Fault_Reset", "HMI sump fault reset"),
    ("HVAC_Furnace_Running", "Furnace is running"),
    ("HVAC_Was_Running", "Furnace was recently running"),
    ("HVAC_Filter_Change_Due", "Filter change reminder at 300 hours"),
    ("HVAC_Short_Cycle_Alarm", "Short cycling alarm"),
    ("HMI_Filter_Reset", "HMI filter hours reset"),
    ("HMI_Temp_MinMax_Reset", "HMI min/max temp reset"),
    ("HMI_HVAC_Alarm_Reset", "HMI HVAC alarm reset"),
    ("Elec_Overload_Alarm", "Sustained overload alarm"),
    ("Elec_Gen_Overload_Alarm", "Generator overload alarm"),
    ("HMI_Elec_Peak_Reset", "HMI peak current reset"),
    ("HMI_Elec_Alarm_Reset", "HMI electrical alarm reset"),
    ("Pulse_1s", "1 second pulse output"),
    ("Exercise_Count_ONS", "One-shot for exercise second counter"),
    ("Crank_Attempt_ONS", "One-shot for crank attempt counter"),
    ("Sump_Cycle_ONS", "One-shot for sump pump cycle counter"),
    # HMI status bools
    ("HMI_Gen_Running", "Generator running for HMI"),
    ("HMI_Gen_On_Utility", "On utility for HMI"),
    ("HMI_Gen_On_Generator", "On generator for HMI"),
    ("HMI_Gen_Exercise_Active", "Exercise active for HMI"),
    ("HMI_Gen_Start_Fail_Alarm", "Gen start fail alarm for HMI"),
    ("HMI_Gen_Stop_Fail_Alarm", "Gen stop fail alarm for HMI"),
    ("HMI_Gen_Fault_Alarm", "Gen fault alarm for HMI"),
    ("HMI_Utility_Present", "Utility present for HMI"),
    ("HMI_Sump_Pump_Running", "Pump running for HMI"),
    ("HMI_Sump_Float_Active", "Float active for HMI"),
    ("HMI_Sump_Test_Active", "Sump test active for HMI"),
    ("HMI_Sump_Max_Run_Alarm", "Sump max run alarm for HMI"),
    ("HMI_Sump_Last_Test_OK", "Last test OK for HMI"),
    ("HMI_Any_Alarm", "Any active alarm for HMI banner"),
    ("HMI_HVAC_Furnace_Running", "Furnace running for HMI"),
    ("HMI_HVAC_Filter_Change_Due", "Filter change due for HMI"),
    ("HMI_HVAC_Short_Cycle_Alarm", "Short cycle alarm for HMI"),
    ("HMI_Elec_Overload_Alarm", "Overload alarm for HMI"),
    ("HMI_Elec_Gen_Overload_Alarm", "Generator overload alarm for HMI"),
    # Feature 3: Freeze Protection
    ("Freeze_Warning", "Freeze warning - temp below warning setpoint"),
    ("Freeze_Critical", "Freeze critical - temp below critical setpoint"),
    ("HMI_Freeze_Alarm_Reset", "HMI freeze alarm reset"),
    # Feature 2: Sump Cycle Rate Alarm
    ("Sump_Cycle_Rate_Alarm", "Sump pump excessive cycle rate alarm"),
    ("Sump_Cycle_Rate_ONS", "One-shot for sump cycle rate counting"),
    # Feature 9: Water Leak Detection
    ("Leak_Zone1", "Leak sensor zone 1"),
    ("Leak_Zone2", "Leak sensor zone 2"),
    ("Leak_Zone3", "Leak sensor zone 3"),
    ("Leak_Any_Alarm", "Any leak zone alarm active"),
    ("HMI_Leak_Alarm_Reset", "HMI leak alarm reset"),
    # Feature 10: Garage Door Monitor
    ("Garage_Door_Closed", "Garage door closed limit switch NC"),
    ("Garage_Door_Open", "Garage door is open"),
    ("Garage_Open_Alarm", "Garage door open too long alarm"),
    ("HMI_Garage_Alarm_Reset", "HMI garage alarm reset"),
    # Feature 11: Well Pump / Water Pressure
    ("Well_Pump_Running", "Well pump running feedback"),
    ("Well_Pump_Cycle_ONS", "One-shot for well pump cycle counting"),
    ("Well_Pump_Short_Cycle_Alarm", "Well pump short cycle alarm"),
    ("Water_Pressure_Low_Alarm", "Water pressure low alarm"),
    ("HMI_Well_Alarm_Reset", "HMI well pump alarm reset"),
    # Feature 4: Load Shedding
    ("Load_Shed_Active", "Load shedding active"),
    ("Load_Shed_HVAC", "Load shed HVAC output"),
    ("Load_Shed_NonCritical1", "Load shed non-critical 1 output"),
    ("Load_Shed_NonCritical2", "Load shed non-critical 2 output"),
    ("HMI_Load_Shed_Reset", "HMI load shed reset"),
    # Feature 8: Maintenance Schedules
    ("Maint_Gen_Oil_Due", "Generator oil change due"),
    ("Maint_Sump_Inspect_Due", "Sump pump inspection due"),
    ("Maint_Furnace_Inspect_Due", "Furnace inspection due"),
    ("HMI_Maint_Gen_Oil_Reset", "HMI gen oil maintenance reset"),
    ("HMI_Maint_Sump_Reset", "HMI sump maintenance reset"),
    ("HMI_Maint_Furnace_Reset", "HMI furnace maintenance reset"),
    ("Maint_Sump_Cycle_ONS", "One-shot for maintenance sump cycle counting"),
    # Feature 7: HVAC Efficiency
    ("HVAC_Efficiency_Alarm", "HVAC efficiency degradation alarm"),
    ("HMI_HVAC_Efficiency_Reset", "HMI HVAC efficiency reset"),
    # HMI tags for new features
    ("HMI_Freeze_Warning", "Freeze warning for HMI"),
    ("HMI_Freeze_Critical", "Freeze critical for HMI"),
    ("HMI_Sump_Cycle_Rate_Alarm", "Sump cycle rate alarm for HMI"),
    ("HMI_Leak_Any_Alarm", "Leak alarm for HMI"),
    ("HMI_Garage_Open_Alarm", "Garage open alarm for HMI"),
    ("HMI_Well_Pump_Running", "Well pump running for HMI"),
    ("HMI_Well_Short_Cycle_Alarm", "Well pump short cycle alarm for HMI"),
    ("HMI_Water_Pressure_Low_Alarm", "Water pressure low alarm for HMI"),
    ("HMI_Load_Shed_Active", "Load shed active for HMI"),
    ("HMI_Maint_Gen_Oil_Due", "Gen oil due for HMI"),
    ("HMI_Maint_Sump_Inspect_Due", "Sump inspect due for HMI"),
    ("HMI_Maint_Furnace_Inspect_Due", "Furnace inspect due for HMI"),
    ("HMI_HVAC_Efficiency_Alarm", "HVAC efficiency alarm for HMI"),
]
for name, desc in bool_tags:
    tags.append(bool_tag(name, desc))

# === DINT TAGS ===
dint_tags = [
    ("Gen_State", "Generator state machine"),
    ("Gen_Crank_Attempts", "Generator crank attempt counter"),
    ("Gen_Total_Run_Seconds", "Total generator run time in seconds"),
    ("Exercise_Seconds", "Seconds since last exercise"),
    ("Sump_State", "Sump pump state machine"),
    ("Sump_Cycle_Count", "Total pump cycles"),
    ("Sump_Total_Run_Seconds", "Total pump run time in seconds"),
    ("Sump_Current_Run_Seconds", "Current cycle run time"),
    ("Sump_Last_Run_Seconds", "Last cycle run duration"),
    ("Sump_Test_Seconds", "Seconds since last sump test"),
    ("HVAC_Cycle_Count", "Total furnace cycles"),
    ("HVAC_Current_Run_Seconds", "Current furnace run time"),
    ("HVAC_Last_Run_Seconds", "Last furnace run duration"),
    ("HVAC_Total_Run_Seconds", "Total furnace run time in seconds"),
    ("HVAC_Filter_Run_Seconds", "Blower run time since filter change"),
    ("HVAC_Short_Cycle_Count", "Consecutive short cycles detected"),
    # HMI DINT tags
    ("HMI_Gen_State", "Generator state for HMI display"),
    ("HMI_Gen_Total_Run_Hours", "Generator total run hours for HMI"),
    ("HMI_Gen_Crank_Attempts", "Crank attempts for HMI"),
    ("HMI_Sump_State", "Sump state for HMI display"),
    ("HMI_Sump_Cycle_Count", "Pump cycle count for HMI"),
    ("HMI_Sump_Total_Run_Hours", "Pump total run hours for HMI"),
    ("HMI_Sump_Last_Run_Seconds", "Last run duration for HMI"),
    ("HMI_HVAC_Cycle_Count", "Furnace cycles for HMI"),
    ("HMI_HVAC_Total_Run_Hours", "Furnace run hours for HMI"),
    ("HMI_HVAC_Last_Run_Seconds", "Last furnace run for HMI"),
    ("HMI_HVAC_Filter_Run_Hours", "Filter hours for HMI"),
    # Feature 1: Exercise Scheduler
    ("Exercise_Schedule_Day", "Exercise day of week 0=Sun 6=Sat", "6"),
    ("Exercise_Schedule_Hour", "Exercise hour of day 0-23", "10"),
    ("Exercise_Duration_Minutes", "Exercise duration in minutes", "15"),
    # Feature 2: Sump Cycle Rate Alarm
    ("Sump_Hourly_Cycle_Count", "Sump pump starts in current hour"),
    ("Sump_Hourly_Seconds", "Seconds counter for hourly cycle rate"),
    ("Sump_Cycle_Rate_Max", "Max sump cycles per hour before alarm", "10"),
    # Feature 10: Garage Door Monitor
    ("Garage_Open_Seconds", "Garage door open duration seconds"),
    ("Garage_Open_Max_Seconds", "Max garage open seconds before alarm", "1800"),
    # Feature 11: Well Pump / Water Pressure
    ("Well_Pump_Cycle_Count", "Total well pump cycles"),
    ("Well_Pump_Current_Run_Seconds", "Current well pump run seconds"),
    ("Well_Pump_Last_Run_Seconds", "Last well pump run duration seconds"),
    ("Well_Pump_Short_Cycle_Count", "Consecutive well pump short cycles"),
    ("Well_Pump_Min_Run_Seconds", "Minimum expected well pump run seconds", "30"),
    # Feature 8: Maintenance Schedules
    ("Maint_Gen_Oil_Hours", "Gen oil change interval hours", "200"),
    ("Maint_Gen_Run_Since_Oil", "Gen run seconds since last oil change"),
    ("Maint_Sump_Inspect_Cycles", "Sump inspect interval cycles", "500"),
    ("Maint_Sump_Cycles_Since_Inspect", "Sump cycles since last inspection"),
    ("Maint_Furnace_Inspect_Hours", "Furnace inspect interval hours", "1000"),
    ("Maint_Furnace_Run_Since_Inspect", "Furnace run seconds since last inspection"),
    ("Maint_Gen_Hours_Since_Oil", "Gen hours since oil change"),
    ("Maint_Furnace_Hours_Since_Inspect", "Furnace hours since inspection"),
    # Feature 7: HVAC Efficiency
    ("HVAC_Daily_Run_Seconds", "Daily furnace run seconds for efficiency calc"),
    ("HVAC_HDD_Hourly_Seconds", "Seconds counter for HDD hourly calc"),
    # HMI tags for new features
    ("HMI_Garage_Open_Seconds", "Garage open seconds for HMI"),
    ("HMI_Well_Pump_Cycle_Count", "Well pump cycles for HMI"),
    ("HMI_Well_Pump_Last_Run_Seconds", "Well pump last run for HMI"),
    ("HMI_Maint_Gen_Hours_Since_Oil", "Gen hours since oil for HMI"),
    ("HMI_Maint_Sump_Cycles_Since_Inspect", "Sump cycles since inspect for HMI"),
    ("HMI_Maint_Furnace_Hours_Since_Inspect", "Furnace hours since inspect for HMI"),
]
for entry in dint_tags:
    if len(entry) == 3:
        name, desc, val = entry
        tags.append(dint_tag(name, desc, val))
    else:
        name, desc = entry
        tags.append(dint_tag(name, desc))

# === REAL TAGS ===
real_tags = [
    ("Outdoor_Temp_F", "Scaled outdoor temperature in F", "0.0"),
    ("House_Current_Amps", "Scaled whole house current in amps", "0.0"),
    ("Elec_Current_Amps", "Current whole house amps", "0.0"),
    ("Elec_Peak_Amps", "Peak current since last reset", "0.0"),
    ("Elec_Gen_Max_Amps", "Generator max amp threshold", "80.0"),
    ("Elec_Watt_Seconds", "Accumulated watt-seconds for kWh calc", "0.0"),
    ("Elec_Total_kWh", "Total energy consumed in kWh", "0.0"),
    ("Elec_Watt_Seconds_Temp", "Temp variable for watt calculation", "0.0"),
    ("HVAC_Outdoor_Temp_Min", "Daily outdoor temp minimum", "120.0"),
    ("HVAC_Outdoor_Temp_Max", "Daily outdoor temp maximum", "-40.0"),
    ("HMI_Outdoor_Temp", "Outdoor temp for HMI", "0.0"),
    ("HMI_Outdoor_Temp_Min", "Daily temp min for HMI", "0.0"),
    ("HMI_Outdoor_Temp_Max", "Daily temp max for HMI", "0.0"),
    ("HMI_Elec_Current_Amps", "Current amps for HMI", "0.0"),
    ("HMI_Elec_Peak_Amps", "Peak amps for HMI", "0.0"),
    ("HMI_Elec_Total_kWh", "Total kWh for HMI", "0.0"),
    # Feature 3: Freeze Protection
    ("Freeze_Warning_SP", "Freeze warning setpoint deg F", "35.0"),
    ("Freeze_Critical_SP", "Freeze critical setpoint deg F", "20.0"),
    # Feature 11: Well Pump / Water Pressure
    ("Water_Pressure_PSI", "Scaled water pressure in PSI", "0.0"),
    ("Water_Pressure_Raw", "Raw water pressure intermediate calc", "0.0"),
    ("Water_Pressure_Low_SP", "Water pressure low alarm setpoint PSI", "30.0"),
    # Feature 4: Load Shedding
    ("Load_Shed_Threshold", "Load shed current threshold amps", "70.0"),
    # Feature 7: HVAC Efficiency
    ("HVAC_HDD_Accumulated", "Accumulated heating degree days", "0.0"),
    ("HVAC_HDD_Runtime_Ratio", "Runtime to HDD ratio", "0.0"),
    ("HVAC_HDD_Baseline_Ratio", "Baseline runtime to HDD ratio", "3600.0"),
    ("HVAC_Efficiency_Pct", "HVAC efficiency percentage", "0.0"),
    ("HVAC_Efficiency_Threshold", "HVAC efficiency alarm threshold pct", "130.0"),
    ("HVAC_Daily_HDD", "Daily heating degree days", "0.0"),
    # HMI tags for new features
    ("HMI_Water_Pressure_PSI", "Water pressure for HMI", "0.0"),
    ("HMI_HVAC_Efficiency_Pct", "HVAC efficiency pct for HMI", "0.0"),
]
for name, desc, val in real_tags:
    tags.append(real_tag(name, desc, val))

# === TIMER TAGS ===
timer_tags = [
    ("Power_Loss_Delay", "5s delay to confirm power loss", 5000),
    ("Gen_Start_Timeout", "30s crank timeout", 30000),
    ("Gen_Warmup_Timer", "30s generator warmup", 30000),
    ("Gen_Cooldown_Timer", "2min cooldown before shutdown", 120000),
    ("Gen_Stop_Timeout", "30s stop confirmation timeout", 30000),
    ("Exercise_Run_Timer", "15min exercise run duration", 900000),
    ("Transfer_Delay", "3s ATS transfer delay", 3000),
    ("Gen_Utility_Return_Timer", "5s utility return stability", 5000),
    ("Sump_Debounce", "2s float switch debounce", 2000),
    ("Sump_Max_Run", "5min max pump run time", 300000),
    ("Sump_Off_Delay", "10s pump off delay after float drops", 10000),
    ("Sump_Test_Run_Timer", "15s test run duration", 15000),
    ("Heat_Call_Debounce", "5s thermostat call debounce", 5000),
    ("Short_Cycle_Timer", "3min short cycle detection window", 180000),
    ("Pulse_1s_Timer", "1 second pulse timer", 1000),
    ("Elec_Overload_Timer", "5s sustained overload detection", 5000),
    ("Elec_Gen_Overload_Timer", "3s generator overload detection", 3000),
    # Feature 4: Load Shedding
    ("Load_Shed_Timer", "10s sustained overload for load shed", 10000),
    # Feature 11: Well Pump / Water Pressure
    ("Well_Short_Cycle_Timer", "60s well pump short cycle detection", 60000),
]
for name, desc, preset in timer_tags:
    tags.append(timer_tag(name, desc, preset))

tags_section = "<Tags>\n" + "\n".join(tags) + "\n</Tags>\n"

# ============================================================
# ROUTINES / PROGRAMS SECTION
# ============================================================

def rung(num, comment, text):
    if comment:
        return f'''<Rung Number="{num}" Type="N">
<Comment><![CDATA[{comment}]]></Comment>
<Text><![CDATA[{text}]]></Text>
</Rung>'''
    else:
        return f'''<Rung Number="{num}" Type="N">
<Text><![CDATA[{text}]]></Text>
</Rung>'''

# --- MainRoutine ---
main_rungs = [
    rung(0, "Call Input Mapping", "JSR(Input_Mapping,0);"),
    rung(1, "Call Generator Control", "JSR(Generator_Control,0);"),
    rung(2, "Call Sump Pump Control", "JSR(Sump_Pump_Control,0);"),
    rung(3, "Call HVAC Monitor", "JSR(HVAC_Monitor,0);"),
    rung(4, "Call Electrical Monitor", "JSR(Electrical_Monitor,0);"),
    rung(5, "Call Leak Detection", "JSR(Leak_Detection,0);"),
    rung(6, "Call Garage Monitor", "JSR(Garage_Monitor,0);"),
    rung(7, "Call Well Pump Monitor", "JSR(Well_Pump_Monitor,0);"),
    rung(8, "Call Maintenance Monitor", "JSR(Maintenance_Monitor,0);"),
    rung(9, "Call HMI Interface", "JSR(HMI_Interface,0);"),
    rung(10, "Call Output Mapping", "JSR(Output_Mapping,0);"),
]

# --- Input_Mapping ---
input_rungs = [
    rung(0, "Pt00: Utility power present", "XIC(Local:1:I.Pt00.Data)OTE(Utility_Power_Present);"),
    rung(1, "Pt01: Generator running feedback", "XIC(Local:1:I.Pt01.Data)OTE(Gen_Running);"),
    rung(2, "Pt02: Generator fault", "XIC(Local:1:I.Pt02.Data)OTE(Gen_Fault);"),
    rung(3, "Pt03: Generator ready", "XIC(Local:1:I.Pt03.Data)OTE(Gen_Ready);"),
    rung(4, "Pt04: ATS utility position", "XIC(Local:1:I.Pt04.Data)OTE(ATS_Utility_Pos);"),
    rung(5, "Pt05: ATS generator position", "XIC(Local:1:I.Pt05.Data)OTE(ATS_Generator_Pos);"),
    rung(6, "Pt06: Sump pit float switch", "XIC(Local:1:I.Pt06.Data)OTE(Sump_Float_High);"),
    rung(7, "Pt07: Thermostat heat call", "XIC(Local:1:I.Pt07.Data)OTE(Thermostat_W_Call);"),
    rung(8, "Outdoor temp: subtract 20% offset (4mA on 0-20mA range)", "SUB(Local:3:I.Ch00.Data,20.0,Outdoor_Temp_F);"),
    rung(9, "Outdoor temp: scale 0-80% to -40 to 120F (x2.0 - 40)", "MUL(Outdoor_Temp_F,2.0,Outdoor_Temp_F);"),
    rung(10, "Outdoor temp: offset -40F", "SUB(Outdoor_Temp_F,40.0,Outdoor_Temp_F);"),
    rung(11, "House current: subtract 20% offset (4mA on 0-20mA range)", "SUB(Local:3:I.Ch01.Data,20.0,House_Current_Amps);"),
    rung(12, "House current: scale 0-80% to 0-200A (x2.5)", "MUL(House_Current_Amps,2.5,House_Current_Amps);"),
    rung(13, "Clamp outdoor temp low", "LES(Outdoor_Temp_F,-40.0)MOV(-40.0,Outdoor_Temp_F);"),
    rung(14, "Clamp outdoor temp high", "GRT(Outdoor_Temp_F,120.0)MOV(120.0,Outdoor_Temp_F);"),
    rung(15, "Clamp current low", "LES(House_Current_Amps,0.0)MOV(0.0,House_Current_Amps);"),
    rung(16, "Clamp current high", "GRT(House_Current_Amps,200.0)MOV(200.0,House_Current_Amps);"),
    # Feature 9: Water Leak Detection inputs
    rung(17, "Pt08: Leak sensor zone 1", "XIC(Local:1:I.Pt08.Data)OTE(Leak_Zone1);"),
    rung(18, "Pt09: Leak sensor zone 2", "XIC(Local:1:I.Pt09.Data)OTE(Leak_Zone2);"),
    rung(19, "Pt10: Leak sensor zone 3", "XIC(Local:1:I.Pt10.Data)OTE(Leak_Zone3);"),
    # Feature 10: Garage Door input (NC switch)
    rung(20, "Pt11: Garage door closed limit switch NC", "XIC(Local:1:I.Pt11.Data)OTE(Garage_Door_Closed);"),
    # Feature 11: Well Pump input
    rung(21, "Pt12: Well pump running feedback", "XIC(Local:1:I.Pt12.Data)OTE(Well_Pump_Running);"),
    # Feature 11: Water pressure analog scaling Ch02 (4-20mA = 0-100 PSI)
    rung(22, "Water pressure: subtract 20% offset (4mA)", "SUB(Local:3:I.Ch02.Data,20.0,Water_Pressure_Raw);"),
    rung(23, "Water pressure: scale to 0-100 PSI (x1.25)", "MUL(Water_Pressure_Raw,1.25,Water_Pressure_PSI);"),
    rung(24, "Clamp water pressure low", "LES(Water_Pressure_PSI,0.0)MOV(0.0,Water_Pressure_PSI);"),
    rung(25, "Clamp water pressure high", "GRT(Water_Pressure_PSI,100.0)MOV(100.0,Water_Pressure_PSI);"),
]

# --- Generator_Control ---
gen_rungs = [
    # Timers
    rung(0, "Power loss confirm delay 5s", "XIO(Utility_Power_Present)TON(Power_Loss_Delay,5000,0);"),
    rung(1, "Generator crank timeout 30s", "[EQU(Gen_State,20),EQU(Gen_State,95)]TON(Gen_Start_Timeout,30000,0);"),
    rung(2, "Generator warmup 30s", "EQU(Gen_State,30)TON(Gen_Warmup_Timer,30000,0);"),
    rung(3, "Generator cooldown 120s", "[EQU(Gen_State,60),EQU(Gen_State,105)]TON(Gen_Cooldown_Timer,120000,0);"),
    rung(4, "Generator stop timeout 30s", "[EQU(Gen_State,70),EQU(Gen_State,110)]TON(Gen_Stop_Timeout,30000,0);"),
    rung(5, "Exercise run timer 15min", "EQU(Gen_State,100)TON(Exercise_Run_Timer,900000,0);"),
    rung(6, "ATS transfer delay 3s", "EQU(Gen_State,40)TON(Transfer_Delay,3000,0);"),
    rung(7, "Utility return stability 5s", "EQU(Gen_State,50)XIC(Utility_Power_Present)TON(Gen_Utility_Return_Timer,5000,0);"),
    # 1-second pulse
    rung(8, "1-second pulse timer", "XIO(Pulse_1s)TON(Pulse_1s_Timer,1000,0);"),
    rung(9, "1-second pulse output", "XIC(Pulse_1s_Timer.DN)OTE(Pulse_1s);"),
    # Exercise schedule
    rung(10, "Count seconds for weekly exercise schedule", "XIC(Pulse_1s)ONS(Exercise_Count_ONS)ADD(Exercise_Seconds,1,Exercise_Seconds);"),
    rung(11, "Trigger exercise at 1 week (604800s)", "GEQ(Exercise_Seconds,604800)OTL(Exercise_Trigger);"),
    rung(12, "Reset exercise second counter after trigger", "XIC(Exercise_Trigger)MOV(0,Exercise_Seconds);"),
    rung(13, "HMI manual exercise request", "XIC(HMI_Exercise_Request)OTL(Exercise_Trigger);"),
    rung(14, "Clear HMI exercise request", "XIC(HMI_Exercise_Request)OTU(HMI_Exercise_Request);"),
    # Feature 1: Set exercise run timer preset dynamically from minutes setting
    rung(15, "Set exercise timer preset from duration setting", "EQU(Gen_State,0)MUL(Exercise_Duration_Minutes,60000,Exercise_Run_Timer.PRE);"),
    # Output control rungs - ONE OTE per output tag
    rung(16, "Gen start cmd - active in run/warmup/transfer/exercise states",
         "[EQU(Gen_State,10),EQU(Gen_State,20),EQU(Gen_State,30),EQU(Gen_State,40),EQU(Gen_State,50),EQU(Gen_State,55),EQU(Gen_State,60),EQU(Gen_State,90),EQU(Gen_State,95),EQU(Gen_State,100),EQU(Gen_State,105)]OTE(Gen_Start_Cmd);"),
    rung(17, "ATS transfer cmd - active during generator operation",
         "[EQU(Gen_State,40),EQU(Gen_State,50)]OTE(ATS_Transfer_Cmd);"),
    rung(18, "On utility power flag",
         "[EQU(Gen_State,0),EQU(Gen_State,55),EQU(Gen_State,60),EQU(Gen_State,70),EQU(Gen_State,90),EQU(Gen_State,95),EQU(Gen_State,100),EQU(Gen_State,105),EQU(Gen_State,110),EQU(Gen_State,999)]OTE(Gen_On_Utility);"),
    rung(19, "On generator power flag", "EQU(Gen_State,50)OTE(Gen_On_Generator);"),
    rung(20, "Exercise active flag",
         "[EQU(Gen_State,90),EQU(Gen_State,95),EQU(Gen_State,100),EQU(Gen_State,105)]OTE(Gen_Exercise_Active);"),
    # State transitions
    rung(21, "State 0->10: Power loss confirmed", "EQU(Gen_State,0)XIC(Power_Loss_Delay.DN)MOV(10,Gen_State);"),
    rung(22, "State 0->90: Exercise trigger, no fault", "EQU(Gen_State,0)XIC(Exercise_Trigger)XIO(Gen_Fault)XIO(Power_Loss_Delay.DN)MOV(90,Gen_State);"),
    rung(23, "State 90: Clear exercise trigger", "EQU(Gen_State,90)OTU(Exercise_Trigger);"),
    rung(24, "State 10->20: Start commanded", "EQU(Gen_State,10)MOV(20,Gen_State);"),
    rung(25, "State 20->30: Generator running confirmed", "EQU(Gen_State,20)XIC(Gen_Running)MOV(30,Gen_State);"),
    rung(26, "State 20: Increment crank attempts on timeout", "EQU(Gen_State,20)XIC(Gen_Start_Timeout.DN)ONS(Crank_Attempt_ONS)ADD(Gen_Crank_Attempts,1,Gen_Crank_Attempts);"),
    rung(27, "State 20->999: Start fail after 3 attempts", "EQU(Gen_State,20)XIC(Gen_Start_Timeout.DN)GEQ(Gen_Crank_Attempts,3)OTL(Gen_Start_Fail);"),
    rung(28, None, "EQU(Gen_State,20)XIC(Gen_Start_Timeout.DN)GEQ(Gen_Crank_Attempts,3)MOV(999,Gen_State);"),
    rung(29, "State 20->10: Retry start (under 3 attempts)", "EQU(Gen_State,20)XIC(Gen_Start_Timeout.DN)LES(Gen_Crank_Attempts,3)MOV(10,Gen_State);"),
    rung(30, "State 30->40: Warmup complete", "EQU(Gen_State,30)XIC(Gen_Warmup_Timer.DN)MOV(40,Gen_State);"),
    rung(31, "State 30->999: Fault during warmup", "EQU(Gen_State,30)XIC(Gen_Fault)MOV(999,Gen_State);"),
    rung(32, "State 40->50: ATS transfer confirmed", "EQU(Gen_State,40)XIC(Transfer_Delay.DN)XIC(ATS_Generator_Pos)MOV(50,Gen_State);"),
    rung(33, "State 40->999: Fault during transfer", "EQU(Gen_State,40)XIC(Gen_Fault)MOV(999,Gen_State);"),
    rung(34, "State 50: Track generator run time", "EQU(Gen_State,50)XIC(Pulse_1s)ADD(Gen_Total_Run_Seconds,1,Gen_Total_Run_Seconds);"),
    rung(35, "State 50->55: Utility returned stable 5s", "EQU(Gen_State,50)XIC(Gen_Utility_Return_Timer.DN)MOV(55,Gen_State);"),
    rung(36, "State 50->999: Fault while on generator", "EQU(Gen_State,50)XIC(Gen_Fault)MOV(999,Gen_State);"),
    rung(37, "State 55->60: ATS back to utility confirmed", "EQU(Gen_State,55)XIC(ATS_Utility_Pos)MOV(60,Gen_State);"),
    rung(38, "State 60->70: Cooldown complete", "EQU(Gen_State,60)XIC(Gen_Cooldown_Timer.DN)MOV(70,Gen_State);"),
    rung(39, "State 70: Clear crank attempts on successful stop", "EQU(Gen_State,70)XIO(Gen_Running)MOV(0,Gen_Crank_Attempts);"),
    rung(40, "State 70->0: Generator stopped", "EQU(Gen_State,70)XIO(Gen_Running)MOV(0,Gen_State);"),
    rung(41, "State 70->999: Stop timeout", "EQU(Gen_State,70)XIC(Gen_Stop_Timeout.DN)OTL(Gen_Stop_Fail);"),
    rung(42, None, "EQU(Gen_State,70)XIC(Gen_Stop_Timeout.DN)MOV(999,Gen_State);"),
    rung(43, "State 90->95: Exercise start transition", "EQU(Gen_State,90)MOV(95,Gen_State);"),
    rung(44, "State 95->100: Exercise generator running", "EQU(Gen_State,95)XIC(Gen_Running)MOV(100,Gen_State);"),
    rung(45, "State 95->999: Exercise start timeout", "EQU(Gen_State,95)XIC(Gen_Start_Timeout.DN)OTL(Gen_Start_Fail);"),
    rung(46, None, "EQU(Gen_State,95)XIC(Gen_Start_Timeout.DN)MOV(999,Gen_State);"),
    rung(47, "State 100: Track exercise run time", "EQU(Gen_State,100)XIC(Pulse_1s)ADD(Gen_Total_Run_Seconds,1,Gen_Total_Run_Seconds);"),
    rung(48, "State 100->105: Exercise run complete", "EQU(Gen_State,100)XIC(Exercise_Run_Timer.DN)MOV(105,Gen_State);"),
    rung(49, "State 100->30: Power loss during exercise - switch to real operation", "EQU(Gen_State,100)XIO(Utility_Power_Present)MOV(30,Gen_State);"),
    rung(50, "State 100->999: Fault during exercise", "EQU(Gen_State,100)XIC(Gen_Fault)MOV(999,Gen_State);"),
    rung(51, "State 105->110: Exercise cooldown complete", "EQU(Gen_State,105)XIC(Gen_Cooldown_Timer.DN)MOV(110,Gen_State);"),
    rung(52, "State 110: Clear crank attempts on exercise shutdown", "EQU(Gen_State,110)XIO(Gen_Running)MOV(0,Gen_Crank_Attempts);"),
    rung(53, "State 110->0: Exercise shutdown complete", "EQU(Gen_State,110)XIO(Gen_Running)MOV(0,Gen_State);"),
    rung(54, "State 110->999: Exercise stop timeout", "EQU(Gen_State,110)XIC(Gen_Stop_Timeout.DN)OTL(Gen_Stop_Fail);"),
    rung(55, None, "EQU(Gen_State,110)XIC(Gen_Stop_Timeout.DN)MOV(999,Gen_State);"),
    # Fault reset
    rung(56, "Fault reset from HMI - clear start fail", "XIC(HMI_Gen_Fault_Reset)XIO(Gen_Fault)OTU(Gen_Start_Fail);"),
    rung(57, "Fault reset - clear stop fail", "XIC(HMI_Gen_Fault_Reset)XIO(Gen_Fault)OTU(Gen_Stop_Fail);"),
    rung(58, "Fault reset - clear crank attempts", "XIC(HMI_Gen_Fault_Reset)XIO(Gen_Fault)MOV(0,Gen_Crank_Attempts);"),
    rung(59, "Fault reset - return to idle", "XIC(HMI_Gen_Fault_Reset)XIO(Gen_Fault)MOV(0,Gen_State);"),
    rung(60, "Clear HMI fault reset", "XIC(HMI_Gen_Fault_Reset)OTU(HMI_Gen_Fault_Reset);"),
]

# --- Sump_Pump_Control ---
sump_rungs = [
    # Timers
    rung(0, "Float switch debounce 2s", "XIC(Sump_Float_High)TON(Sump_Debounce,2000,0);"),
    rung(1, "Max pump run time 5min", "XIC(Sump_Pump_Run)TON(Sump_Max_Run,300000,0);"),
    rung(2, "Pump off delay 10s after float drops", "XIO(Sump_Float_High)XIC(Sump_Pump_Run)TON(Sump_Off_Delay,10000,0);"),
    rung(3, "Test run timer 15s", "EQU(Sump_State,30)TON(Sump_Test_Run_Timer,15000,0);"),
    # Weekly test schedule
    rung(4, "Count seconds for weekly sump test", "XIC(Pulse_1s)ADD(Sump_Test_Seconds,1,Sump_Test_Seconds);"),
    rung(5, "Trigger sump test at 1 week", "GEQ(Sump_Test_Seconds,604800)OTL(Sump_Test_Trigger);"),
    rung(6, "Reset sump test counter after trigger", "XIC(Sump_Test_Trigger)MOV(0,Sump_Test_Seconds);"),
    rung(7, "HMI manual sump test request", "XIC(HMI_Sump_Test_Request)OTL(Sump_Test_Trigger);"),
    rung(8, "Clear HMI sump test request", "XIC(HMI_Sump_Test_Request)OTU(HMI_Sump_Test_Request);"),
    # State transitions
    rung(9, "State 0->10: Float debounced high", "EQU(Sump_State,0)XIC(Sump_Debounce.DN)MOV(10,Sump_State);"),
    rung(10, "State 0->30: Test triggered", "EQU(Sump_State,0)XIC(Sump_Test_Trigger)XIO(Sump_Debounce.DN)MOV(30,Sump_State);"),
    rung(11, "Clear test trigger on entry", "EQU(Sump_State,30)OTU(Sump_Test_Trigger);"),
    rung(12, "State 10: Count pump cycle", "EQU(Sump_State,10)ONS(Sump_Cycle_ONS)ADD(Sump_Cycle_Count,1,Sump_Cycle_Count);"),
    rung(13, "State 10->20: Start pumping", "EQU(Sump_State,10)MOV(20,Sump_State);"),
    rung(14, "State 20: Track current run time", "EQU(Sump_State,20)XIC(Pulse_1s)ADD(Sump_Current_Run_Seconds,1,Sump_Current_Run_Seconds);"),
    rung(15, "State 20: Track total run time", "EQU(Sump_State,20)XIC(Pulse_1s)ADD(Sump_Total_Run_Seconds,1,Sump_Total_Run_Seconds);"),
    # Max run fault (check before normal completion)
    rung(16, "State 20->999: Max run time exceeded - set fault", "EQU(Sump_State,20)XIC(Sump_Max_Run.DN)OTL(Sump_Max_Run_Fault);"),
    rung(17, "State 20: Save last run on fault", "EQU(Sump_State,20)XIC(Sump_Max_Run.DN)MOV(Sump_Current_Run_Seconds,Sump_Last_Run_Seconds);"),
    rung(18, "State 20: Clear current run on fault", "EQU(Sump_State,20)XIC(Sump_Max_Run.DN)MOV(0,Sump_Current_Run_Seconds);"),
    rung(19, "State 20->999: Transition to fault", "EQU(Sump_State,20)XIC(Sump_Max_Run.DN)MOV(999,Sump_State);"),
    # Normal completion
    rung(20, "State 20: Save last run on completion", "EQU(Sump_State,20)XIC(Sump_Off_Delay.DN)MOV(Sump_Current_Run_Seconds,Sump_Last_Run_Seconds);"),
    rung(21, "State 20: Clear current run on completion", "EQU(Sump_State,20)XIC(Sump_Off_Delay.DN)MOV(0,Sump_Current_Run_Seconds);"),
    rung(22, "State 20->0: Float dropped, off delay done", "EQU(Sump_State,20)XIC(Sump_Off_Delay.DN)MOV(0,Sump_State);"),
    # Test run states
    rung(23, "State 30: Set test active", "EQU(Sump_State,30)OTL(Sump_Test_Active);"),
    rung(24, "State 30->0: Test complete - clear active", "EQU(Sump_State,30)XIC(Sump_Test_Run_Timer.DN)OTU(Sump_Test_Active);"),
    rung(25, "State 30: Set last test OK", "EQU(Sump_State,30)XIC(Sump_Test_Run_Timer.DN)OTL(Sump_Last_Test_OK);"),
    rung(26, "State 30->0: Test complete transition", "EQU(Sump_State,30)XIC(Sump_Test_Run_Timer.DN)MOV(0,Sump_State);"),
    rung(27, "State 30->20: Real high water during test", "EQU(Sump_State,30)XIC(Sump_Float_High)XIO(Sump_Test_Run_Timer.DN)OTU(Sump_Test_Active);"),
    rung(28, None, "EQU(Sump_State,30)XIC(Sump_Float_High)XIO(Sump_Test_Run_Timer.DN)MOV(20,Sump_State);"),
    # Pump output - single OTE
    rung(29, "Sump pump run output",
         "[EQU(Sump_State,10),EQU(Sump_State,20),EQU(Sump_State,30),EQU(Sump_State,999)XIC(Sump_Float_High)]OTE(Sump_Pump_Run);"),
    # Fault reset
    rung(30, "Sump fault reset from HMI", "XIC(HMI_Sump_Fault_Reset)OTU(Sump_Max_Run_Fault);"),
    rung(31, "Sump fault reset - clear cycle rate alarm", "XIC(HMI_Sump_Fault_Reset)OTU(Sump_Cycle_Rate_Alarm);"),
    rung(32, None, "XIC(HMI_Sump_Fault_Reset)MOV(0,Sump_State);"),
    rung(33, None, "XIC(HMI_Sump_Fault_Reset)OTU(HMI_Sump_Fault_Reset);"),
    # Feature 2: Sump Cycle Rate Alarm - count pump starts per hour
    rung(34, "Count hourly seconds", "XIC(Pulse_1s)ADD(Sump_Hourly_Seconds,1,Sump_Hourly_Seconds);"),
    rung(35, "One-shot trigger: pump entering state 10", "EQU(Sump_State,10)XIO(Sump_Cycle_Rate_ONS)ADD(Sump_Hourly_Cycle_Count,1,Sump_Hourly_Cycle_Count);"),
    rung(36, "Set one-shot bit when in state 10", "EQU(Sump_State,10)OTL(Sump_Cycle_Rate_ONS);"),
    rung(37, "Clear one-shot bit when not in state 10", "NEQ(Sump_State,10)OTU(Sump_Cycle_Rate_ONS);"),
    rung(38, "Reset hourly counter at 3600 seconds", "GEQ(Sump_Hourly_Seconds,3600)MOV(0,Sump_Hourly_Cycle_Count);"),
    rung(39, "Reset hourly seconds at 3600", "GEQ(Sump_Hourly_Seconds,3600)MOV(0,Sump_Hourly_Seconds);"),
    rung(40, "Cycle rate alarm when count exceeds max", "GEQ(Sump_Hourly_Cycle_Count,Sump_Cycle_Rate_Max)OTL(Sump_Cycle_Rate_Alarm);"),
]

# --- HVAC_Monitor ---
hvac_rungs = [
    # Timers
    rung(0, "Heat call debounce 5s", "XIC(Thermostat_W_Call)TON(Heat_Call_Debounce,5000,0);"),
    rung(1, "Short cycle detection window 3min", "XIO(Thermostat_W_Call)XIC(HVAC_Was_Running)TON(Short_Cycle_Timer,180000,0);"),
    # Furnace start detection (XIO before latch provides one-shot)
    rung(2, "Count furnace cycle on start", "XIC(Heat_Call_Debounce.DN)XIO(HVAC_Furnace_Running)ADD(HVAC_Cycle_Count,1,HVAC_Cycle_Count);"),
    rung(3, "Clear current run seconds on start", "XIC(Heat_Call_Debounce.DN)XIO(HVAC_Furnace_Running)MOV(0,HVAC_Current_Run_Seconds);"),
    rung(4, "Short cycle check - restart within 3min window", "XIC(Heat_Call_Debounce.DN)XIO(HVAC_Furnace_Running)XIC(Short_Cycle_Timer.TT)ADD(HVAC_Short_Cycle_Count,1,HVAC_Short_Cycle_Count);"),
    rung(5, "Clear short cycle count if not short cycling", "XIC(Heat_Call_Debounce.DN)XIO(HVAC_Furnace_Running)XIO(Short_Cycle_Timer.TT)MOV(0,HVAC_Short_Cycle_Count);"),
    rung(6, "Short cycle alarm at 3 consecutive", "GEQ(HVAC_Short_Cycle_Count,3)OTL(HVAC_Short_Cycle_Alarm);"),
    rung(7, "Latch furnace running", "XIC(Heat_Call_Debounce.DN)OTL(HVAC_Furnace_Running);"),
    # Furnace shutdown detection
    rung(8, "Save last run on shutdown", "XIO(Thermostat_W_Call)XIC(HVAC_Furnace_Running)MOV(HVAC_Current_Run_Seconds,HVAC_Last_Run_Seconds);"),
    rung(9, "Set was running flag", "XIO(Thermostat_W_Call)XIC(HVAC_Furnace_Running)OTL(HVAC_Was_Running);"),
    rung(10, "Clear furnace running on shutdown", "XIO(Thermostat_W_Call)OTU(HVAC_Furnace_Running);"),
    rung(11, "Clear was running after short cycle window", "XIC(Short_Cycle_Timer.DN)OTU(HVAC_Was_Running);"),
    # Run time tracking
    rung(12, "Track current furnace run time", "XIC(HVAC_Furnace_Running)XIC(Pulse_1s)ADD(HVAC_Current_Run_Seconds,1,HVAC_Current_Run_Seconds);"),
    rung(13, "Track total furnace run time", "XIC(HVAC_Furnace_Running)XIC(Pulse_1s)ADD(HVAC_Total_Run_Seconds,1,HVAC_Total_Run_Seconds);"),
    rung(14, "Track filter run time", "XIC(HVAC_Furnace_Running)XIC(Pulse_1s)ADD(HVAC_Filter_Run_Seconds,1,HVAC_Filter_Run_Seconds);"),
    rung(15, "Filter change due at 300 hours (1080000s)", "GEQ(HVAC_Filter_Run_Seconds,1080000)OTL(HVAC_Filter_Change_Due);"),
    # HMI resets
    rung(16, "HMI filter reset - clear hours", "XIC(HMI_Filter_Reset)MOV(0,HVAC_Filter_Run_Seconds);"),
    rung(17, "HMI filter reset - clear flag", "XIC(HMI_Filter_Reset)OTU(HVAC_Filter_Change_Due);"),
    rung(18, None, "XIC(HMI_Filter_Reset)OTU(HMI_Filter_Reset);"),
    # Outdoor temp tracking
    rung(19, "Track outdoor temp minimum", "LES(Outdoor_Temp_F,HVAC_Outdoor_Temp_Min)MOV(Outdoor_Temp_F,HVAC_Outdoor_Temp_Min);"),
    rung(20, "Track outdoor temp maximum", "GRT(Outdoor_Temp_F,HVAC_Outdoor_Temp_Max)MOV(Outdoor_Temp_F,HVAC_Outdoor_Temp_Max);"),
    rung(21, "HMI min/max reset", "XIC(HMI_Temp_MinMax_Reset)MOV(Outdoor_Temp_F,HVAC_Outdoor_Temp_Min);"),
    rung(22, None, "XIC(HMI_Temp_MinMax_Reset)MOV(Outdoor_Temp_F,HVAC_Outdoor_Temp_Max);"),
    rung(23, None, "XIC(HMI_Temp_MinMax_Reset)OTU(HMI_Temp_MinMax_Reset);"),
    rung(24, "HMI HVAC alarm reset", "XIC(HMI_HVAC_Alarm_Reset)OTU(HVAC_Short_Cycle_Alarm);"),
    rung(25, None, "XIC(HMI_HVAC_Alarm_Reset)MOV(0,HVAC_Short_Cycle_Count);"),
    rung(26, None, "XIC(HMI_HVAC_Alarm_Reset)OTU(HMI_HVAC_Alarm_Reset);"),
    # Feature 3: Freeze Protection
    rung(27, "Freeze warning when temp at or below warning setpoint", "LEQ(Outdoor_Temp_F,Freeze_Warning_SP)OTL(Freeze_Warning);"),
    rung(28, "Freeze critical when temp at or below critical setpoint", "LEQ(Outdoor_Temp_F,Freeze_Critical_SP)OTL(Freeze_Critical);"),
    rung(29, "Clear freeze warning when temp above warning SP and HMI reset", "XIC(HMI_Freeze_Alarm_Reset)GRT(Outdoor_Temp_F,Freeze_Warning_SP)OTU(Freeze_Warning);"),
    rung(30, "Clear freeze critical when temp above critical SP and HMI reset", "XIC(HMI_Freeze_Alarm_Reset)GRT(Outdoor_Temp_F,Freeze_Critical_SP)OTU(Freeze_Critical);"),
    rung(31, "Clear HMI freeze alarm reset", "XIC(HMI_Freeze_Alarm_Reset)OTU(HMI_Freeze_Alarm_Reset);"),
    # Feature 7: HVAC Efficiency
    rung(32, "Track daily furnace run seconds", "XIC(HVAC_Furnace_Running)XIC(Pulse_1s)ADD(HVAC_Daily_Run_Seconds,1,HVAC_Daily_Run_Seconds);"),
    rung(33, "Count HDD hourly seconds", "XIC(Pulse_1s)ADD(HVAC_HDD_Hourly_Seconds,1,HVAC_HDD_Hourly_Seconds);"),
    rung(34, "Accumulate HDD hourly: HDD += max(0,(65-temp)/24) every 3600s", "GEQ(HVAC_HDD_Hourly_Seconds,3600)SUB(65.0,Outdoor_Temp_F,HVAC_Daily_HDD);"),
    rung(35, "HDD: divide by 24 for hourly fraction", "GEQ(HVAC_HDD_Hourly_Seconds,3600)DIV(HVAC_Daily_HDD,24.0,HVAC_Daily_HDD);"),
    rung(36, "HDD: clamp negative to zero", "LES(HVAC_Daily_HDD,0.0)MOV(0.0,HVAC_Daily_HDD);"),
    rung(37, "HDD: add hourly fraction to accumulated", "GEQ(HVAC_HDD_Hourly_Seconds,3600)ADD(HVAC_HDD_Accumulated,HVAC_Daily_HDD,HVAC_HDD_Accumulated);"),
    rung(38, "HDD: reset hourly seconds counter", "GEQ(HVAC_HDD_Hourly_Seconds,3600)MOV(0,HVAC_HDD_Hourly_Seconds);"),
    rung(39, "Compute runtime to HDD ratio (avoid div by zero)", "GRT(HVAC_HDD_Accumulated,0.0)DIV(HVAC_Daily_Run_Seconds,HVAC_HDD_Accumulated,HVAC_HDD_Runtime_Ratio);"),
    rung(40, "Compute efficiency pct = ratio/baseline * 100", "GRT(HVAC_HDD_Baseline_Ratio,0.0)DIV(HVAC_HDD_Runtime_Ratio,HVAC_HDD_Baseline_Ratio,HVAC_Efficiency_Pct);"),
    rung(41, "Scale efficiency to percentage", "MUL(HVAC_Efficiency_Pct,100.0,HVAC_Efficiency_Pct);"),
    rung(42, "Efficiency alarm when above threshold", "GRT(HVAC_Efficiency_Pct,HVAC_Efficiency_Threshold)OTL(HVAC_Efficiency_Alarm);"),
    rung(43, "HMI efficiency reset - clear accumulated data", "XIC(HMI_HVAC_Efficiency_Reset)MOV(0,HVAC_Daily_Run_Seconds);"),
    rung(44, None, "XIC(HMI_HVAC_Efficiency_Reset)MOV(0.0,HVAC_HDD_Accumulated);"),
    rung(45, None, "XIC(HMI_HVAC_Efficiency_Reset)MOV(0.0,HVAC_Efficiency_Pct);"),
    rung(46, None, "XIC(HMI_HVAC_Efficiency_Reset)OTU(HVAC_Efficiency_Alarm);"),
    rung(47, None, "XIC(HMI_HVAC_Efficiency_Reset)OTU(HMI_HVAC_Efficiency_Reset);"),
]

# --- Electrical_Monitor ---
elec_rungs = [
    rung(0, "Copy current reading", "MOV(House_Current_Amps,Elec_Current_Amps);"),
    rung(1, "Track peak current", "GRT(Elec_Current_Amps,Elec_Peak_Amps)MOV(Elec_Current_Amps,Elec_Peak_Amps);"),
    rung(2, "Overload timer - sustained >180A for 5s", "GRT(Elec_Current_Amps,180.0)TON(Elec_Overload_Timer,5000,0);"),
    rung(3, "Set overload alarm", "XIC(Elec_Overload_Timer.DN)OTL(Elec_Overload_Alarm);"),
    rung(4, "Generator overload - sustained above threshold for 3s", "XIC(Gen_On_Generator)GRT(Elec_Current_Amps,Elec_Gen_Max_Amps)TON(Elec_Gen_Overload_Timer,3000,0);"),
    rung(5, "Set generator overload alarm", "XIC(Elec_Gen_Overload_Timer.DN)OTL(Elec_Gen_Overload_Alarm);"),
    rung(6, "Calculate watts this second", "XIC(Pulse_1s)MUL(Elec_Current_Amps,240.0,Elec_Watt_Seconds_Temp);"),
    rung(7, "Add to watt-seconds accumulator", "XIC(Pulse_1s)ADD(Elec_Watt_Seconds,Elec_Watt_Seconds_Temp,Elec_Watt_Seconds);"),
    rung(8, "Convert to kWh at 3600000 watt-seconds", "GEQ(Elec_Watt_Seconds,3600000.0)ADD(Elec_Total_kWh,1.0,Elec_Total_kWh);"),
    rung(9, "Subtract 3600000 from accumulator", "GEQ(Elec_Watt_Seconds,3600000.0)SUB(Elec_Watt_Seconds,3600000.0,Elec_Watt_Seconds);"),
    rung(10, "HMI peak current reset", "XIC(HMI_Elec_Peak_Reset)MOV(0.0,Elec_Peak_Amps);"),
    rung(11, None, "XIC(HMI_Elec_Peak_Reset)OTU(HMI_Elec_Peak_Reset);"),
    rung(12, "HMI electrical alarm reset", "XIC(HMI_Elec_Alarm_Reset)OTU(Elec_Overload_Alarm);"),
    rung(13, None, "XIC(HMI_Elec_Alarm_Reset)OTU(Elec_Gen_Overload_Alarm);"),
    rung(14, None, "XIC(HMI_Elec_Alarm_Reset)OTU(HMI_Elec_Alarm_Reset);"),
    # Feature 4: Load Shedding
    rung(15, "Load shed timer - on generator and above threshold for 10s", "XIC(Gen_On_Generator)GRT(Elec_Current_Amps,Load_Shed_Threshold)TON(Load_Shed_Timer,10000,0);"),
    rung(16, "Latch load shed active", "XIC(Load_Shed_Timer.DN)OTL(Load_Shed_Active);"),
    rung(17, "Auto-clear load shed when not on generator or HMI reset", "[XIO(Gen_On_Generator),XIC(HMI_Load_Shed_Reset)]OTU(Load_Shed_Active);"),
    rung(18, "Clear HMI load shed reset", "XIC(HMI_Load_Shed_Reset)OTU(HMI_Load_Shed_Reset);"),
    rung(19, "Load shed HVAC output", "XIC(Load_Shed_Active)OTE(Load_Shed_HVAC);"),
    rung(20, "Load shed non-critical 1 output", "XIC(Load_Shed_Active)OTE(Load_Shed_NonCritical1);"),
    rung(21, "Load shed non-critical 2 output", "XIC(Load_Shed_Active)OTE(Load_Shed_NonCritical2);"),
]

# --- HMI_Interface ---
hmi_rungs = [
    rung(0, "Generator state to HMI", "MOV(Gen_State,HMI_Gen_State);"),
    rung(1, "Generator running to HMI", "XIC(Gen_Running)OTE(HMI_Gen_Running);"),
    rung(2, "On utility to HMI", "XIC(Gen_On_Utility)OTE(HMI_Gen_On_Utility);"),
    rung(3, "On generator to HMI", "XIC(Gen_On_Generator)OTE(HMI_Gen_On_Generator);"),
    rung(4, "Exercise active to HMI", "XIC(Gen_Exercise_Active)OTE(HMI_Gen_Exercise_Active);"),
    rung(5, "Start fail alarm to HMI", "XIC(Gen_Start_Fail)OTE(HMI_Gen_Start_Fail_Alarm);"),
    rung(6, "Stop fail alarm to HMI", "XIC(Gen_Stop_Fail)OTE(HMI_Gen_Stop_Fail_Alarm);"),
    rung(7, "Gen fault alarm to HMI", "XIC(Gen_Fault)OTE(HMI_Gen_Fault_Alarm);"),
    rung(8, "Utility present to HMI", "XIC(Utility_Power_Present)OTE(HMI_Utility_Present);"),
    rung(9, "Gen run hours to HMI (seconds / 3600)", "DIV(Gen_Total_Run_Seconds,3600,HMI_Gen_Total_Run_Hours);"),
    rung(10, "Gen crank attempts to HMI", "MOV(Gen_Crank_Attempts,HMI_Gen_Crank_Attempts);"),
    rung(11, "Sump state to HMI", "MOV(Sump_State,HMI_Sump_State);"),
    rung(12, "Sump pump running to HMI", "XIC(Sump_Pump_Run)OTE(HMI_Sump_Pump_Running);"),
    rung(13, "Sump float active to HMI", "XIC(Sump_Float_High)OTE(HMI_Sump_Float_Active);"),
    rung(14, "Sump test active to HMI", "XIC(Sump_Test_Active)OTE(HMI_Sump_Test_Active);"),
    rung(15, "Sump max run alarm to HMI", "XIC(Sump_Max_Run_Fault)OTE(HMI_Sump_Max_Run_Alarm);"),
    rung(16, "Sump cycle count to HMI", "MOV(Sump_Cycle_Count,HMI_Sump_Cycle_Count);"),
    rung(17, "Sump run hours to HMI", "DIV(Sump_Total_Run_Seconds,3600,HMI_Sump_Total_Run_Hours);"),
    rung(18, "Sump last run to HMI", "MOV(Sump_Last_Run_Seconds,HMI_Sump_Last_Run_Seconds);"),
    rung(19, "Sump last test OK to HMI", "XIC(Sump_Last_Test_OK)OTE(HMI_Sump_Last_Test_OK);"),
    rung(20, "Furnace running to HMI", "XIC(HVAC_Furnace_Running)OTE(HMI_HVAC_Furnace_Running);"),
    rung(21, "HVAC cycle count to HMI", "MOV(HVAC_Cycle_Count,HMI_HVAC_Cycle_Count);"),
    rung(22, "HVAC run hours to HMI", "DIV(HVAC_Total_Run_Seconds,3600,HMI_HVAC_Total_Run_Hours);"),
    rung(23, "HVAC last run to HMI", "MOV(HVAC_Last_Run_Seconds,HMI_HVAC_Last_Run_Seconds);"),
    rung(24, "Filter run hours to HMI", "DIV(HVAC_Filter_Run_Seconds,3600,HMI_HVAC_Filter_Run_Hours);"),
    rung(25, "Filter change due to HMI", "XIC(HVAC_Filter_Change_Due)OTE(HMI_HVAC_Filter_Change_Due);"),
    rung(26, "Short cycle alarm to HMI", "XIC(HVAC_Short_Cycle_Alarm)OTE(HMI_HVAC_Short_Cycle_Alarm);"),
    rung(27, "Outdoor temp to HMI", "MOV(Outdoor_Temp_F,HMI_Outdoor_Temp);"),
    rung(28, "Outdoor temp min to HMI", "MOV(HVAC_Outdoor_Temp_Min,HMI_Outdoor_Temp_Min);"),
    rung(29, "Outdoor temp max to HMI", "MOV(HVAC_Outdoor_Temp_Max,HMI_Outdoor_Temp_Max);"),
    rung(30, "Current amps to HMI", "MOV(Elec_Current_Amps,HMI_Elec_Current_Amps);"),
    rung(31, "Peak amps to HMI", "MOV(Elec_Peak_Amps,HMI_Elec_Peak_Amps);"),
    rung(32, "Total kWh to HMI", "MOV(Elec_Total_kWh,HMI_Elec_Total_kWh);"),
    rung(33, "Overload alarm to HMI", "XIC(Elec_Overload_Alarm)OTE(HMI_Elec_Overload_Alarm);"),
    rung(34, "Gen overload alarm to HMI", "XIC(Elec_Gen_Overload_Alarm)OTE(HMI_Elec_Gen_Overload_Alarm);"),
    # Feature 3: Freeze Protection to HMI
    rung(35, "Freeze warning to HMI", "XIC(Freeze_Warning)OTE(HMI_Freeze_Warning);"),
    rung(36, "Freeze critical to HMI", "XIC(Freeze_Critical)OTE(HMI_Freeze_Critical);"),
    # Feature 2: Sump cycle rate alarm to HMI
    rung(37, "Sump cycle rate alarm to HMI", "XIC(Sump_Cycle_Rate_Alarm)OTE(HMI_Sump_Cycle_Rate_Alarm);"),
    # Feature 9: Leak detection to HMI
    rung(38, "Leak alarm to HMI", "XIC(Leak_Any_Alarm)OTE(HMI_Leak_Any_Alarm);"),
    # Feature 10: Garage door to HMI
    rung(39, "Garage open alarm to HMI", "XIC(Garage_Open_Alarm)OTE(HMI_Garage_Open_Alarm);"),
    rung(40, "Garage open seconds to HMI", "MOV(Garage_Open_Seconds,HMI_Garage_Open_Seconds);"),
    # Feature 11: Well pump to HMI
    rung(41, "Well pump running to HMI", "XIC(Well_Pump_Running)OTE(HMI_Well_Pump_Running);"),
    rung(42, "Well pump short cycle alarm to HMI", "XIC(Well_Pump_Short_Cycle_Alarm)OTE(HMI_Well_Short_Cycle_Alarm);"),
    rung(43, "Water pressure low alarm to HMI", "XIC(Water_Pressure_Low_Alarm)OTE(HMI_Water_Pressure_Low_Alarm);"),
    rung(44, "Water pressure to HMI", "MOV(Water_Pressure_PSI,HMI_Water_Pressure_PSI);"),
    rung(45, "Well pump cycle count to HMI", "MOV(Well_Pump_Cycle_Count,HMI_Well_Pump_Cycle_Count);"),
    rung(46, "Well pump last run to HMI", "MOV(Well_Pump_Last_Run_Seconds,HMI_Well_Pump_Last_Run_Seconds);"),
    # Feature 4: Load shedding to HMI
    rung(47, "Load shed active to HMI", "XIC(Load_Shed_Active)OTE(HMI_Load_Shed_Active);"),
    # Feature 8: Maintenance to HMI
    rung(48, "Gen oil due to HMI", "XIC(Maint_Gen_Oil_Due)OTE(HMI_Maint_Gen_Oil_Due);"),
    rung(49, "Sump inspect due to HMI", "XIC(Maint_Sump_Inspect_Due)OTE(HMI_Maint_Sump_Inspect_Due);"),
    rung(50, "Furnace inspect due to HMI", "XIC(Maint_Furnace_Inspect_Due)OTE(HMI_Maint_Furnace_Inspect_Due);"),
    rung(51, "Gen hours since oil to HMI", "MOV(Maint_Gen_Hours_Since_Oil,HMI_Maint_Gen_Hours_Since_Oil);"),
    rung(52, "Sump cycles since inspect to HMI", "MOV(Maint_Sump_Cycles_Since_Inspect,HMI_Maint_Sump_Cycles_Since_Inspect);"),
    rung(53, "Furnace hours since inspect to HMI", "MOV(Maint_Furnace_Hours_Since_Inspect,HMI_Maint_Furnace_Hours_Since_Inspect);"),
    # Feature 7: HVAC efficiency to HMI
    rung(54, "HVAC efficiency pct to HMI", "MOV(HVAC_Efficiency_Pct,HMI_HVAC_Efficiency_Pct);"),
    rung(55, "HVAC efficiency alarm to HMI", "XIC(HVAC_Efficiency_Alarm)OTE(HMI_HVAC_Efficiency_Alarm);"),
    # Combined alarm banner - all alarms
    rung(56, "Any alarm active for HMI banner",
         "[XIC(Gen_Start_Fail),XIC(Gen_Stop_Fail),XIC(Gen_Fault),XIC(Sump_Max_Run_Fault),XIC(Sump_Cycle_Rate_Alarm),XIC(HVAC_Short_Cycle_Alarm),XIC(HVAC_Filter_Change_Due),XIC(HVAC_Efficiency_Alarm),XIC(Elec_Overload_Alarm),XIC(Elec_Gen_Overload_Alarm),XIC(Freeze_Warning),XIC(Freeze_Critical),XIC(Leak_Any_Alarm),XIC(Garage_Open_Alarm),XIC(Well_Pump_Short_Cycle_Alarm),XIC(Water_Pressure_Low_Alarm),XIC(Load_Shed_Active),XIC(Maint_Gen_Oil_Due),XIC(Maint_Sump_Inspect_Due),XIC(Maint_Furnace_Inspect_Due)]OTE(HMI_Any_Alarm);"),
]

# --- Output_Mapping ---
output_rungs = [
    rung(0, "Gen start command to Pt00", "XIC(Gen_Start_Cmd)OTE(Local:2:O.Pt00.Data);"),
    rung(1, "ATS transfer command to Pt01", "XIC(ATS_Transfer_Cmd)OTE(Local:2:O.Pt01.Data);"),
    rung(2, "Sump pump run to Pt02", "XIC(Sump_Pump_Run)OTE(Local:2:O.Pt02.Data);"),
    # Feature 4: Load Shedding outputs
    rung(3, "Load shed HVAC to Pt03", "XIC(Load_Shed_HVAC)OTE(Local:2:O.Pt03.Data);"),
    rung(4, "Load shed non-critical 1 to Pt04", "XIC(Load_Shed_NonCritical1)OTE(Local:2:O.Pt04.Data);"),
    rung(5, "Load shed non-critical 2 to Pt05", "XIC(Load_Shed_NonCritical2)OTE(Local:2:O.Pt05.Data);"),
]

# --- Leak_Detection (Feature 9) ---
leak_rungs = [
    rung(0, "Any leak zone active - latch alarm", "[XIC(Leak_Zone1),XIC(Leak_Zone2),XIC(Leak_Zone3)]OTL(Leak_Any_Alarm);"),
    rung(1, "Reset leak alarm only when all zones clear", "XIC(HMI_Leak_Alarm_Reset)XIO(Leak_Zone1)XIO(Leak_Zone2)XIO(Leak_Zone3)OTU(Leak_Any_Alarm);"),
    rung(2, "Clear HMI leak alarm reset", "XIC(HMI_Leak_Alarm_Reset)OTU(HMI_Leak_Alarm_Reset);"),
]

# --- Garage_Monitor (Feature 10) ---
garage_rungs = [
    rung(0, "Garage door open when not closed", "XIO(Garage_Door_Closed)OTE(Garage_Door_Open);"),
    rung(1, "Track garage open duration", "XIC(Garage_Door_Open)XIC(Pulse_1s)ADD(Garage_Open_Seconds,1,Garage_Open_Seconds);"),
    rung(2, "Reset open counter when door closed", "XIO(Garage_Door_Open)MOV(0,Garage_Open_Seconds);"),
    rung(3, "Alarm when open too long", "GEQ(Garage_Open_Seconds,Garage_Open_Max_Seconds)OTL(Garage_Open_Alarm);"),
    rung(4, "Reset garage alarm when door closed and HMI reset", "XIC(HMI_Garage_Alarm_Reset)XIC(Garage_Door_Closed)OTU(Garage_Open_Alarm);"),
    rung(5, "Clear HMI garage alarm reset", "XIC(HMI_Garage_Alarm_Reset)OTU(HMI_Garage_Alarm_Reset);"),
]

# --- Well_Pump_Monitor (Feature 11) ---
well_rungs = [
    # Short cycle detection timer
    rung(0, "Well pump short cycle detection window 60s", "XIO(Well_Pump_Running)TON(Well_Short_Cycle_Timer,60000,0);"),
    # Cycle counting with one-shot
    rung(1, "Count well pump cycle on start", "XIC(Well_Pump_Running)XIO(Well_Pump_Cycle_ONS)ADD(Well_Pump_Cycle_Count,1,Well_Pump_Cycle_Count);"),
    rung(2, "Set well pump cycle one-shot", "XIC(Well_Pump_Running)OTL(Well_Pump_Cycle_ONS);"),
    rung(3, "Clear well pump cycle one-shot", "XIO(Well_Pump_Running)OTU(Well_Pump_Cycle_ONS);"),
    # Track current run time
    rung(4, "Track well pump current run seconds", "XIC(Well_Pump_Running)XIC(Pulse_1s)ADD(Well_Pump_Current_Run_Seconds,1,Well_Pump_Current_Run_Seconds);"),
    # Detect shutdown - save last run, check short cycle
    rung(5, "Save last run on pump stop", "XIO(Well_Pump_Running)XIC(Well_Pump_Cycle_ONS)MOV(Well_Pump_Current_Run_Seconds,Well_Pump_Last_Run_Seconds);"),
    rung(6, "Short cycle detect - run less than minimum", "XIO(Well_Pump_Running)XIC(Well_Pump_Cycle_ONS)LES(Well_Pump_Current_Run_Seconds,Well_Pump_Min_Run_Seconds)ADD(Well_Pump_Short_Cycle_Count,1,Well_Pump_Short_Cycle_Count);"),
    rung(7, "Clear short cycle count on normal run", "XIO(Well_Pump_Running)XIC(Well_Pump_Cycle_ONS)GEQ(Well_Pump_Current_Run_Seconds,Well_Pump_Min_Run_Seconds)MOV(0,Well_Pump_Short_Cycle_Count);"),
    rung(8, "Clear current run seconds on pump stop", "XIO(Well_Pump_Running)MOV(0,Well_Pump_Current_Run_Seconds);"),
    # Short cycle alarm at 3
    rung(9, "Short cycle alarm at 3 consecutive", "GEQ(Well_Pump_Short_Cycle_Count,3)OTL(Well_Pump_Short_Cycle_Alarm);"),
    # Low pressure alarm
    rung(10, "Low water pressure alarm", "LES(Water_Pressure_PSI,Water_Pressure_Low_SP)OTL(Water_Pressure_Low_Alarm);"),
    rung(11, "Clear low pressure when above setpoint", "GEQ(Water_Pressure_PSI,Water_Pressure_Low_SP)OTU(Water_Pressure_Low_Alarm);"),
    # HMI reset
    rung(12, "HMI well alarm reset - clear short cycle alarm", "XIC(HMI_Well_Alarm_Reset)OTU(Well_Pump_Short_Cycle_Alarm);"),
    rung(13, "HMI well alarm reset - clear short cycle count", "XIC(HMI_Well_Alarm_Reset)MOV(0,Well_Pump_Short_Cycle_Count);"),
    rung(14, "Clear HMI well alarm reset", "XIC(HMI_Well_Alarm_Reset)OTU(HMI_Well_Alarm_Reset);"),
]

# --- Maintenance_Monitor (Feature 8) ---
maint_rungs = [
    # Generator oil change tracking
    rung(0, "Track gen run seconds since oil change", "XIC(Gen_Running)XIC(Pulse_1s)ADD(Maint_Gen_Run_Since_Oil,1,Maint_Gen_Run_Since_Oil);"),
    rung(1, "Convert gen run seconds to hours", "DIV(Maint_Gen_Run_Since_Oil,3600,Maint_Gen_Hours_Since_Oil);"),
    rung(2, "Gen oil change due", "GEQ(Maint_Gen_Hours_Since_Oil,Maint_Gen_Oil_Hours)OTL(Maint_Gen_Oil_Due);"),
    rung(3, "HMI gen oil reset", "XIC(HMI_Maint_Gen_Oil_Reset)MOV(0,Maint_Gen_Run_Since_Oil);"),
    rung(4, None, "XIC(HMI_Maint_Gen_Oil_Reset)OTU(Maint_Gen_Oil_Due);"),
    rung(5, None, "XIC(HMI_Maint_Gen_Oil_Reset)OTU(HMI_Maint_Gen_Oil_Reset);"),
    # Sump pump inspection tracking - count pump starts with one-shot
    rung(6, "Track sump cycles since inspection", "XIC(Sump_Pump_Run)XIO(Maint_Sump_Cycle_ONS)ADD(Maint_Sump_Cycles_Since_Inspect,1,Maint_Sump_Cycles_Since_Inspect);"),
    rung(7, "Set maint sump cycle one-shot", "XIC(Sump_Pump_Run)OTL(Maint_Sump_Cycle_ONS);"),
    rung(8, "Clear maint sump cycle one-shot", "XIO(Sump_Pump_Run)OTU(Maint_Sump_Cycle_ONS);"),
    rung(9, "Sump inspection due", "GEQ(Maint_Sump_Cycles_Since_Inspect,Maint_Sump_Inspect_Cycles)OTL(Maint_Sump_Inspect_Due);"),
    rung(10, "HMI sump inspect reset - clear cycle counter", "XIC(HMI_Maint_Sump_Reset)MOV(0,Maint_Sump_Cycles_Since_Inspect);"),
    rung(11, None, "XIC(HMI_Maint_Sump_Reset)OTU(Maint_Sump_Inspect_Due);"),
    rung(12, None, "XIC(HMI_Maint_Sump_Reset)OTU(HMI_Maint_Sump_Reset);"),
    # Furnace inspection tracking
    rung(13, "Track furnace run seconds since inspection", "XIC(HVAC_Furnace_Running)XIC(Pulse_1s)ADD(Maint_Furnace_Run_Since_Inspect,1,Maint_Furnace_Run_Since_Inspect);"),
    rung(14, "Convert furnace run seconds to hours", "DIV(Maint_Furnace_Run_Since_Inspect,3600,Maint_Furnace_Hours_Since_Inspect);"),
    rung(15, "Furnace inspection due", "GEQ(Maint_Furnace_Hours_Since_Inspect,Maint_Furnace_Inspect_Hours)OTL(Maint_Furnace_Inspect_Due);"),
    rung(16, "HMI furnace inspect reset", "XIC(HMI_Maint_Furnace_Reset)MOV(0,Maint_Furnace_Run_Since_Inspect);"),
    rung(17, None, "XIC(HMI_Maint_Furnace_Reset)OTU(Maint_Furnace_Inspect_Due);"),
    rung(18, None, "XIC(HMI_Maint_Furnace_Reset)OTU(HMI_Maint_Furnace_Reset);"),
]

def build_routine(name, rung_list):
    rungs_xml = "\n".join(rung_list)
    return f'''<Routine Name="{name}" Type="RLL">
<RLLContent>
{rungs_xml}
</RLLContent>
</Routine>'''

programs_section = '''<Programs>
<Program Name="MainProgram" TestEdits="false" MainRoutineName="MainRoutine" Disabled="false" UseAsFolder="false">
<Tags/>
<Routines>
''' + build_routine("MainRoutine", main_rungs) + "\n" \
   + build_routine("Input_Mapping", input_rungs) + "\n" \
   + build_routine("Generator_Control", gen_rungs) + "\n" \
   + build_routine("Sump_Pump_Control", sump_rungs) + "\n" \
   + build_routine("HVAC_Monitor", hvac_rungs) + "\n" \
   + build_routine("Electrical_Monitor", elec_rungs) + "\n" \
   + build_routine("Leak_Detection", leak_rungs) + "\n" \
   + build_routine("Garage_Monitor", garage_rungs) + "\n" \
   + build_routine("Well_Pump_Monitor", well_rungs) + "\n" \
   + build_routine("Maintenance_Monitor", maint_rungs) + "\n" \
   + build_routine("HMI_Interface", hmi_rungs) + "\n" \
   + build_routine("Output_Mapping", output_rungs) + '''
</Routines>
</Program>
</Programs>
'''

footer = '''<Tasks>
<Task Name="MainTask" Type="CONTINUOUS" Priority="10" Watchdog="500" DisableUpdateOutputs="false" InhibitTask="false">
<ScheduledPrograms>
<ScheduledProgram Name="MainProgram"/>
</ScheduledPrograms>
</Task>
</Tasks>
<CST MasterID="0"/>
<WallClockTime LocalTimeAdjustment="0" TimeZone="0"/>
<Trends/>
<DataLogs/>
<TimeSynchronize Priority1="128" Priority2="128" PTPEnable="false"/>
<EthernetPorts>
<EthernetPort Port="1" Label="A1" PortEnabled="true"/>
<EthernetPort Port="2" Label="A2" PortEnabled="true"/>
</EthernetPorts>
</Controller>
</RSLogix5000Content>
'''

# Assemble the complete file
with open(r"C:\Users\tremmen\Desktop\HomePLC.L5X", "w", encoding="utf-8") as f:
    f.write(header)
    f.write(tags_section)
    f.write(programs_section)
    f.write(footer)

print("HomePLC.L5X written successfully!")
print(f"Tags: {len(tags)}")
print(f"Routines: 12 (MainRoutine + 11 subroutines)")
print(f"Main rungs: {len(main_rungs)}")
print(f"Input mapping rungs: {len(input_rungs)}")
print(f"Generator control rungs: {len(gen_rungs)}")
print(f"Sump pump control rungs: {len(sump_rungs)}")
print(f"HVAC monitor rungs: {len(hvac_rungs)}")
print(f"Electrical monitor rungs: {len(elec_rungs)}")
print(f"Leak detection rungs: {len(leak_rungs)}")
print(f"Garage monitor rungs: {len(garage_rungs)}")
print(f"Well pump monitor rungs: {len(well_rungs)}")
print(f"Maintenance monitor rungs: {len(maint_rungs)}")
print(f"HMI interface rungs: {len(hmi_rungs)}")
print(f"Output mapping rungs: {len(output_rungs)}")
