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


from .WebSocketCode import CloseFrameStatusCode

class WebSocketException(Exception):
    detail = "unknown websocket error"
    def __init__(self, detail=""):
        if isinstance(detail, str):
            self.detail += " ("+detail+")"
    def __str__(self):
        return self.detail

class ClientBadState(WebSocketException):
    detail = "client bad state"

class ServerBadState(WebSocketException):
    detail = "server bad state"

class BadHandShake(WebSocketException):
    detail = "bad handshake"

class CloseFrameReceived(WebSocketException):
    detail = "close frame received (status={} {}, reason=\"{}\")"
    status = CloseFrameStatusCode.NO_STATUS_RECVD
    reason = ""
    def __init__(self, status=CloseFrameStatusCode.NO_STATUS_RECVD, reason=""):
        self.status = status
        self.reason = reason
    def __str__(self):
        return self.detail.format(
            self.status,
            WebSocketCode.CloseFrameStatusCode.name[self.status],
            self.reason
        )

class ClientSleeping(WebSocketException):
    detail = "client is sleeping"

class DataMaskingError(WebSocketException):
    detail = "data masking error"

class MessageTooBig(WebSocketException):
    detail = "message too big"

class BadFrame(WebSocketException):
    detail = "bad frame"

class IncompleteFrame(BadFrame):
    detail = "incomplete frame"

class PayloadDataNotUnicode(BadFrame):
    detail = "payload data cannot be decoded as utf-8"
