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

import types
import socket

from threading import Thread
from sys       import stderr
from struct    import pack, unpack
from hashlib   import sha1
from base64    import b64encode

from .WebSocketException import *
from .WebSocketCode      import *

class server(Thread):
    """
    A WebSocket server object
    Because it is a thread object, the server should be started with its start()
    method
    """
    clients  = []
    _connTimeout = 1.
    _maxDataSize = 4096
    _state = WebSocketServerState.STATE_STARTED
    _valid_state_transition = {
        WebSocketServerState.STATE_STARTED:
            (WebSocketServerState.STATE_STOPPING, ),
        
        WebSocketServerState.STATE_STOPPING:
            (WebSocketServerState.STATE_STOPPED, )
    }
    
    def __init__(self,
                 addr,
                 host,
                 port,
                 handle,
                 init=None,
                 exit=None,
                 debug=WebSocketDebugLevel.PRINT_NOTHING):
        self.addr   = addr
        self.host   = host
        self.port   = port
        self.handle = handle
        self.init   = init
        self.exit   = exit
        self.debug  = debug
        Thread.__init__(self)
    
    def run(self):
        """
        Bind the socket to the wished address/port
        Accept clients forever
        """
        try:
            self.conn = socket.socket()
            self.conn.bind((self.addr, self.port))
            self.conn.listen(0)
            self.conn.settimeout(self._connTimeout)
        except socket.error as e:
            if self.debug >= WebSocketDebugLevel.PRINT_ERROR:
                print("err: cannot bind the socket to '{}':{} {}".format(
                    self.addr, self.port, e),
                    file=stderr)
            try:
                self.conn.close()
            except:
                pass
            self.stop()
            return
        
        if self.debug >= WebSocketDebugLevel.PRINT_INFO:
            print("info: server started")
        
        # Accept new clients forever
        while self.is_alive():
            try:
                sock, addr = self.conn.accept()
            # Check regulary if the stop() method fired
            except socket.timeout:
                continue
            except socket.error:
                break
            t = client(self, sock, addr)
            if self.debug >= WebSocketDebugLevel.PRINT_INFO:
                print("info: client {} start".format(addr))
            t.start()
            self.clients.append(t)
        
        try:
            self.stop()
        except ServerBadState:
            pass
    
    def is_alive(self):
        """
        Return whether the server is able to accept new clients
        """
        return self._state == WebSocketServerState.STATE_STARTED
    
    def updateState(self, state):
        """
        Rules the server's state machine transitions
        """
        old_state = self._state
        if self._state in self._valid_state_transition.keys() and \
                 state in self._valid_state_transition[self._state]:
            self._state = state
        else:
            raise ServerBadState('transition "{}"->"{}" forbidden'.format(
                WebSocketServerState.name[old_state],
                WebSocketServerState.name[state]
            ))
    
    def stop(self):
        self.updateState(WebSocketServerState.STATE_STOPPING)
        # Ask to all clients to stop
        for t in self.clients:
            t.updateState(WebSocketClientState.STATE_CLOSURE_INITIATED)
            try:
                #TODO this is a WORKAROUND: abort any waiting recv() operation
                t.sock.shutdown(socket.SHUT_RD)
            except socket.error as e:
                pass
        # Wait for all clients to return
        for t in self.clients: t.join()
        self.conn.close()
        if self.debug >= WebSocketDebugLevel.PRINT_INFO:
            print("info: server stopped")
    
    def remove(self, t):
        """
        Remove a client
        """
        self.clients.remove(t)
        if self.debug >= WebSocketDebugLevel.PRINT_INFO:
            print("info: client {} exit".format(t.addr))

