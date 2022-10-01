# You can run this .tac file directly with:
#    twistd -ny service.tac

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

class state:
    dpms = True
    sleep = 0

def screen_width():
    return int(subprocess.check_output(["xrandr"]).decode("utf-8").split('\n')[0].split(',')[1].split()[1])

def monitor_width():
    return int(subprocess.check_output(["xrandr"]).decode("utf-8").split('\n')[1].split()[3].split('x')[0])

def toggle_hdmi():
    if monitor_width() == screen_width():
        subprocess.Popen("xrandr --output HDMI-0 --auto --left-of DVI-D-0".split())
    else:
        subprocess.Popen("xrandr --output HDMI-0 --off".split())

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

# this is the core part of any tac file, the creation of the root-level
# application object
application = service.Application("Hagent application")

# attach the service to its parent application
service = getWebService()
service.setServiceParent(application)
