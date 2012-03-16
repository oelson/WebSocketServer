#-*- coding: utf-8 -*-
# Copyright 2012 Nelson HOUILLON <houillon.nelson@gmail.com>
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

class WebSocketDebugLevel:
    """
    Various debug level
    """
    PRINT_NOTHING = 0 # Quiet
    PRINT_INFO    = 1
    PRINT_ERROR   = 2
    PRINT_DATA    = 3 # Print data flow

class WebSocketState:
    """
    WebSocket connection states
    """
    STATE_CONNECTING        = 0 # Socket opened, handshaking
    STATE_OPEN              = 1 # Hanshake done, receiving & sending
    STATE_CLOSURE_INITIATED = 2 # Closure initiated by the server
    STATE_CLOSURE_REQUESTED = 3 # Closure initiated by the client
    STATE_WAIT_CLOSURE_ACK  = 4 # Waiting for client's close frame
    STATE_CLOSED            = 5 # Close frame received _and_ sent, socket closed
    # Human readable Websocket states
    name = {
        STATE_CONNECTING:         "connecting",
        STATE_OPEN:               "open",
        STATE_CLOSURE_INITIATED:  "closure initiated",
        STATE_CLOSURE_REQUESTED:  "closure requested",
        STATE_WAIT_CLOSURE_ACK:   "waiting closure ack",
        STATE_CLOSED:             "closed"
    }

class OperationCode:
    """
    Frame Operation codes
    """
    # Aliases
    CONTINUATION_FRAME     = 0x0
    TEXT_FRAME             = 0x1
    BINARY_FRAME           = 0x2
    NON_CONTROL_FRAME      = range(0x3, 0x7)
    CONNECTION_CLOSE_FRAME = 0x8
    PING_FRAME             = 0x9
    PONG_FRAME             = 0xA
    CONTROL_FRAME          = range(0xB, 0xF)
    # Human readable frame type
    name = {
        CONTINUATION_FRAME:     "Continuation frame",
        TEXT_FRAME:             "Text frame",
        BINARY_FRAME:           "Binary frame",
        # Non-control frames from 0x3 to 0x7
        CONNECTION_CLOSE_FRAME: "Connection close frame",
        PING_FRAME:             "Ping frame",
        CONTROL_FRAME:          "Pong frame"
        # Control frames from 0xB to 0xF
    }

class CloseFrameStatusCode:
    """
    Close frame status codes
    """
    # Aliases
    NORMAL_CLOSURE        = 1000
    GOING_AWAY            = 1001
    PROTOCOL_ERROR        = 1002
    UNSUPPORTED_DATA      = 1003
    RESERVED              = 1004
    NO_STATUS_RECVD       = 1005
    ABNORMAL_CLOSURE      = 1006
    INVALID_PAYLOAD_DATA  = 1007
    POLICY_VIOLATION      = 1008
    MESSAGE_TOO_BIG       = 1009
    MANDATORY_EXT         = 1010
    INTERNAL_SERVER_ERROR = 1011
    TLS_HANDSHAKE         = 1015
    # Human readable reason for the status
    name = {
        NORMAL_CLOSURE:        "Normal closure",
        GOING_AWAY:            "Going Away",
        PROTOCOL_ERROR:        "Protocol error",
        UNSUPPORTED_DATA:      "Unsupported Data",
        RESERVED:              "---Reserved----",
        NO_STATUS_RECVD:       "No Status Rcvd",
        ABNORMAL_CLOSURE:      "Abnormal Closure",
        INVALID_PAYLOAD_DATA:  "Invalid frame payload data",
        POLICY_VIOLATION:      "Policy Violation",
        MESSAGE_TOO_BIG:       "Message Too Big",
        MANDATORY_EXT:         "Mandatory Ext.",
        INTERNAL_SERVER_ERROR: "Internal Server Error",
        TLS_HANDSHAKE:         "TLS handshake"
    }