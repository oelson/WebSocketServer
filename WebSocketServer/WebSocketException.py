#-*- coding: utf-8 -*-
#
#    Copyright 2010 Houillon Nelson <houillon.nelson@gmail.com>
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

class WebSocketException(Exception):
    value = "WebSocketException"
    def __init__(self):
        pass
    def __str__(self):
        return self.value

class WebSocketBadHost(WebSocketException):
    """
    Raised if the host header given by the client don't match with the host name
    associated to the server
    """
    pass

class WebSocketBadHandShake(WebSocketException):
    """
    Raised when the client's handshake is invalid (either malformed or if it's
    using an old specification of the protocol)
    """
    pass

class WebSocketBadFrame(WebSocketException):
    """
    Raised if the client send an invalid WebSocket frame
    The two supported frame types are:
        o data frames
        o disconnexion frame
    """
    pass
    
class WebSocketClose(WebSocketException):
    """
    Raised if the client send a disconnexion frame or if an error occured
    """
    pass

class WebSocketBadClose(WebSocketException):
    """
    Raised if the client close the connexion without respecting the protocol
    """
    pass
