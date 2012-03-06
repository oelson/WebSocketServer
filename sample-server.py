#!/usr/bin/python3
#-*- coding: utf-8 -*-
#
#    Sample server using WebSocketServer 0.3
#
#    Copyright 2010 Houillon Nelson <houillon.nelson@gmail.com>
#
#    This file shows how the class WebSocketServer() should be used in order to
#    create a dedicated WebSocket server
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA 02110-1301, USA.

import sys
import signal
from time import sleep
from WebSocketServer import WebSocketServer

# Define how clients' data is treated
# "self" represents the thread that handles the data
# "data" is the UTF-8 string the thread just received
def handle(self, data):
    """
    Here are some example of how you can handle data:
    """
    # Send the message to all other clients (except the current thread's one):
    for thread in self.master.threadPool:
        if self.addr != thread.addr:
            thread.send(data)
    ## Or just re-send the string to the thread's *own* client
    #self.send(data)
    ## You can terminate a connection by calling the self.close() method

# Create the server and give it the method to trigger when receiving data from
# a client
server = WebSocketServer.server(
    addr="",
    host="localhost",
    port=8080,
    handle=handle
)

# Close the server on SIGINT(2) or SIGTERM(15)
def die(signum, frame):
    server.stop()
    exit(0)

signal.signal(signal.SIGINT,  die)
signal.signal(signal.SIGTERM, die)

server.start()

# The __main__ thread shouldn't terminate, otherwise signals couldn't be
# handled and the server (so as other threads) would become orphaned
while server.running:
    sleep(.1)
