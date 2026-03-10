"""HomePLC Alert Manager - sends email alerts for alarm conditions."""

import smtplib
import json
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta


class AlertManager:
    CONFIG_FILE = "data/alert_config.json"

    ALARM_MESSAGES = {
        "Gen_Start_Fail": "Generator failed to start",
        "Gen_Stop_Fail": "Generator failed to stop",
        "Gen_Fault": "Generator fault signal active",
        "Sump_Max_Run_Fault": "Sump pump max run time exceeded",
        "Sump_Cycle_Rate_Alarm": "Sump pump cycling too frequently",
        "Elec_Overload_Alarm": "Electrical overload detected",
        "Elec_Gen_Overload_Alarm": "Generator overload detected",
        "Freeze_Warning": "Freeze warning - outdoor temp below 35F",
        "Freeze_Critical": "Freeze critical - outdoor temp below 20F",
        "Leak_Any_Alarm": "Water leak detected",
        "Garage_Open_Alarm": "Garage door open too long",
        "Well_Pump_Short_Cycle_Alarm": "Well pump short cycling",
        "Water_Pressure_Low_Alarm": "Low water pressure",
        "HVAC_Short_Cycle_Alarm": "HVAC short cycle detected",
        "HVAC_Filter_Change_Due": "HVAC filter change due",
        "Maint_Gen_Oil_Due": "Generator oil change due",
        "Maint_Sump_Inspect_Due": "Sump pump inspection due",
        "Maint_Furnace_Inspect_Due": "Furnace inspection due",
        "Load_Shed_Active": "Load shedding activated",
        "HVAC_Efficiency_Alarm": "HVAC efficiency degraded",
    }

    def __init__(self):
        self.config = {
            "enabled": False,
            "smtp_server": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "recipients": [],
            "cooldown_minutes": 30,
        }
        self.last_sent = {}    # tag -> last sent datetime
        self.alert_log = []    # recent alerts list
        self._lock = threading.Lock()
        self.load_config()

    def load_config(self):
        """Load config from JSON file if it exists."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                self.config.update(saved)
        except Exception as e:
            print(f"AlertManager: could not load config: {e}")

    def save_config(self):
        """Save config to JSON file."""
        try:
            config_dir = os.path.dirname(self.CONFIG_FILE)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"AlertManager: could not save config: {e}")

    def get_config_safe(self):
        """Return config with password masked."""
        safe = dict(self.config)
        if safe.get("smtp_password"):
            safe["smtp_password"] = "********"
        return safe

    def update_config(self, new_config):
        """Update config from dict and save."""
        # If password is masked, keep the existing password
        if new_config.get("smtp_password") == "********":
            new_config["smtp_password"] = self.config.get("smtp_password", "")
        self.config.update(new_config)
        self.save_config()

    def check_and_send(self, tag_dict):
        """Check alarm tags and send alerts if triggered and not in cooldown."""
        if not self.config.get("enabled"):
            return

        cooldown = self.config.get("cooldown_minutes", 30)

        for tag, message in self.ALARM_MESSAGES.items():
            val = tag_dict.get(tag)
            if val is True or val == 1:
                now = datetime.now()
                with self._lock:
                    last = self.last_sent.get(tag)
                    if last and (now - last).total_seconds() < cooldown * 60:
                        continue  # still in cooldown
                    self.last_sent[tag] = now

                subject = f"HomePLC Alert: {message}"
                body = (
                    f"Alert: {message}\n"
                    f"Tag: {tag}\n"
                    f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"\n"
                    f"This is an automated alert from HomePLC."
                )

                self.send_alert(subject, body)
                with self._lock:
                    self.alert_log.append({
                        "timestamp": now.isoformat(),
                        "tag": tag,
                        "message": message,
                        "status": "sent",
                    })
                    # Keep log to a reasonable size
                    if len(self.alert_log) > 200:
                        self.alert_log = self.alert_log[-200:]

    def send_alert(self, subject, body):
        """Send email alert using SMTP."""
        try:
            recipients = self.config.get("recipients", [])
            if not recipients:
                print("AlertManager: no recipients configured")
                return False

            msg = MIMEMultipart()
            msg["From"] = self.config.get("smtp_user", "homeplc@localhost")
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = self.config.get("smtp_server", "")
            port = self.config.get("smtp_port", 587)
            user = self.config.get("smtp_user", "")
            password = self.config.get("smtp_password", "")

            if not server:
                print("AlertManager: no SMTP server configured")
                return False

            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if user and password:
                    smtp.login(user, password)
                smtp.sendmail(msg["From"], recipients, msg.as_string())

            print(f"AlertManager: sent alert - {subject}")
            return True

        except Exception as e:
            print(f"AlertManager: send failed - {e}")
            with self._lock:
                self.alert_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "tag": "_error",
                    "message": f"Send failed: {e}",
                    "status": "error",
                })
            return False

    def send_test(self):
        """Send a test email to verify config."""
        subject = "HomePLC Alert Test"
        body = (
            "This is a test alert from HomePLC.\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "\nIf you received this, your alert configuration is working."
        )
        ok = self.send_alert(subject, body)
        with self._lock:
            self.alert_log.append({
                "timestamp": datetime.now().isoformat(),
                "tag": "_test",
                "message": "Test alert" + (" sent" if ok else " failed"),
                "status": "sent" if ok else "error",
            })
        return ok

    def get_log(self, limit=50):
        """Return recent alert log entries."""
        with self._lock:
            return list(reversed(self.alert_log[-limit:]))
