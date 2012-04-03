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
from WebSocketServer import WebSocketServer, WebSocketCode, WebSocketException

# Define how clients' data is treated
# /handler/ represents the WebSocket client object that received the data
# /data/ is the UTF-8 string (or the byte array) that was received
def handle(handler, data):
    """
    Handle a message from a client
    """
    # Broadcast the received message with (ip, socket) prefixed
    for t in handler.server.clients:
        if handler.addr != t.addr:
            try:
                t.send("{},{}:{}".format(handler.addr[0], handler.addr[1], data))
            except WebSocketException.ClientBadState:
                pass

# Create the WebSocket server object
server = WebSocketServer.server(
    addr="",
    host="localhost",
    port=8080,
    handle=handle,
    debug=WebSocketCode.WebSocketDebugLevel.PRINT_ERROR
)

# Ask the server to stop on SIGINT(2) or SIGTERM(15)
def die(signum, frame):
    print("signal received: {}".format(signum))
    server.updateState(WebSocketCode.WebSocketServerState.STATE_STOPPING)

signal.signal(signal.SIGINT,  die)
signal.signal(signal.SIGTERM, die)

server.start()

# The __main__ thread shouldn't terminate, otherwise signals couldn't be
# handled and the server (so as other threads) would become orphaned
while server._state == WebSocketCode.WebSocketServerState.STATE_STARTED:
    signal.pause()
