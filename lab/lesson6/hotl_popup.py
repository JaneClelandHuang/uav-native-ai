#!/usr/bin/env python3
"""hotl_popup.py -- the Human-on-the-Loop operator popup for HW6 (PyQt5).

Provided, finished and unwired: there is no planner behind it. Your planner
talks to it over MQTT, and the topics and payloads below are the contract
your planner must honor (see "The popup contract" in the HW6 spec:
https://janeclelandhuang.github.io/uav-native-ai/lessons/lesson6.html#the-popup-contract). You shouldn't
need to edit this file. If you do, say why in design.md.

  MissionBridge  -- paho-mqtt client. paho calls back on its own network
                    thread, and Qt widgets may only be touched from the GUI
                    thread, so every message is re-emitted as a Qt signal.
  DecisionDialog -- one non-modal popup per event: what was seen, where,
                    by whom, the state of each UAV, one button per candidate
                    response and that response's parameters, then the
                    validator's verdict and live execution status.
  StatusWindow   -- an always-open list of what each UAV is doing, with
                    Cancel (stop the response, resume mission) and Abort
                    (return to launch) per UAV.

The operator never flies the UAV here: they choose a *high-level response*
from the planner's menu, and the planner validates and executes it.

Topics:
    in   mission/decision_request, mission/action_result, mission/behavior_status
    out  mission/decision, mission/cancel, mission/abort

Run with any Python that has PyQt5 and paho-mqtt (gui/'s requirements have both):

    python lab/lesson6/hotl_popup.py
"""
import base64
import json
import os
import sys
import time

import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

STATE_COLORS = {"PENDING": "#b8860b", "RUNNING": "#1e6fd9", "COMPLETED": "#2e8b57",
                "FAILED": "#c0392b", "CANCELLED": "#7f8c8d"}


class MissionBridge(QObject):
    """MQTT <-> Qt signals. The only class that knows about paho."""

    decision_requested = pyqtSignal(dict)
    action_result = pyqtSignal(dict)
    behavior_status = pyqtSignal(dict)

    _TOPICS = {
        "mission/decision_request": "decision_requested",
        "mission/action_result": "action_result",
        "mission/behavior_status": "behavior_status",
    }

    def __init__(self):
        super().__init__()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def start(self):
        self._client.connect(MQTT_HOST, MQTT_PORT)
        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        for topic in self._TOPICS:
            client.subscribe(topic)

    def _on_message(self, client, userdata, msg):  # paho thread
        try:
            data = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        getattr(self, self._TOPICS[msg.topic]).emit(data)  # -> GUI thread

    def send_decision(self, request_id, action):
        self._client.publish("mission/decision", json.dumps({"request_id": request_id, "action": action}))

    def dismiss(self, request_id):
        self._client.publish("mission/decision", json.dumps({"request_id": request_id, "dismiss": True}))

    def cancel(self, uav, action_id=None):
        # action_id names the response being cancelled, so a cancel that
        # races a newly approved response can't stop the new one by mistake.
        self._client.publish("mission/cancel", json.dumps({"uav": uav, "action_id": action_id}))

    def abort(self, uav):
        self._client.publish("mission/abort", json.dumps({"uav": uav}))


def _fmt_battery(level):
    return "unknown" if level is None else f"{level:.0%}"