class client(Thread):
    """
    A WebSocket client object
    """
    _frameStack  = []
    _closeStatus = CloseFrameStatusCode.NO_STATUS_RECVD
    _closeReason = ""

    _state = WebSocketClientState.STATE_CONNECTED

    # state-machine transitions
    _valid_state_transition = {
        WebSocketClientState.STATE_CONNECTED:
            (WebSocketClientState.STATE_HANDSHAKING,
             WebSocketClientState.STATE_DONE),

        WebSocketClientState.STATE_HANDSHAKING:
            (WebSocketClientState.STATE_READY,
             WebSocketClientState.STATE_DONE),

        WebSocketClientState.STATE_READY:
            (WebSocketClientState.STATE_CLOSURE_INITIATED,
             WebSocketClientState.STATE_CLOSURE_REQUESTED,
             WebSocketClientState.STATE_DONE),

        WebSocketClientState.STATE_CLOSURE_INITIATED:
            (WebSocketClientState.STATE_WAIT_CLOSURE_ACK,
             WebSocketClientState.STATE_DONE),

        WebSocketClientState.STATE_CLOSURE_REQUESTED:
            (WebSocketClientState.STATE_DONE, ),

        WebSocketClientState.STATE_WAIT_CLOSURE_ACK:
            (WebSocketClientState.STATE_DONE, ),

        WebSocketClientState.STATE_DONE:
            (WebSocketClientState.STATE_DONE, )
    }
    
    def __init__(self, server, sock, addr):
        self.server = server
        self.sock   = sock
        self.addr   = addr
        Thread.__init__(self)
    
    def run(self):
        """
        Read the client's handshake and respond
        Read and write on the socket until the self.close() method fires
        """
        # Apply the server's common init method on the thread
        if isinstance(self.server.init, types.FunctionType):
            self.server.init(self)
        
        # Handshake with the client
        try:
            self.openingHandShake()
        except BadHandShake as e:
            if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                print("err: {} {}".format(self.addr, e), file=stderr)
            # Abort
            self.updateState(WebSocketClientState.STATE_DONE)
        
        # Receive/send forever
        while self._state == WebSocketClientState.STATE_READY:
            try:
                data = self.recv()
            except IncompleteFrame as e:
                #TODO this is a WORKAROUND: recv() may have been aborted by
                # closing the socket in read mode
                # problem: this implies that we can't read a further close frame
                if self._state == WebSocketClientState.STATE_CLOSURE_INITIATED:
                    break
                if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                    print("err: {} {}".format(self.addr, e), file=stderr)
                self.updateState(WebSocketClientState.STATE_DONE)
            except BadFrame as e:
                if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                    print("err: {} {}".format(self.addr, e), file=stderr)
                self.updateState(WebSocketClientState.STATE_DONE)
            except UnicodeDecodeError:
                self._closeStatus = CloseFrameStatusCode.UNSUPPORTED_DATA
                self._closeReason = "cannot decode data as UTF-8"
                if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                    print("err: {} cannot decode data as UTF-8".format(
                        self.addr), file=stderr)
                self.updateState(WebSocketClientState.STATE_CLOSURE_INITIATED)
            except CloseFrameReceived as e:
                # Send back exactly the same close frame data
                self._closeStatus = e.status
                self._closeReason = e.reason
                self.updateState(WebSocketClientState.STATE_CLOSURE_REQUESTED)
            except socket.error as e:
                if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                    print("err: {} {}".format(self.addr, e), file=stderr)
                self.updateState(WebSocketClientState.STATE_DONE)
            try:
                # Call the trigger function on the received message
                self.server.handle(self, data)
            except socket.error as e:
                self.updateState(WebSocketClientState.STATE_DONE)
                break

        # Initiate the closing handshake
        if self._state == WebSocketClientState.STATE_CLOSURE_INITIATED:
            # The method itself is responsible for updating the thread's state
            self.initiateClosingHandShake(self._closeStatus, self._closeReason)
            self.sock.close()
        # The client sent a connection close frame
        elif self._state == WebSocketClientState.STATE_CLOSURE_REQUESTED:
            # Send the ack connection close frame
            self.sendClosingFrame(self._closeStatus, self._closeReason)
            # Don't wait for further communcation
            self.sock.close()
            self.updateState(WebSocketClientState.STATE_DONE)
        
        # Apply the server's common exit method on the thread
        if isinstance(self.server.exit, types.FunctionType):
            self.server.exit(self)
        
        self.stop()
    
    def updateState(self, state):
        """
        Rules the state machine transitions
        """
        old_state = self._state
        if self._state in self._valid_state_transition.keys() and \
                 state in self._valid_state_transition[self._state]:
            self._state = state
        else:
            raise ClientBadState('transition "{}"->"{}" forbidden'.format(
                WebSocketClientState.name[old_state],
                WebSocketClientState.name[state]
            ))
        if self.server.debug >= WebSocketDebugLevel.PRINT_INFO:
            print('info: client {} transition ("{}"->"{}")'.format(
                self.addr,
                WebSocketClientState.name[old_state],
                WebSocketClientState.name[state]
            ))
    
    def openingHandShake(self):
        """
        Shake with the client
        """
        self.updateState(WebSocketClientState.STATE_HANDSHAKING)
        
        data = self.sock.recv(4096)
        
        shake  = data.decode("utf-8")
        lines  = shake.split("\r\n")
        params = {}
        
        # The opening handshake is a valid HTTP/1.1 request
        # Extract the method, the request path and the version of the protocol
        tmp = lines[0].split(" ")
        if len(tmp) != 3 or tmp[0] != "GET" or tmp[2] != "HTTP/1.1":
            raise BadHandShake("received handshake is not HTTP/1.1 valid")
        params["method"]  = tmp[0]
        params["path"]    = tmp[1]
        params["version"] = tmp[2]
        
        #TODO use "path" info to enable multiple services with one instance
        
        # Extract regular HTTP fields
        for l in lines[1:]:
            if not l:
                continue
            # Extract the key and the value
            pos = l.find(": ")
            key = l[:pos].lower()
            value = l[pos+2:]
            if pos >= 0:
                params[key] = value
            else:
                raise BadHandShake("invalid header line \"{}\"".format(l))
        
        # Check host name correspondance
        if params["host"] != self.server.host and \
           params["host"] != self.server.host+":"+str(self.server.port):
            raise BadHandShake("bad host name requested")
        
        # Compute the response key
        accept = sha1()
        accept.update(bytes(params["sec-websocket-key"], "utf-8"))
        accept.update(bytes("258EAFA5-E914-47DA-95CA-C5AB0DC85B11", "utf-8"))
        
        # Handshake with a valid HTTP/1.1 response
        response = "HTTP/1.1 101 Switching Protocols\r\n"\
                   "Upgrade: websocket\r\n"\
                   "Connection: Upgrade\r\n"\
                   "Sec-WebSocket-Accept: {}\r\n"\
                   "\r\n".format(b64encode(accept.digest()).decode("utf-8"))
        
        self.sock.sendall(response.encode("utf-8"))
        
        self.updateState(WebSocketClientState.STATE_READY)

    def initiateClosingHandShake(self,
                                 status=CloseFrameStatusCode.NO_STATUS_RECVD,
                                 reason=""):
        """
        Initiate the closing handshake with the client:
          * Send a connection close frame to the client
          * Wait for the corresponding connection close frame _from_ the
            client
        Raise an exception if the client doesn't respond quickly enought so the
        caller can close the socket itself
        """
        self.sendClosingFrame()
        # Wait for client's acknowledgment
        self.updateState(WebSocketClientState.STATE_WAIT_CLOSURE_ACK)
        self.sock.settimeout(1.)
        try:
            #TODO None received since socket was shutdowned in RCV mode
            self.recv()
        except CloseFrameReceived:
            # Closing handshake successfull
            self.updateState(WebSocketClientState.STATE_WAIT_CLOSURE_ACK)
        except socket.timeout:
            if self.server.debug >= WebSocketDebugLevel.PRINT_ERROR:
                print("err: {} client sleeping".format(self.addr),
                    file=stderr)
            raise ClientSleeping
    
    def sendClosingFrame(self,
                         status=CloseFrameStatusCode.NO_STATUS_RECVD,
                         reason=""):
        """
        Send a close frame only if it was never sent before and if the
        connection allows it
        """
        data = pack("!H", status)
        if isinstance(reason, str):
            data += reason.encode("utf-8")
        f = frame(
            True,
            False, False, False,
            OperationCode.CONNECTION_CLOSE_FRAME,
            False,
            len(data),
            None,
            data
        )
        self.sock.sendall(bytes(f))
    
    def recv_frame(self):
        """
        Receive a frame and return it as it is
        """
        # Receive 2 bytes (static part)
        tmp = self.sock.recv(2)
        if len(tmp) != 2:
            raise IncompleteFrame("no data received")
        
        FIN    =    bool(tmp[0] & 0b10000000)
        RSV1   =    bool(tmp[0] & 0b01000000)
        RSV2   =    bool(tmp[0] & 0b00100000)
        RSV3   =    bool(tmp[0] & 0b00010000)
        Opcode =         tmp[0] & 0b00001111
        
        Mask   =    bool(tmp[1] & 0b10000000)
        Payload_length = tmp[1] & 0b01111111
        
        # Extended length (dynamic part)
        if Payload_length == 126:
            # Consider the next 2 bytes as an unsigned short
            tmp = self.sock.recv(2)
            if len(tmp) != 2:
                raise IncompleteFrame("2 bytes extended length")
            Payload_length = unpack("!H", tmp)[0]
        elif Payload_length == 127:
            # Consider the next 8 bytes as an unsigned long long
            tmp = self.sock.recv(8)
            if len(tmp) != 8:
                raise IncompleteFrame("8 bytes extended length")
            Payload_length = unpack("!Q", tmp)[0]
        # Receive the masking key (dynamic part)
        if Mask:
            Masking_key = self.sock.recv(4)
            if len(Masking_key) != 4:
                raise IncompleteFrame("4 bytes masking key")
        else:
            Masking_key = None
        # Receive the payload data (dynamic part)
        if Payload_length > 0:
            Payload_data = self.sock.recv(Payload_length)
            if len(Payload_data) != Payload_length:
                raise IncompleteFrame("{} bytes payload data".format(
                    Payload_length))
        else:
            Payload_data = None
        # Return a frame object
        return frame(FIN, RSV1, RSV2, RSV3, Opcode, Mask, Payload_length,
          Masking_key, Payload_data)
    
    def recv(self):
        """
        Return a message or None
        """
        # Ge the full message potentially from multiple frames
        while self._state == WebSocketClientState.STATE_READY:
            f = self.recv_frame()
            # The client is asking to close the WebSocket
            if f.Opcode == OperationCode.CONNECTION_CLOSE_FRAME:
                status, reason = f.extractData(f.Opcode)
                raise CloseFrameReceived(status, reason)
            # The frame is the last of a series
            if f.FIN:
                data = f.extractData(f.Opcode)
                # Build back the original message
                while self._frameStack:
                   f = self._frameStack.pop()
                   data = f.extractData(code) + data
                if self.server.debug >= WebSocketDebugLevel.PRINT_DATA:
                    print("info: {} recv \"{}\"".format(self.addr, data))
                return data
            # Push the frame on the stack until the final frame is received
            else:
                self._frameStack.append(f)
    
    def send(self, data):
        """
        Send a message
        """
        if self._state != WebSocketClientState.STATE_READY:
            raise ClientBadState("cannot send data in state \"{}\"".format(
                WebSocketClientState.name[self._state]
            ))
        if not data:
            return
        if self.server.debug >= WebSocketDebugLevel.PRINT_DATA:
            print('info: {} send "{}"'.format(self.addr, data))
        # Convert the message to bytes
        if isinstance(data, str):
            data = data.encode("utf-8")
            code = OperationCode.TEXT_FRAME
        else:
            code = OperationCode.BINARY_FRAME
        # Encapsulate data into a valid WebSocket frame
        f = frame(
            # TODO: implement fragmentation using /_maxDataSize/
            True,
            False, False, False,
            code,
            # No masking for server to client communication
            False,
            len(data),
            None,
            data
        )
        self.sock.sendall(bytes(f))
    
    def stop(self):
        """
        Last instructions to execute before exiting run()
        """
        self.server.remove(self)
    
    def info(self, msg):
        print("info: client ('{}', {}) {}".format(
            self.addr[0],
            self.addr[1],
            msg
        ))
    
    def error(self, msg):
        print("err: client ('{}', {}) {}".format(
            self.addr[0],
            self.addr[1],
            msg
        ), file=stderr)

