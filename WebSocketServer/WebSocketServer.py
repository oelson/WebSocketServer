#-*- coding: utf-8 -*-
#
#	Copyright 2010 Houillon Nelson <houillon.nelson@gmail.com>
#
#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software
#	Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#	MA 02110-1301, USA.

import socket
import threading
from struct import pack
from hashlib import md5
from time import sleep
from string import digits
import sys

from .WebSocketException import *

def _int(s):
	buff = ""
	for c in s:
		if c in digits:
			buff += c
	return int(buff)

_handShakeStr = \
"HTTP/1.1 101 WebSocket Protocol Handshake\r\n" +\
"Upgrade: WebSocket\r\n"  +\
"Connection: Upgrade\r\n" +\
"Sec-WebSocket-Origin: {0}\r\n" +\
"Sec-WebSocket-Location: ws://{1}{2}\r\n\r\n"

def __void__(self):
	pass

class server(threading.Thread):
	"""
	Initialize a WebSocketServer server
	As a thread the server should be started
	using the server.start() method
	"""
	addr = None
	host = None
	port = -1
	running = True
	conn = None
	buffSize = 4096
	connexionTimeout = 1
	threadPool = []
	
	init   = None
	handle = None
	exit   = None
	
	debug = False
	
	def __init__(self, addr, host, port, handle, init=__void__, exit=__void__):
		self.addr = addr
		self.host = host
		self.port = port
		self.handle = handle
		self.init = init
		self.exit = exit
		threading.Thread.__init__(self)
	
	def run(self):
		"""
		Bind the socket to the wished address/port
		Serve forever clients
		"""
		self.conn = socket.socket()
		try:
			self.conn.bind((self.addr, self.port))
			self.conn.listen(1)
		except socket.error as e:
			print("err: cannot bind the socket to '{0}':{1} {2}".format(
					self.addr, self.port, e),
				file=sys.stderr)
			self.stop()
			return 1
		
		# Allows to check regulary if the server.stop() method fired
		self.conn.settimeout(self.connexionTimeout)
		
		if self.debug:
			print("info: server started")
		
		# Accept new clients until the server.stop() method fires
		while self.running:
			try:
				sock, addr = self.conn.accept()
			except socket.timeout:
				continue
			except socket.error:
				break
			if self.running:
				# Start a dedicated thread for each new client
				t = _WebSocketHandler(self, sock, addr)
				self.threadPool.append(t)
				t.start()
		# End While
		
		if self.debug:
			print("info: server stopped")
	
	def stop(self):
		"""
		Disconnect all clients and exit
		"""
		if self.running:
			self.running = False
			for thread in self.threadPool:
				if thread.is_alive() and thread.running:
					thread.stop()
					thread.join()
			self.conn.close()

