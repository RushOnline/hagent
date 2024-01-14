# You can run this .tac file directly with:
#    twistd -ny service.tac
# apt install pm-utils # x11-xserver-utils

"""
This is an example .tac file which starts a webserver on port 8080 and
serves files from the current working directory.

The important part of this, the part that makes it a .tac file, is
the final root-level section, which sets up the object called 'application'
which twistd will look for
"""

import os
import subprocess
import json
from time import sleep

from twisted.application import internet, service
from twisted.web import server, static
from twisted.web.resource import Resource
from twisted.python import log

import sys

from twisted.internet.defer       import inlineCallbacks, DeferredList
from twisted.internet             import reactor
from twisted.internet.endpoints   import clientFromString
from twisted.application.internet import ClientService, backoffPolicy

from zeroconf import Zeroconf
from mqtt.client.factory import MQTTFactory
import configparser

# Global variables
class state:
    dpms = True
    sleep = 0

config = configparser.ConfigParser()

broker_type = '_mqtt._tcp.local.'
broker_name = 'Your mosquitto service name'
broker_address = None
broker_login = None
broker_password = None

# Handler functions

def screen_width():
    return int(subprocess.check_output(["xrandr"]).decode("utf-8").split('\n')[0].split(',')[1].split()[1])

def monitor_width():
    return int(subprocess.check_output(["xrandr"]).decode("utf-8").split('\n')[1].split()[3].split('x')[0])

def toggle_hdmi():
    if monitor_width() == screen_width():
        subprocess.Popen("xrandr --output HDMI-0 --auto --left-of DVI-D-0".split())
    else:
        subprocess.Popen("xrandr --output HDMI-0 --off".split())

def handle_command(cmd):
    if cmd != 'sleep': state.sleep = 0

    if cmd == 'toggle-dpms':
        state.dpms = not state.dpms
        if state.dpms:
            log.msg(f'DPMS ON')
            subprocess.Popen("xset dpms force on".split()).wait()
        else:
            log.msg(f'DPMS OFF')
            subprocess.Popen("xset dpms force off".split()).wait()
    elif cmd == 'sleep':
        state.sleep += 1
        if state.sleep > 3:
            subprocess.Popen("systemctl suspend --ignore-inhibitors --no-ask-password".split()).wait()
            state.sleep = 0
    elif cmd == 'toggle-hdmi':
        toggle_hdmi()
    else:
        log.msg(f'Unknown command: {cmd}')

class Dispatcher(Resource):
    def render_POST(self, request):
        params = json.loads(request.content.read())

        log.msg(f'content: {params}')

        cmd = params.get('command', None)
        if cmd != 'sleep': state.sleep = 0
    
        if cmd == 'toggle-dpms':
            state.dpms = not state.dpms
            if state.dpms:
                log.msg(f'DPMS ON')
                subprocess.Popen("xset dpms force on".split()).wait()
            else:
                log.msg(f'DPMS OFF')
                subprocess.Popen("xset dpms force off".split()).wait()
        elif cmd == 'sleep':
            state.sleep += 1
            if state.sleep > 3:
                subprocess.Popen("systemctl suspend --ignore-inhibitors --no-ask-password".split()).wait()
                state.sleep = 0
        elif cmd == 'toggle-hdmi':
            toggle_hdmi()
        
        request.responseHeaders.addRawHeader("Content-Type", "application/json")
        return ('{ "command": "hz" }'.encode('utf-8'))

def getWebService():
    """
    Return a service suitable for creating an application object.

    This service is a simple web server that serves files on port 8080 from
    underneath the current working directory.
    """
    # create a resource to serve static files
    hagent = Resource()
    hagent.putChild(b"api", Dispatcher())

    root = Resource()
    root.putChild(b"hagent", hagent)
    
    site = server.Site(root)
    return internet.TCPServer(8282, site)

# -----------------------
# MQTT Subscriber Service
# ------------------------

class MQTTService(ClientService):


    def __init(self, endpoint, factory):
        ClientService.__init__(self, endpoint, factory, retryPolicy=backoffPolicy())


    def startService(self):
        log.msg(f"starting MQTT Client Subscriber Service")
        # invoke whenConnected() inherited method
        self.whenConnected().addCallback(self.connectToBroker)
        ClientService.startService(self)


    @inlineCallbacks
    def connectToBroker(self, protocol):
        '''
        Connect to MQTT broker
        '''
        self.protocol                 = protocol
        self.protocol.onPublish       = self.onPublish
        self.protocol.onDisconnection = self.onDisconnection
        self.protocol.setWindowSize(3)

        try:
            yield self.protocol.connect("TwistedMQTT-subs", keepalive=60,
                                        username=broker_login,password=broker_password)
            yield self.subscribe()
        except Exception as e:
            log.msg(f"Connecting to {broker_name} raised {e!s}")
        else:
            log.msg(f"Connected and subscribed to {broker_name}")


    def subscribe(self):

        def _logFailure(failure):
            log.msg(f"subscribe to arcturus/command has been failed: {failure.getErrorMessage()}")
            return failure

        def _logSuccess(value):
            log.msg(f"subscribed to arcturus/command: {value}")
            return True

        d1 = self.protocol.subscribe("arcturus/command", 0 )
        d1.addCallbacks(_logSuccess, _logFailure)
        return d1

    def onPublish(self, topic, payload, qos, dup, retain, msgId):
        '''
        Callback Receiving messages from publisher
        '''
        log.msg(f"msg={payload}")
        handle_command(payload.decode("utf-8"))


    def onDisconnection(self, reason):
        '''
        get notfied of disconnections
        and get a deferred for a new protocol object (next retry)
        '''
        log.msg(f" >< Connection was lost ! ><, reason={reason}")
        self.whenConnected().addCallback(self.connectToBroker)

config.read('hagent.conf')

broker_login = config['broker']['login']
broker_password = config['broker']['password']
broker_type = config['broker']['type']
broker_name = config['broker']['name']

zeroconf = Zeroconf()
try:
    broker_address = config['broker']['address']

    si = zeroconf.get_service_info(broker_type, broker_name + '.' + broker_type)
    broker_address = f"tcp:{si.parsed_addresses().pop(0)}:{si.port}"
    log.msg(f"{broker_name}: {broker_address}")
finally:
    zeroconf.close()

# this is the core part of any tac file, the creation of the root-level
# application object
application = service.Application("Hagent application")

# attach the service to its parent application
service = getWebService()
service.setServiceParent(application)

mqttFactory     = MQTTFactory(profile=MQTTFactory.SUBSCRIBER)
mqttEndpoint    = clientFromString(reactor, config['broker']['address'])
mqttService     = MQTTService(mqttEndpoint, mqttFactory)
mqttService.setServiceParent(application)
