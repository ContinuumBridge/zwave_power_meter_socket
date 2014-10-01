#!/usr/bin/env python
# zwave_power_meter_socket.py
# Copyright (C) ContinuumBridge Limited, 2014 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
ModuleName = "zwave_power_meter_socket"

import sys
import time
import os
import logging
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor

class Adaptor(CbAdaptor):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.status =           "ok"
        self.state =            "stopped"
        self.apps =             {"energy": [],
                                 "power": [],
                                 "voltage": [],
                                 "current": [],
                                 "power_factor": [],
                                 "switch": [],
                                 "conneted": []}
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def setState(self, action):
        # error is only ever set from the running state, so set back to running if error is cleared
        if action == "error":
            self.state == "error"
        elif action == "clear_error":
            self.state = "running"
        logging.debug("%s %s state = %s", ModuleName, self.id, self.state)
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

    def checkAllProcessed(self, appID):
        self.processedApps.append(appID)
        found = True
        for a in self.appInstances:
            if a not in self.processedApps:
                found = False
        if found:
            self.setState("inUse")

    def onZwaveMessage(self, message):
        logging.debug("%s %s onZwaveMessage, message: %s", ModuleName, self.id, str(message))
        if message["content"] == "init":
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
            reactor.callLater(30, self.pollSensors)
        elif message["content"] == "data":
            try:
                if message["commandClass"] == "50":
                    if message["data"]["name"] == "0":
                        energy = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, energy (KWh): %s", ModuleName, self.id, str(energy))
                        self.sendCharacteristic("energy", energy, time.time())
                    elif message["data"]["name"] == "2":
                        power = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, power (W): %s", ModuleName, self.id, str(power))
                        self.sendCharacteristic("power", power, time.time())
                    elif message["data"]["name"] == "4":
                        voltage = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, voltage: %s", ModuleName, self.id, str(voltage))
                        self.sendCharacteristic("voltage", voltage, time.time())
                    elif message["data"]["name"] == "5":
                        current = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, current: %s", ModuleName, self.id, str(current))
                        self.sendCharacteristic("current", current, time.time())
                    elif message["data"]["name"] == "6":
                        power_factor = message["data"]["val"]["value"] 
                        logging.debug("%s %s onZwaveMessage, power_factor: %s", ModuleName, self.id, str(power_factor))
                        self.sendCharacteristic("power_factor", power_factor, time.time())
                elif message["commandClass"] == "48":
                    if message["data"]["name"] == "1":
                        if message["data"]["level"]["value"]:
                            b = "on"
                        else:
                            b = "off"
                        logging.debug("%s %s onZwaveMessage, alarm: %s", ModuleName, self.id, b)
                        self.sendCharacteristic("binary_sensor", b, time.time())
            except:
                logging.warning("%s %s onZwaveMessage, unexpected message", ModuleName, str(message))

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
        #logging.debug("%s %s %s onAppInit, req = %s", ModuleName, self.id, self.friendly_name, message)
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "service": [{"characteristic": "energy", "interval": 60},
                            {"characteristic": "power", "interval": 60},
                            {"characteristic": "voltage", "interval": 60},
                            {"characteristic": "current", "interval": 60},
                            {"characteristic": "power_factor", "interval": 60},
                            {"characteristic": "connected", "interval": 60},
                            {"characteristic": "switch", "interval": 300}],
                "content": "service"}
        self.sendMessage(resp, message["id"])
        self.setState("running")

    def onAppCommand(self, message):
        #logging.debug("%s %s %s onAppCommand, req = %s", ModuleName, self.id, self.friendly_name, message)
        if "data" not in message:
            logging.warning("%s %s %s app message without data: %s", ModuleName, self.id, self.friendly_name, message)
        elif message["data"] != "on" and message["data"] != "off":
            logging.warning("%s %s %s app switch state must be on or off: %s", ModuleName, self.id, self.friendly_name, message)
        else:
            self.switch(message["data"])

    def onConfigureMessage(self, config):
        """Config is based on what apps are to be connected.
            May be called again if there is a new configuration, which
            could be because a new app has been added.
        """
        logging.debug("%s onConfigureMessage, config: %s", ModuleName, config)
        self.setState("starting")

if __name__ == '__main__':
    Adaptor(sys.argv)
