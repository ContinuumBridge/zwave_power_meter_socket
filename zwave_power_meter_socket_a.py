#!/usr/bin/env python
# zwave_power_meter_socket.py
# Copyright (C) ContinuumBridge Limited, 2014 - 2015
# Written by Peter Claydon
#
ModuleName = "zwave_power_meter_socket"
INTERVAL                 = 60         # How often to request sensor values
CHECK_ALIVE_INTERVAL     = 120 
TIME_CUTOFF              = 1800       # Data older than this is considered "stale"

import sys
import time
import os
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor

class Adaptor(CbAdaptor):
    def __init__(self, argv):
        self.status =           "ok"
        self.state =            "stopped"
        self.connected =        False
        self.switchState =      "unknown"
        self.apps =             {"energy": [],
                                 "power": [],
                                 "voltage": [],
                                 "current": [],
                                 "power_factor": [],
                                 "binary_sensor": [],
                                 "switch": [],
                                 "connected": []}
        self.lastEnergyTime =    0
        self.lastPowerTime =     0
        self.lastVoltageTime =   0
        self.lastCurrentTime =   0
        self.lastPowerFactorTime = 0
        self.lastBinaryTime =    0
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def setState(self, action):
        # error is only ever set from the running state, so set back to running if error is cleared
        if action == "error":
            self.state == "error"
        elif action == "clear_error":
            self.state = "running"
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def sendCharacteristic(self, characteristic, data, timeStamp):
        msg = {"id": self.id,
               "content": "characteristic",
               "characteristic": characteristic,
               "data": data,
               "timeStamp": timeStamp}
        for a in self.apps[characteristic]:
            reactor.callFromThread(self.sendMessage, msg, a)

    def onStop(self):
        # Mainly caters for situation where adaptor is told to stop while it is starting
        pass

    def pollSensors(self):
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "50",
               "action": "Get",
               "value": ""
              }
        self.sendZwaveMessage(cmd)
        reactor.callLater(INTERVAL, self.pollSensors)

    def checkConnected(self):
        if time.time() - self.updateTime > CHECK_ALIVE_INTERVAL + 60:
            self.connected = False
        else:
            self.connected = True
        self.sendCharacteristic("connected", self.connected, time.time())
        reactor.callLater(INTERVAL, self.checkConnected)

    def onZwaveMessage(self, message):
        #self.cbLog("debug", "onZwaveMessage, message: " + str(message))
        if message["content"] == "init":
            self.updateTime = 0
            self.lastUpdateTime = time.time()
            # Energy - KWh
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "50",
                   "value": "0"
                  }
            self.sendZwaveMessage(cmd)
            # Power - W
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "50",
                   "value": "2"
                  }
            self.sendZwaveMessage(cmd)
            # Voltage
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "50",
                   "value": "4"
                  }
            self.sendZwaveMessage(cmd)
            # Current - A
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "50",
                   "value": "5"
                  }
            self.sendZwaveMessage(cmd)
            # Power Factor
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "50",
                   "value": "6"
                  }
            self.sendZwaveMessage(cmd)
            # Switch state
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "37",
                   "value": "level"
                  }
            self.sendZwaveMessage(cmd)
            # wakeup 
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "132",
                   "value": "lastWakeup"
                  }
            self.sendZwaveMessage(cmd)
            reactor.callLater(30, self.pollSensors)
            reactor.callLater(INTERVAL, self.checkConnected)
        elif message["content"] == "data":
            if True:
            #try:
                if message["commandClass"] == "50":
                    if message["value"] == "0":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastEnergyTime and time.time() - updateTime < TIME_CUTOFF:
                            energy = message["data"]["val"]["value"] 
                            self.sendCharacteristic("energy", energy, time.time())
                            self.lastEnergyTime = updateTime
                    elif message["value"] == "2":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastPowerTime and time.time() - updateTime < TIME_CUTOFF:
                            power = message["data"]["val"]["value"] 
                            if power > 4000:
                                self.cbLog("debug", "onZwaveMessage, power " + str(power) + " set to 0")
                                self.cbLog("debug", "onZwaveMessage, power message was: " + str(message))
                                power = 0
                            elif power < -1:
                                self.cbLog("debug", "onZwaveMessage, power " + str(power) + " set to -1")
                                self.cbLog("debug", "onZwaveMessage, power message was: " + str(message))
                                power = -1
                            self.sendCharacteristic("power", power, time.time())
                            self.lastPowerTime = updateTime
                    elif message["value"] == "4":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastVoltageTime and time.time() - updateTime < TIME_CUTOFF:
                            voltage = message["data"]["val"]["value"] 
                            self.sendCharacteristic("voltage", voltage, time.time())
                            self.lastVoltageTime = updateTime
                    elif message["value"] == "5":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastCurrentTime and time.time() - updateTime < TIME_CUTOFF:
                            current = message["data"]["val"]["value"] 
                            self.sendCharacteristic("current", current, time.time())
                            self.lastCurrentTime = updateTime
                    elif message["value"] == "6":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastPowerFactorTime and time.time() - updateTime < TIME_CUTOFF:
                            power_factor = message["data"]["val"]["value"] 
                            self.sendCharacteristic("power_factor", power_factor, time.time())
                            self.lastPowerFactorTime = updateTime
                elif message["commandClass"] == "37":
                    updateTime = message["data"]["updateTime"] 
                    if updateTime != self.lastBinaryTime and time.time() - updateTime < TIME_CUTOFF:
                        if message["value"] == "level":
                            if message["data"]["value"]:
                                b = "on"
                            else:
                                b = "off"
                            self.switchState = b
                            self.sendCharacteristic("binary_sensor", b, time.time())
                            self.lastBinaryTime = updateTime
                self.updateTime = message["data"]["updateTime"]
            #except:
            #    self.cbLog("warning", "onZwaveMessage, unexpected message: " + str(message))

    def onOff(self, s):
        if s == "on":
            return "255"
        else:
            return "0"

    def switch(self, onOrOff):
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "0x25",
               "action": "Set",
               "value": self.onOff(onOrOff)
              }
        self.sendZwaveMessage(cmd)

    def onAppInit(self, message):
        self.cbLog("debug", "onAppInit, req = " + str(message))
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "service": [{"characteristic": "energy", "interval": INTERVAL, "type": "switch"},
                            {"characteristic": "power", "interval": 0, "type": "switch"},
                            {"characteristic": "voltage", "interval": INTERVAL, "type": "switch"},
                            {"characteristic": "current", "interval": INTERVAL, "type": "switch"},
                            {"characteristic": "power_factor", "interval": INTERVAL, "type": "switch"},
                            {"characteristic": "connected", "interval": INTERVAL, "type": "switch"},
                            {"characteristic": "binary_sensor", "interval": 0, "type": "switch"},
                            {"characteristic": "switch", "interval": 0}],
                "content": "service"}
        self.sendMessage(resp, message["id"])
        self.setState("running")

    def onAppRequest(self, message):
        #self.cbLog("debug", "onAppRequest, message: " + str(message))
        # Switch off anything that already exists for this app
        for a in self.apps:
            if message["id"] in self.apps[a]:
                self.apps[a].remove(message["id"])
        # Now update details based on the message
        for f in message["service"]:
            if message["id"] not in self.apps[f["characteristic"]]:
                self.apps[f["characteristic"]].append(message["id"])
        self.cbLog("debug", "onAppRequest, apps: " + str(self.apps))

    def onAppCommand(self, message):
        self.cbLog("debug", "onAppCommand, req: " + str(message))
        if "data" not in message:
            self.cbLog("warning", "app message without data: " +  str(message))
        elif message["data"] != "on" and message["data"] != "off":
            self.cbLog("warning", "This is a sensor. Message not understood: " + str(message))
        else:
            if message["data"] != self.switchState:
                self.switch(message["data"])

    def onConfigureMessage(self, config):
        """Config is based on what apps are to be connected.
            May be called again if there is a new configuration, which
            could be because a new app has been added.
        """
        self.cbLog("debug", "onConfigureMessage, config: " + str(config))
        self.setState("starting")

if __name__ == '__main__':
    Adaptor(sys.argv)