class frame:
    """
    Represent a WebSocket frame
    """
    def __init__(self, FIN, RSV1, RSV2, RSV3, Opcode, Mask, Payload_length,
      Masking_key, Payload_data):
        self.FIN    = FIN
        self.RSV1   = RSV1
        self.RSV2   = RSV2
        self.RSV3   = RSV3
        self.Opcode = Opcode
        self.Mask   = Mask
        self.Payload_length = Payload_length
        self.Masking_key  = Masking_key
        self.Payload_data = Payload_data
    
    def getUnmaskedData(self):
        """
        RFC 6455/5.3 Client-to-Server Masking
        The masking does not affect the length of the "Payload data". To
        convert masked data into triggerMaskinged data, or vice versa, the
        following algorithm is applied. The same algorithm applies regardless of
        the direction of the translation, e.g., the same steps are applied to
        mask the data as to triggerMasking the data.
        """
        if self.Payload_data == None:
            raise DataMaskingError
        # We need a 4-bytes masking key
        if not self.Masking_key or not isinstance(self.Masking_key, bytes) \
          or len(self.Masking_key) != 4:
            raise DataMaskingError
        # Temporary array for swapping bytes
        tmp = [0 for i in range(self.Payload_length)]
        for i in range(self.Payload_length):
            tmp[i] = self.Payload_data[i] ^ self.Masking_key[i%4]
        # Return an unmasked copy of the payload data
        return bytes(tmp)
    
    def extractData(self, Opcode=None):
        """
        Return unmasked data
        If the frame contains text, return an utf-8 string
        If the frame is a close-connection one, return the code and the reason
        Else return a byte array
        """
        if Opcode == None:
            if self.Opcode == OperationCode.CONTINUATION_FRAME:
                raise TypeError("missing a valid Opcode")
            Opcode = self.Opcode
        # Unmasking
        if self.Mask and self.Payload_data != None:
            data = self.getUnmaskedData()
        else:
            data = self.Payload_data
        # Interpretation
        if self.Opcode == OperationCode.TEXT_FRAME:
            return data.decode("utf-8")
        elif self.Opcode == OperationCode.CONNECTION_CLOSE_FRAME:
            code, reason = (CloseFrameStatusCode.NO_STATUS_RECVD, "")
            # A code was given
            if self.Payload_length >= 2:
                code = unpack("!H", data[0:2])[0]
                # A reason was also given
                if self.Payload_length > 2:
                    try:
                        reason = data[2:].decode("utf-8")
                    except UnicodeDecodeError:
                        pass
            return code, reason
        elif self.Opcode == OperationCode.BINARY_FRAME:
            return data
        
    def __bytes__(self):
        """
        Render the object as bytes (as the RFC6455 specifies it)
        The returned byte array is ready to be pushed over TCP stream
        """
        # Check for maximum payload data length
        size = self.Payload_length if self.Payload_data else 0
        if size > (1<<64):
            raise MessageTooBig
        data = b""
        ## Byte #1
        # Final frame (static part)
        tmp  = int(self.FIN)  << 7
        # RSV1, 2 and 3 (static part)
        tmp += int(self.RSV1) << 6
        tmp += int(self.RSV2) << 5
        tmp += int(self.RSV3) << 4
        # Operation code (static part)
        tmp  += self.Opcode
        data += pack("!B", tmp)
        ## Byte #2
        # Mask bit (static part)
        tmp = int(self.Mask) << 7
        # Payload length (static part)
        Payload_length = size if size < 126     else \
                         126  if size < (1<<16) else \
                         127  if size < (1<<64) else 0
        tmp  += Payload_length
        data += pack("!B", tmp)
        ## Byte #3..
        # Extended payload length (dynamic part)
        if Payload_length == 126:
            # unsigned short (2 bytes)
            data += pack("!H", size)
        elif Payload_length == 127:
            # unsigned long long (8 bytes)
            data += pack("!Q", size)
        # Masking key (dynamic part)
        if self.Masking_key:
            data += self.Masking_key
        # Payload data (dynamic part)
        if self.Payload_data:
            data += self.Payload_data.encode("utf-8") \
                if isinstance(self.Payload_data, str) else self.Payload_data
        return data
    
    def __str__(self, humanReadable=False):
        """
        Render the frame as a string
        """
        if humanReadable:
            return "(FIN={}, RSV1={}, RSV2={}, RSV3={}, Opcode={} ({}), "\
                   "Mask={}, Payload_length={}, Masking_key={}, "\
                   "Payload_data=\"{}\")".format(
                self.FIN,
                self.RSV1,
                self.RSV2,
                self.RSV3,
                self.Opcode,
                OperationCode.name[self.Opcode],
                self.Mask,
                self.Payload_length,
                self.Masking_key,
                self.extractData(self.Opcode)
            )
        else:
            return "(FIN={}, RSV1={}, RSV2={}, RSV3={}, Opcode={}, "\
                   "Mask={}, Payload_length={}, Masking_key={}, "\
                   "Payload_data={})".format(
                self.FIN,
                self.RSV1,
                self.RSV2,
                self.RSV3,
                self.Opcode,
                self.Mask,
                self.Payload_length,
                self.Masking_key,
                self.Payload_data
            )