class DecisionDialog(QDialog):
    """Popup for one event. Stays open after sending so the operator sees
    the verdict; if the planner re-asks (after a rejection) the same dialog
    is re-used with the new request."""

    def __init__(self, bridge, request, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.event = request["event"]
        self.request = None
        self.action_id = None
        self.setWindowTitle(f"{self.event['type'].upper()} DETECTED")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        self.header = QLabel()
        self.header.setTextFormat(Qt.RichText)
        layout.addWidget(self.header)

        row = QHBoxLayout()
        self.snapshot = QLabel("(no image)")
        self.snapshot.setAlignment(Qt.AlignCenter)
        self.snapshot.setMinimumSize(320, 220)
        row.addWidget(self.snapshot)
        self.uav_info = QLabel()
        self.uav_info.setTextFormat(Qt.RichText)
        self.uav_info.setAlignment(Qt.AlignTop)
        row.addWidget(self.uav_info, 1)
        layout.addLayout(row)

        self.rejection = QLabel()
        self.rejection.setWordWrap(True)
        self.rejection.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.rejection.hide()
        layout.addWidget(self.rejection)

        box = QGroupBox("SELECT RESPONSE")
        box_layout = QVBoxLayout(box)
        self.button_row = QGridLayout()
        box_layout.addLayout(self.button_row)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color: gray;")
        box_layout.addWidget(self.description)
        self.form = QFormLayout()
        box_layout.addLayout(self.form)
        layout.addWidget(box)
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        self.buttons.buttonClicked.connect(self._on_response_chosen)

        actions = QHBoxLayout()
        self.countdown = QLabel()
        self.countdown.setStyleSheet("color: gray;")
        actions.addWidget(self.countdown, 1)
        self.dismiss_btn = QPushButton("No action")
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        actions.addWidget(self.dismiss_btn)
        self.send_btn = QPushButton("Send response")
        self.send_btn.setDefault(True)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._on_send)
        actions.addWidget(self.send_btn)
        layout.addLayout(actions)

        self.verdict = QLabel()
        self.verdict.setWordWrap(True)
        layout.addWidget(self.verdict)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_countdown)
        self._timer.start(1000)

        self.load_request(request)

    # -- a (new) decision request for this event --------------------------
    def load_request(self, request):
        self.request = request
        self._deadline = time.time() + request.get("timeout_s", 180)
        ev = self.event
        self.header.setText(
            f"<h2>POSSIBLE {ev['type'].upper()} DETECTED</h2>"
            f"Location: {ev['lat']:.6f}, {ev['lon']:.6f}<br>"
            f"Confidence: {ev['confidence']:.2f}<br>"
            f"Detected by: UAV {ev.get('source_uav')}")
        if ev.get("image_b64"):
            pix = QPixmap()
            pix.loadFromData(base64.b64decode(ev["image_b64"]))
            self.snapshot.setPixmap(pix.scaled(320, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lines = []
        for u in request["world_state"]["uavs"]:
            lines.append(
                f"<b>UAV {u['uav']} ({u['color']})</b><br>"
                f"Battery: {_fmt_battery(u['battery_level'])}<br>"
                f"Payload: {', '.join(u['payloads']) or 'none'}<br>"
                f"Current task: {u['current_behavior'] or 'idle'}")
        self.uav_info.setText("<br><br>".join(lines))
        if request.get("previous_rejection"):
            self.rejection.setText("Previous choice REJECTED: " + " ".join(request["previous_rejection"])
                                   + " Choose again.")
            self.rejection.show()

        for btn in self.buttons.buttons():
            self.buttons.removeButton(btn)
            btn.deleteLater()
        self.candidates = {c["type"]: c for c in request["candidates"]}
        for i, cand in enumerate(request["candidates"]):
            btn = QPushButton(cand["label"])
            btn.setCheckable(True)
            btn.setProperty("response_type", cand["type"])
            self.buttons.addButton(btn)
            self.button_row.addWidget(btn, i // 3, i % 3)
        self._clear_form()
        self.send_btn.setEnabled(False)
        self.dismiss_btn.setEnabled(True)
        self.verdict.clear()
        self.show()
        self.raise_()
        self.activateWindow()

    def _clear_form(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields = {}

    def _on_response_chosen(self, button):
        cand = self.candidates[button.property("response_type")]
        self.description.setText(cand["description"])
        self._clear_form()
        uav_box = QComboBox()
        uav_box.addItems(cand["eligible_uavs"])
        if cand["default_uav"] in cand["eligible_uavs"]:
            uav_box.setCurrentText(cand["default_uav"])
        self.form.addRow("UAV", uav_box)
        self.fields["uav"] = uav_box
        for name, value in cand["parameters"].items():
            options = cand.get("options", {}).get(name)
            if options:
                widget = QComboBox()
                widget.addItems(options)
                if value in options:
                    widget.setCurrentText(value)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                widget = QDoubleSpinBox()
                widget.setRange(-10000, 10000)
                widget.setDecimals(1)
                widget.setValue(value)
            else:
                widget = QLineEdit("" if value is None else str(value))
            self.form.addRow(name, widget)
            self.fields[name] = widget
        self.send_btn.setEnabled(True)

    def _read_fields(self):
        values = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                values[name] = widget.currentText()
            elif isinstance(widget, QDoubleSpinBox):
                values[name] = widget.value()
            else:
                values[name] = widget.text()
        return values

    def _on_send(self):
        response_type = self.buttons.checkedButton().property("response_type")
        values = self._read_fields()
        uav = values.pop("uav")
        action = {"type": response_type, "uav": uav,
                  "target": {"lat": self.event["lat"], "lon": self.event["lon"]},
                  "parameters": values}
        self.bridge.send_decision(self.request["request_id"], action)
        self.send_btn.setEnabled(False)
        self.dismiss_btn.setEnabled(False)
        self.rejection.hide()
        self.verdict.setText("Sent -- waiting for validation...")

    def _on_dismiss(self):
        self.bridge.dismiss(self.request["request_id"])
        self.close()

    def _tick_countdown(self):
        if self.send_btn.isEnabled() or self.dismiss_btn.isEnabled():
            left = max(0, int(self._deadline - time.time()))
            self.countdown.setText(f"{left}s to decide" if left else "Timed out (no action)")
        else:
            self.countdown.clear()

    # -- planner feedback --------------------------------------------------
    def on_action_result(self, result):
        if result.get("request_id") != self.request["request_id"]:
            return
        if result["approved"]:
            self.action_id = result["action_id"]
            notes = (" " + " ".join(result["reasons"])) if result["reasons"] else ""
            self.verdict.setText(f"<b style='color:#2e8b57'>APPROVED</b> -- {result['type']} "
                                 f"on UAV {result['uav']}.{notes}")
        else:
            # The planner will re-ask with a fresh request (load_request).
            self.verdict.setText("<b style='color:#c0392b'>REJECTED</b>: " + " ".join(result["reasons"]))

    def on_behavior_status(self, status):
        if self.action_id is None or status.get("action_id") != self.action_id:
            return
        color = STATE_COLORS.get(status["state"], "black")
        stream = (f"<br><i>Enable camera streaming for this drone in new-gui.</i>"
                  if status.get("stream_required") and status["state"] == "RUNNING" else "")
        self.status.setText(f"<b style='color:{color}'>{status['state']}</b> -- {status['detail']}{stream}")


class StatusWindow(QWidget):
    """Always-open overview: what each UAV is doing, with Cancel/Abort."""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("Mission status")
        self.grid = QGridLayout(self)
        self.grid.addWidget(QLabel("<b>Waiting for planner status...</b>"), 0, 0, 1, 4)
        self.rows = {}
        self.action_ids = {}  # uav -> action_id of the response its row shows

    def on_behavior_status(self, status):
        uav = status["uav"]
        if uav not in self.rows:
            r = len(self.rows) + 1
            label = QLabel()
            label.setTextFormat(Qt.RichText)
            cancel = QPushButton("Cancel response")
            cancel.clicked.connect(lambda _=False, u=uav: self.bridge.cancel(u, self.action_ids.get(u)))
            abort = QPushButton("Abort (RTL)")
            abort.clicked.connect(lambda _=False, u=uav: self.bridge.abort(u))
            self.grid.addWidget(QLabel(f"<b>UAV {uav}</b>"), r, 0)
            self.grid.addWidget(label, r, 1)
            self.grid.addWidget(cancel, r, 2)
            self.grid.addWidget(abort, r, 3)
            self.rows[uav] = label
        self.action_ids[uav] = status.get("action_id")
        color = STATE_COLORS.get(status["state"], "black")
        self.rows[uav].setText(f"{status['behavior']}: <span style='color:{color}'>{status['state']}</span>"
                               f" -- {status['detail']}")


def main():
    app = QApplication(sys.argv)
    bridge = MissionBridge()
    status_window = StatusWindow(bridge)
    status_window.resize(700, 120)
    status_window.show()
    dialogs = {}  # event_id -> DecisionDialog

    def on_request(request):
        event_id = request["event"]["event_id"]
        dialog = dialogs.get(event_id)
        if dialog is not None:
            try:
                dialog.load_request(request)  # re-ask after a rejection
                return
            except RuntimeError:  # underlying Qt object already deleted (closed)
                pass
        dialog = DecisionDialog(bridge, request)
        bridge.action_result.connect(dialog.on_action_result)
        bridge.behavior_status.connect(dialog.on_behavior_status)
        dialog.destroyed.connect(lambda _=None, e=event_id: dialogs.pop(e, None))
        dialogs[event_id] = dialog

    bridge.decision_requested.connect(on_request)
    bridge.behavior_status.connect(status_window.on_behavior_status)
    bridge.start()
    code = app.exec_()
    bridge.stop()
    sys.exit(code)


if __name__ == "__main__":
    main()