class _WebSocketHandler(threading.Thread):
	"""
	Create a thread able to handle a WebSocket connection
	Take as arguments:
	  * A file descriptor representing the socket connected to the client
	  * An unique tuple (addr, ?) identifiying the connexion
	Public methods:
	  * utf8_string recv()
	  * void send(utf8_string)
	"""
	master = None
	sock = None
	addr = None
	running = False
	dataStack = []
	dataBuffer = b""
	
	def __init__(self, master, sock, addr):
		self.master = master
		self.sock = sock
		self.addr = addr
		threading.Thread.__init__(self)
	
	def run(self):
		"""
		Read the client's handShakeMsg and respond
		Read and write on the socket until the self.close() method fires
		"""
		self.running = True
		
		# Trigger the master's init function
		self.master.init(self)
		
		try:
			self._handshake()
		except WebSocketBadHandShake:
			self.stop()
			return 1
		except WebSocketBadHost:
			self.stop()
			return 2
		
		if self.master.debug:
			print("info: {0} connected".format(self.addr))
		
		# Receive/send forever
		while self.running:
			try:
				data = self.recv()
				self.master.handle(self, data)
			except WebSocketBadFrame:
				if self.master.debug:
					print("err: {0} bad frame".format(self.addr),
						file=sys.stderr)
				self.stop()
				break
			except (WebSocketClose, WebSocketBadClose):
				if self.master.debug:
					print("info: {0} disconnected".format(self.addr))
				self.stop()
				break
		# End While
		
		# Trigger the master's exit method
		self.master.exit(self)
		
		if self.master.debug:
			print("info: {0} thread terminated".format(self.addr))
	
	def _handshake(self):
		"""
		Shake with the client
		"""
		try:
			data = self.sock.recv(self.master.buffSize)
		except socket.error:
			raise WebSocketBadHandShake
		
		# Ignore last 8 non-utf8 random bytes
		shake = data[:-8].decode()
		dict = {}
		
		# Extract the method, the request path and the version of the protocol
		pos = shake.find("\r\n")
		tmp = shake[:pos].split(" ")
		dict["method"]  = tmp[0]
		dict["path"]    = tmp[1]
		dict["version"] = tmp[2]
		pos += 2
		
		# Parse each header line in order to store them in the dictionary
		# TODO reject malformed headers
		maxpos = shake.rfind("\r\n")
		while pos < maxpos:
			dot = shake.find(":", pos)
			name = shake[pos:dot].lower()
			pos = shake.find("\r\n", pos)
			dict[name] = shake[dot+2:pos]
			pos += 2
		
		# Check host name correspondance
		# TODO check the specification for what to do in such a case
		if dict["host"] != self.master.host and \
		   dict["host"] != self.master.host + ":" + str(self.master.port):
			raise WebSocketBadHost
				
		# Reject old versions of the protocol
		if not ("sec-websocket-key1" in dict and \
		        "sec-websocket-key2" in dict):
			raise WebSocketBadHandShake
		
		response = _handShakeStr.format(
			dict["origin"],
		    dict["host"],
		    dict["path"]
		)
		
		# Compute the challenge key
		# First key
		digits1  = _int(dict["sec-websocket-key1"])
		nbspace1 = dict["sec-websocket-key1"].count(" ")
		if nbspace1 == 0:
			raise WebSocketBadHandShake
		int1 = int(digits1 / nbspace1)
		# Second key
		digits2  = _int(dict["sec-websocket-key2"])
		nbspace2 = dict["sec-websocket-key2"].count(" ")
		if nbspace2 == 0:
			raise WebSocketBadHandShake
		int2 = int(digits2 / nbspace2)
		# Concatenate the two keys (2 * 32 bits) and the 8-bytes key found at
		# the end of the binary data
		# Hash the 2 * 64 = 128 bits object with md5
		h = md5()
		# Use usigned big-endian integers
		h.update(pack(">II", int1, int2))
		h.update(data[-8:])
		# Send the response as bytes
		md5sum = h.digest()
		response = response.encode() + md5sum
		try:
			self.sock.sendall(response)
		except socket.error:
			raise WebSocketBadHandShake
	
	def recv(self):
		"""
		Receive data from the client
		Return a utf-8 string
		Use a stack since multiple data frames may come in a single recv()
		"""
		if not self.running:
			return
		
		# Pop from the stack rather than receive data
		if len(self.dataStack) > 0:
			return self.dataStack.pop(0)
#		try:
		data = self.sock.recv(self.master.buffSize)
		if len(data) == 0:
			raise WebSocketBadClose
#		except socket.error as e:
#			if self.master.debug:
#				print("err: {0} {1} while receiving".format(
#					self.addr, e
#				), file=sys.stderr)
#			raise WebSocketClose
		
		size = len(data)
		returnData = None
		dataFrame  = False
		closeFrame = False
		pos = -1
		
		for i, byte in enumerate(data):
			if byte == 0x00:
				# \xff\x00 is a demand to close the socket
				if closeFrame:
					raise WebSocketClose
				elif not dataFrame:
					dataFrame = True
					pos = i+1
			elif byte == 0xff:
				# *data* frames start with \x00 and ends with \xff
				if dataFrame:
					str = data[pos:i].decode()
					if returnData is None:
						returnData = str
					else:
						self.dataStack.append(str)
					dataFrame = False
					i = -1
				elif not closeFrame:
					closeFrame = True
		# TODO if i != -1 there is some data in the buffer
		# ie: b"\x00a string witho"
		# \xFF may come on the next recv()
		# Appens when the string is greater than master.buffSize
		return returnData
	
	def send(self, s):
		"""
		Send a utf-8 string
		"""
		# *data* frames start with \x00 and ends with \xFF
		data = b"\x00" + s.encode() + b"\xFF"
#		try:
		self.sock.sendall(data)
#		except socket.error as e:
#			if self.master.debug:
#				print("err: {0} {1} while sending".format(
#					self.addr, e
#				), file=sys.stderr)
#			raise WebSocketBadClose
	
	def stop(self):
		"""
		Close the socket
		Ask the run() method to return
		Self-remove from master's pool
		"""
		if self.running:
			self.running = False
#			try:
#				self.sock.send(b"\xff\x00")
#			except socket.error:
#				pass
			self.sock.shutdown(socket.SHUT_RDWR)
			self.sock.close()
			if self.master.debug:
				print("info: {0} stopping".format(self.addr))
