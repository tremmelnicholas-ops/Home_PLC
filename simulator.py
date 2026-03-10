"""PLC Simulator Engine - replicates all HomePLC ladder logic in Python."""

import time
import threading
import random


class SimTimer:
    """Simulates a Studio 5000 TON timer."""
    def __init__(self, preset_ms):
        self.PRE = preset_ms
        self.ACC = 0
        self.EN = False
        self.TT = False
        self.DN = False

    def update(self, enable, dt_ms):
        if enable:
            self.EN = True
            if not self.DN:
                self.ACC += dt_ms
                self.TT = True
                if self.ACC >= self.PRE:
                    self.ACC = self.PRE
                    self.DN = True
                    self.TT = False
        else:
            self.EN = False
            self.TT = False
            self.DN = False
            self.ACC = 0


class PLCSimulator:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.scan_time_ms = 100  # 100ms scan time (10x real for faster demo)

        # === SIMULATED PHYSICAL INPUTS (user toggles these) ===
        self.sim_utility_power = True
        self.sim_gen_running = False  # auto-controlled by sim
        self.sim_gen_fault = False
        self.sim_gen_ready = True
        self.sim_ats_utility = True
        self.sim_ats_generator = False
        self.sim_float_high = False
        self.sim_thermostat_call = False
        self.sim_outdoor_temp_pct = 62.5   # 0-100% (62.5% = ~50F)
        self.sim_house_current_pct = 35.0  # 0-100% (35% = ~37.5A)

        # === ALL PLC TAGS ===
        # Inputs (mapped from sim)
        self.Utility_Power_Present = True
        self.Gen_Running = False
        self.Gen_Fault = False
        self.Gen_Ready = True
        self.ATS_Utility_Pos = True
        self.ATS_Generator_Pos = False
        self.Sump_Float_High = False
        self.Thermostat_W_Call = False
        self.Outdoor_Temp_F = 50.0
        self.House_Current_Amps = 37.5

        # Generator
        self.Gen_State = 0
        self.Gen_Start_Cmd = False
        self.ATS_Transfer_Cmd = False
        self.Gen_On_Utility = True
        self.Gen_On_Generator = False
        self.Gen_Start_Fail = False
        self.Gen_Stop_Fail = False
        self.Gen_Exercise_Active = False
        self.Gen_Crank_Attempts = 0
        self.Gen_Total_Run_Seconds = 0
        self.Exercise_Trigger = False
        self.Exercise_Seconds = 0
        self.HMI_Exercise_Request = False
        self.HMI_Gen_Fault_Reset = False

        # Sump
        self.Sump_State = 0
        self.Sump_Pump_Run = False
        self.Sump_Max_Run_Fault = False
        self.Sump_Test_Active = False
        self.Sump_Last_Test_OK = False
        self.Sump_Test_Trigger = False
        self.Sump_Cycle_Count = 0
        self.Sump_Total_Run_Seconds = 0
        self.Sump_Current_Run_Seconds = 0
        self.Sump_Last_Run_Seconds = 0
        self.Sump_Test_Seconds = 0
        self.HMI_Sump_Test_Request = False
        self.HMI_Sump_Fault_Reset = False

        # HVAC
        self.HVAC_Furnace_Running = False
        self.HVAC_Was_Running = False
        self.HVAC_Cycle_Count = 0
        self.HVAC_Current_Run_Seconds = 0
        self.HVAC_Last_Run_Seconds = 0
        self.HVAC_Total_Run_Seconds = 0
        self.HVAC_Filter_Run_Seconds = 0
        self.HVAC_Filter_Change_Due = False
        self.HVAC_Short_Cycle_Count = 0
        self.HVAC_Short_Cycle_Alarm = False
        self.HVAC_Outdoor_Temp_Min = 120.0
        self.HVAC_Outdoor_Temp_Max = -40.0
        self.HMI_Filter_Reset = False
        self.HMI_Temp_MinMax_Reset = False
        self.HMI_HVAC_Alarm_Reset = False

        # Electrical
        self.Elec_Current_Amps = 0.0
        self.Elec_Peak_Amps = 0.0
        self.Elec_Gen_Max_Amps = 80.0
        self.Elec_Overload_Alarm = False
        self.Elec_Gen_Overload_Alarm = False
        self.Elec_Watt_Seconds = 0.0
        self.Elec_Total_kWh = 0.0
        self.HMI_Elec_Peak_Reset = False
        self.HMI_Elec_Alarm_Reset = False

        # === TIMERS ===
        self.Power_Loss_Delay = SimTimer(5000)
        self.Gen_Start_Timeout = SimTimer(30000)
        self.Gen_Warmup_Timer = SimTimer(30000)
        self.Gen_Cooldown_Timer = SimTimer(120000)
        self.Gen_Stop_Timeout = SimTimer(30000)
        self.Exercise_Run_Timer = SimTimer(900000)
        self.Transfer_Delay = SimTimer(3000)
        self.Gen_Utility_Return_Timer = SimTimer(5000)
        self.Sump_Debounce = SimTimer(2000)
        self.Sump_Max_Run = SimTimer(300000)
        self.Sump_Off_Delay = SimTimer(10000)
        self.Sump_Test_Run_Timer = SimTimer(15000)
        self.Heat_Call_Debounce = SimTimer(5000)
        self.Short_Cycle_Timer = SimTimer(180000)
        self.Elec_Overload_Timer = SimTimer(5000)
        self.Elec_Gen_Overload_Timer = SimTimer(3000)

        # 1-second pulse
        self.Pulse_1s_Timer = SimTimer(1000)
        self.Pulse_1s = False

        # Internal
        self._1s_acc = 0
        self._gen_start_cmd_delay = 0  # simulate gen startup delay
        self._ats_transfer_delay = 0

        # Use faster timers for demo
        self.speed_multiplier = 10  # 10x speed

    def set_sim_input(self, name, value):
        with self.lock:
            setattr(self, f"sim_{name}", value)

    def get_all_tags(self):
        with self.lock:
            return {
                # Generator
                "Gen_State": self.Gen_State,
                "Gen_Running": self.Gen_Running,
                "Gen_Fault": self.Gen_Fault,
                "Gen_Ready": self.Gen_Ready,
                "Gen_On_Utility": self.Gen_On_Utility,
                "Gen_On_Generator": self.Gen_On_Generator,
                "Gen_Start_Cmd": self.Gen_Start_Cmd,
                "ATS_Transfer_Cmd": self.ATS_Transfer_Cmd,
                "Gen_Exercise_Active": self.Gen_Exercise_Active,
                "Gen_Start_Fail": self.Gen_Start_Fail,
                "Gen_Stop_Fail": self.Gen_Stop_Fail,
                "Gen_Crank_Attempts": self.Gen_Crank_Attempts,
                "Gen_Total_Run_Seconds": self.Gen_Total_Run_Seconds,
                "Utility_Power_Present": self.Utility_Power_Present,
                "ATS_Utility_Pos": self.ATS_Utility_Pos,
                "ATS_Generator_Pos": self.ATS_Generator_Pos,
                "Exercise_Trigger": self.Exercise_Trigger,
                # Sump
                "Sump_State": self.Sump_State,
                "Sump_Pump_Run": self.Sump_Pump_Run,
                "Sump_Float_High": self.Sump_Float_High,
                "Sump_Test_Active": self.Sump_Test_Active,
                "Sump_Last_Test_OK": self.Sump_Last_Test_OK,
                "Sump_Max_Run_Fault": self.Sump_Max_Run_Fault,
                "Sump_Cycle_Count": self.Sump_Cycle_Count,
                "Sump_Total_Run_Seconds": self.Sump_Total_Run_Seconds,
                "Sump_Last_Run_Seconds": self.Sump_Last_Run_Seconds,
                "Sump_Current_Run_Seconds": self.Sump_Current_Run_Seconds,
                # HVAC
                "HVAC_Furnace_Running": self.HVAC_Furnace_Running,
                "HVAC_Cycle_Count": self.HVAC_Cycle_Count,
                "HVAC_Total_Run_Seconds": self.HVAC_Total_Run_Seconds,
                "HVAC_Last_Run_Seconds": self.HVAC_Last_Run_Seconds,
                "HVAC_Current_Run_Seconds": self.HVAC_Current_Run_Seconds,
                "HVAC_Filter_Run_Seconds": self.HVAC_Filter_Run_Seconds,
                "HVAC_Filter_Change_Due": self.HVAC_Filter_Change_Due,
                "HVAC_Short_Cycle_Alarm": self.HVAC_Short_Cycle_Alarm,
                "HVAC_Short_Cycle_Count": self.HVAC_Short_Cycle_Count,
                "Thermostat_W_Call": self.Thermostat_W_Call,
                # Electrical / Temp
                "Outdoor_Temp_F": round(self.Outdoor_Temp_F, 1),
                "House_Current_Amps": round(self.House_Current_Amps, 1),
                "Elec_Current_Amps": round(self.Elec_Current_Amps, 1),
                "Elec_Peak_Amps": round(self.Elec_Peak_Amps, 1),
                "Elec_Total_kWh": round(self.Elec_Total_kWh, 1),
                "Elec_Overload_Alarm": self.Elec_Overload_Alarm,
                "Elec_Gen_Overload_Alarm": self.Elec_Gen_Overload_Alarm,
                "Elec_Gen_Max_Amps": self.Elec_Gen_Max_Amps,
                "HVAC_Outdoor_Temp_Min": round(self.HVAC_Outdoor_Temp_Min, 1),
                "HVAC_Outdoor_Temp_Max": round(self.HVAC_Outdoor_Temp_Max, 1),
            }

    def get_sim_inputs(self):
        with self.lock:
            return {
                "utility_power": self.sim_utility_power,
                "gen_fault": self.sim_gen_fault,
                "gen_ready": self.sim_gen_ready,
                "float_high": self.sim_float_high,
                "thermostat_call": self.sim_thermostat_call,
                "outdoor_temp_pct": self.sim_outdoor_temp_pct,
                "house_current_pct": self.sim_house_current_pct,
                "speed_multiplier": self.speed_multiplier,
            }

    def write_tag(self, tag, value):
        with self.lock:
            if hasattr(self, tag):
                setattr(self, tag, value)
                return True
        return False

    def _scan(self, dt_ms):
        """Execute one PLC scan cycle."""
        # === INPUT MAPPING ===
        self.Utility_Power_Present = self.sim_utility_power
        self.Gen_Fault = self.sim_gen_fault
        self.Gen_Ready = self.sim_gen_ready
        self.Sump_Float_High = self.sim_float_high
        self.Thermostat_W_Call = self.sim_thermostat_call

        # Simulate generator auto-response to start command
        if self.Gen_Start_Cmd and not self.Gen_Running and not self.Gen_Fault:
            self._gen_start_cmd_delay += dt_ms
            if self._gen_start_cmd_delay >= 3000:  # 3 sec startup delay
                self.Gen_Running = True
                self.sim_gen_running = True
        elif not self.Gen_Start_Cmd:
            if self.Gen_Running:
                self.Gen_Running = False
                self.sim_gen_running = False
            self._gen_start_cmd_delay = 0

        if self.Gen_Fault:
            self.Gen_Running = False
            self.sim_gen_running = False

        # Simulate ATS auto-response to transfer command
        if self.ATS_Transfer_Cmd:
            self._ats_transfer_delay += dt_ms
            if self._ats_transfer_delay >= 1500:
                self.ATS_Generator_Pos = True
                self.ATS_Utility_Pos = False
                self.sim_ats_generator = True
                self.sim_ats_utility = False
        else:
            self._ats_transfer_delay = 0
            if not self.ATS_Utility_Pos:
                # Return to utility
                self.ATS_Utility_Pos = True
                self.ATS_Generator_Pos = False
                self.sim_ats_utility = True
                self.sim_ats_generator = False

        # Analog scaling (4-20mA on 0-20mA range)
        self.Outdoor_Temp_F = (self.sim_outdoor_temp_pct - 20.0) * 2.0 - 40.0
        self.Outdoor_Temp_F = max(-40.0, min(120.0, self.Outdoor_Temp_F))
        self.House_Current_Amps = (self.sim_house_current_pct - 20.0) * 2.5
        self.House_Current_Amps = max(0.0, min(200.0, self.House_Current_Amps))

        # Add slight noise to analog
        self.Outdoor_Temp_F += random.uniform(-0.3, 0.3)
        self.House_Current_Amps += random.uniform(-0.5, 0.5)
        self.House_Current_Amps = max(0.0, self.House_Current_Amps)

        # === 1-SECOND PULSE ===
        self._1s_acc += dt_ms
        if self._1s_acc >= 1000:
            self._1s_acc -= 1000
            self.Pulse_1s = True
        else:
            self.Pulse_1s = False

        # === GENERATOR CONTROL ===
        self._gen_timers(dt_ms)
        self._gen_logic()

        # === SUMP PUMP CONTROL ===
        self._sump_timers(dt_ms)
        self._sump_logic()

        # === HVAC MONITOR ===
        self._hvac_timers(dt_ms)
        self._hvac_logic()

        # === ELECTRICAL MONITOR ===
        self._elec_logic()

    def _gen_timers(self, dt_ms):
        self.Power_Loss_Delay.update(not self.Utility_Power_Present, dt_ms)
        self.Gen_Start_Timeout.update(self.Gen_State in (20, 95), dt_ms)
        self.Gen_Warmup_Timer.update(self.Gen_State == 30, dt_ms)
        self.Gen_Cooldown_Timer.update(self.Gen_State in (60, 105), dt_ms)
        self.Gen_Stop_Timeout.update(self.Gen_State in (70, 110), dt_ms)
        self.Exercise_Run_Timer.update(self.Gen_State == 100, dt_ms)
        self.Transfer_Delay.update(self.Gen_State == 40, dt_ms)
        self.Gen_Utility_Return_Timer.update(
            self.Gen_State == 50 and self.Utility_Power_Present, dt_ms)

    def _gen_logic(self):
        # Exercise schedule
        if self.Pulse_1s:
            self.Exercise_Seconds += 1
        if self.Exercise_Seconds >= 604800:
            self.Exercise_Trigger = True
        if self.Exercise_Trigger:
            self.Exercise_Seconds = 0

        # HMI exercise request
        if self.HMI_Exercise_Request:
            self.Exercise_Trigger = True
            self.HMI_Exercise_Request = False

        # Output flags based on state
        self.Gen_Start_Cmd = self.Gen_State in (10,20,30,40,50,55,60,90,95,100,105)
        self.ATS_Transfer_Cmd = self.Gen_State in (40, 50)
        self.Gen_On_Utility = self.Gen_State in (0,55,60,70,90,95,100,105,110,999)
        self.Gen_On_Generator = self.Gen_State == 50
        self.Gen_Exercise_Active = self.Gen_State in (90, 95, 100, 105)

        # State transitions (order matters)
        gs = self.Gen_State

        if gs == 0:
            if self.Power_Loss_Delay.DN:
                self.Gen_State = 10
            elif self.Exercise_Trigger and not self.Gen_Fault:
                self.Gen_State = 90

        elif gs == 90:
            self.Exercise_Trigger = False
            self.Gen_State = 95

        elif gs == 10:
            self.Gen_State = 20

        elif gs == 20:
            if self.Gen_Running:
                self.Gen_State = 30
            elif self.Gen_Start_Timeout.DN:
                self.Gen_Crank_Attempts += 1
                if self.Gen_Crank_Attempts >= 3:
                    self.Gen_Start_Fail = True
                    self.Gen_State = 999
                else:
                    self.Gen_State = 10

        elif gs == 30:
            if self.Gen_Warmup_Timer.DN:
                self.Gen_State = 40
            if self.Gen_Fault:
                self.Gen_State = 999

        elif gs == 40:
            if self.Transfer_Delay.DN and self.ATS_Generator_Pos:
                self.Gen_State = 50
            if self.Gen_Fault:
                self.Gen_State = 999

        elif gs == 50:
            if self.Pulse_1s:
                self.Gen_Total_Run_Seconds += 1
            if self.Gen_Utility_Return_Timer.DN:
                self.Gen_State = 55
            if self.Gen_Fault:
                self.Gen_State = 999

        elif gs == 55:
            if self.ATS_Utility_Pos:
                self.Gen_State = 60

        elif gs == 60:
            if self.Gen_Cooldown_Timer.DN:
                self.Gen_State = 70

        elif gs == 70:
            if not self.Gen_Running:
                self.Gen_Crank_Attempts = 0
                self.Gen_State = 0
            elif self.Gen_Stop_Timeout.DN:
                self.Gen_Stop_Fail = True
                self.Gen_State = 999

        elif gs == 95:
            if self.Gen_Running:
                self.Gen_State = 100
            elif self.Gen_Start_Timeout.DN:
                self.Gen_Start_Fail = True
                self.Gen_State = 999

        elif gs == 100:
            if self.Pulse_1s:
                self.Gen_Total_Run_Seconds += 1
            if self.Exercise_Run_Timer.DN:
                self.Gen_State = 105
            if not self.Utility_Power_Present:
                self.Gen_State = 30
            if self.Gen_Fault:
                self.Gen_State = 999

        elif gs == 105:
            if self.Gen_Cooldown_Timer.DN:
                self.Gen_State = 110

        elif gs == 110:
            if not self.Gen_Running:
                self.Gen_Crank_Attempts = 0
                self.Gen_State = 0
            elif self.Gen_Stop_Timeout.DN:
                self.Gen_Stop_Fail = True
                self.Gen_State = 999

        # Fault reset
        if self.HMI_Gen_Fault_Reset and not self.Gen_Fault:
            self.Gen_Start_Fail = False
            self.Gen_Stop_Fail = False
            self.Gen_Crank_Attempts = 0
            self.Gen_State = 0
            self.HMI_Gen_Fault_Reset = False

    def _sump_timers(self, dt_ms):
        self.Sump_Debounce.update(self.Sump_Float_High, dt_ms)
        self.Sump_Max_Run.update(self.Sump_Pump_Run, dt_ms)
        self.Sump_Off_Delay.update(
            not self.Sump_Float_High and self.Sump_Pump_Run, dt_ms)
        self.Sump_Test_Run_Timer.update(self.Sump_State == 30, dt_ms)

    def _sump_logic(self):
        # Weekly test
        if self.Pulse_1s:
            self.Sump_Test_Seconds += 1
        if self.Sump_Test_Seconds >= 604800:
            self.Sump_Test_Trigger = True
        if self.Sump_Test_Trigger:
            self.Sump_Test_Seconds = 0

        if self.HMI_Sump_Test_Request:
            self.Sump_Test_Trigger = True
            self.HMI_Sump_Test_Request = False

        ss = self.Sump_State

        if ss == 0:
            if self.Sump_Debounce.DN:
                self.Sump_State = 10
            elif self.Sump_Test_Trigger:
                self.Sump_Test_Trigger = False
                self.Sump_State = 30

        elif ss == 10:
            self.Sump_Cycle_Count += 1
            self.Sump_State = 20

        elif ss == 20:
            if self.Pulse_1s:
                self.Sump_Current_Run_Seconds += 1
                self.Sump_Total_Run_Seconds += 1
            if self.Sump_Max_Run.DN:
                self.Sump_Max_Run_Fault = True
                self.Sump_Last_Run_Seconds = self.Sump_Current_Run_Seconds
                self.Sump_Current_Run_Seconds = 0
                self.Sump_State = 999
            elif self.Sump_Off_Delay.DN:
                self.Sump_Last_Run_Seconds = self.Sump_Current_Run_Seconds
                self.Sump_Current_Run_Seconds = 0
                self.Sump_State = 0

        elif ss == 30:
            self.Sump_Test_Active = True
            if self.Sump_Test_Run_Timer.DN:
                self.Sump_Test_Active = False
                self.Sump_Last_Test_OK = True
                self.Sump_State = 0
            elif self.Sump_Float_High:
                self.Sump_Test_Active = False
                self.Sump_State = 20

        elif ss == 999:
            pass

        # Pump output
        self.Sump_Pump_Run = self.Sump_State in (10, 20, 30) or \
            (self.Sump_State == 999 and self.Sump_Float_High)

        # Fault reset
        if self.HMI_Sump_Fault_Reset:
            self.Sump_Max_Run_Fault = False
            self.Sump_State = 0
            self.HMI_Sump_Fault_Reset = False

    def _hvac_timers(self, dt_ms):
        self.Heat_Call_Debounce.update(self.Thermostat_W_Call, dt_ms)
        self.Short_Cycle_Timer.update(
            not self.Thermostat_W_Call and self.HVAC_Was_Running, dt_ms)

    def _hvac_logic(self):
        # Furnace start detection
        if self.Heat_Call_Debounce.DN and not self.HVAC_Furnace_Running:
            self.HVAC_Cycle_Count += 1
            self.HVAC_Current_Run_Seconds = 0
            if self.Short_Cycle_Timer.TT:
                self.HVAC_Short_Cycle_Count += 1
                if self.HVAC_Short_Cycle_Count >= 3:
                    self.HVAC_Short_Cycle_Alarm = True
            else:
                self.HVAC_Short_Cycle_Count = 0
            self.HVAC_Furnace_Running = True

        # Furnace shutdown
        if not self.Thermostat_W_Call and self.HVAC_Furnace_Running:
            self.HVAC_Last_Run_Seconds = self.HVAC_Current_Run_Seconds
            self.HVAC_Was_Running = True
            self.HVAC_Furnace_Running = False

        if self.Short_Cycle_Timer.DN:
            self.HVAC_Was_Running = False

        # Run time tracking
        if self.HVAC_Furnace_Running and self.Pulse_1s:
            self.HVAC_Current_Run_Seconds += 1
            self.HVAC_Total_Run_Seconds += 1
            self.HVAC_Filter_Run_Seconds += 1

        if self.HVAC_Filter_Run_Seconds >= 1080000:
            self.HVAC_Filter_Change_Due = True

        # Temp tracking
        if self.Outdoor_Temp_F < self.HVAC_Outdoor_Temp_Min:
            self.HVAC_Outdoor_Temp_Min = self.Outdoor_Temp_F
        if self.Outdoor_Temp_F > self.HVAC_Outdoor_Temp_Max:
            self.HVAC_Outdoor_Temp_Max = self.Outdoor_Temp_F

        # HMI resets
        if self.HMI_Filter_Reset:
            self.HVAC_Filter_Run_Seconds = 0
            self.HVAC_Filter_Change_Due = False
            self.HMI_Filter_Reset = False

        if self.HMI_Temp_MinMax_Reset:
            self.HVAC_Outdoor_Temp_Min = self.Outdoor_Temp_F
            self.HVAC_Outdoor_Temp_Max = self.Outdoor_Temp_F
            self.HMI_Temp_MinMax_Reset = False

        if self.HMI_HVAC_Alarm_Reset:
            self.HVAC_Short_Cycle_Alarm = False
            self.HVAC_Short_Cycle_Count = 0
            self.HMI_HVAC_Alarm_Reset = False

    def _elec_logic(self):
        self.Elec_Current_Amps = self.House_Current_Amps

        if self.Elec_Current_Amps > self.Elec_Peak_Amps:
            self.Elec_Peak_Amps = self.Elec_Current_Amps

        # Overload (uses timer now instead of scan counter)
        self.Elec_Overload_Timer.update(
            self.Elec_Current_Amps > 180.0, self.scan_time_ms)
        if self.Elec_Overload_Timer.DN:
            self.Elec_Overload_Alarm = True

        self.Elec_Gen_Overload_Timer.update(
            self.Gen_On_Generator and self.Elec_Current_Amps > self.Elec_Gen_Max_Amps,
            self.scan_time_ms)
        if self.Elec_Gen_Overload_Timer.DN:
            self.Elec_Gen_Overload_Alarm = True

        # kWh tracking
        if self.Pulse_1s:
            self.Elec_Watt_Seconds += self.Elec_Current_Amps * 240.0
            if self.Elec_Watt_Seconds >= 3600000.0:
                self.Elec_Total_kWh += 1.0
                self.Elec_Watt_Seconds -= 3600000.0

        if self.HMI_Elec_Peak_Reset:
            self.Elec_Peak_Amps = 0.0
            self.HMI_Elec_Peak_Reset = False

        if self.HMI_Elec_Alarm_Reset:
            self.Elec_Overload_Alarm = False
            self.Elec_Gen_Overload_Alarm = False
            self.HMI_Elec_Alarm_Reset = False

    def run(self):
        """Main scan loop."""
        self.running = True
        last = time.time()
        while self.running:
            now = time.time()
            elapsed_ms = (now - last) * 1000.0 * self.speed_multiplier
            last = now
            with self.lock:
                self._scan(elapsed_ms)
            time.sleep(self.scan_time_ms / 1000.0)

    def start(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
