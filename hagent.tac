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

from twisted.application import internet, service
from twisted.web import server, static
from twisted.web.resource import Resource
from twisted.python import log

class Dispatcher(Resource):
    def render_POST(self, request):
        params = json.loads(request.content.read())
        log.msg(f'content: {params}')
        #subprocess.Popen("xset dpms force off".split())
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
