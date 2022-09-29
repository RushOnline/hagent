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

from twisted.application import internet, service
from twisted.web import server, static
from twisted.web.resource import Resource

class Handler(Resource):
    def __init__(self, cmd):
        Resource.__init__(self)
        self.cmd = cmd

    def render_GET(self, request):
        request.responseHeaders.addRawHeader("Content-Type", "text/plain")
        return (b"cmd: " + self.cmd + b"\n")

class Dispatcher(Resource):
  def getChild(self, cmd, request):
      return Handler(cmd)

def getWebService():
    """
    Return a service suitable for creating an application object.

    This service is a simple web server that serves files on port 8080 from
    underneath the current working directory.
    """
    # create a resource to serve static files
    dispatcher = server.Site(Dispatcher())
    return internet.TCPServer(8282, dispatcher)

# this is the core part of any tac file, the creation of the root-level
# application object
application = service.Application("Hagent application")

# attach the service to its parent application
service = getWebService()
service.setServiceParent(application)
