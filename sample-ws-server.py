#!/usr/bin/env python3
#-*- coding: utf-8 -*-
#
# Copyright 2010 Houillon Nelson <houillon.nelson@gmail.com>
#
# Sample server using WebSocketServer.server
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import sys
import signal
from time import sleep
from WebSocketServer import WebSocketServer, WebSocketCode

# Define how clients' data is treated
# "handler" represents the thread that handles the data
# "data" is the UTF-8 string (or the byte array) the thread just received
def handle(handler, msg):
    """
    Handle a message from a client
    """
    # Broadcast the message with (ip, socket) prefixed
    for t in handler.server.threadPool:
        if handler.addr != t.addr:
            t.send("{},{}:{}".format(handler.addr[0], handler.addr[1], msg))

# Create the server and give it the method to trigger when receiving data from
# a client
server = WebSocketServer.server(
    addr="",
    host="localhost",
    port=8080,
    handle=handle,
    debug=WebSocketCode.WebSocketDebugLevel.PRINT_INFO
)

# Ask the server to stop on SIGINT(2) or SIGTERM(15)
def die(signum, frame):
    server.stop()

signal.signal(signal.SIGINT,  die)
signal.signal(signal.SIGTERM, die)

server.start()

# The __main__ thread shouldn't terminate, otherwise signals couldn't be
# handled and the server (so as other threads) would become orphaned
while server.running and server.threadPool:
    signal.pause()
