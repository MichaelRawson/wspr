from tornado.ioloop import IOLoop as IO

import socket
from subprocess import check_output, run as invoke_process
from threading import Thread

import serial
# from serial import Serial
from fake_serial import Serial
from wire_format import for_wire, from_wire

class Hardware:
	def __init__(self, state):
		self.state = state
		self.serial = Serial(
			port='/dev/ttyAMA0',
			baudrate=115200,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS
		)
		self.handlers = {
			'H': self.handle_hostname,
			'I': self.handle_ip,
			'C': self.handle_callsign,
			'L': self.handle_locator,
			'P': self.handle_power,
			'B': self.handle_bandhop,
			'F': self.handle_frequency,
			'X': self.handle_tx_percentage,
			'S': self.handle_status,
			'T': self.handle_timestamp
		}

		# populate hostname and IP for the frontend
		self.handle_hostname(None)
		self.handle_ip(None)

	def handle_hostname(self, data):
		hostname = socket.gethostname()
		self.state.set_from_hardware('hostname', hostname)
		return ('H', hostname)

	def handle_ip(self, data):
		ip = check_output(['hostname' , '-I'])\
			.decode('ascii')\
			.strip()
		self.state.set_from_hardware('ip', ip)
		return ('I', ip)

	def handle_callsign(self, data):
		self.state.set_from_hardware('callsign', data)

	def handle_locator(self, data):
		self.state.set_from_hardware('locator', data)

	def handle_power(self, data):
		self.state.set_from_hardware('power', int(data))

	def handle_bandhop(self, data):
		self.state.set_from_hardware('bandhop', data.split(','))

	def handle_frequency(self, data):
		self.state.set_from_hardware('frequency', int(data))

	def handle_tx_percentage(self, data):
		self.state.set_from_hardware('tx_percentage', int(data))

	def handle_status(self, data):
		self.state.set_from_hardware('status', data)

	def handle_timestamp(self, data):
		invoke_process(['date', '+%T', '-s', data])

	def route_command(self, data):
		command, rest = from_wire(data)
		handler = None
		try:
			handler = self.handlers[command]
		except KeyError:
			raise NotImplementedException("no handler for {}".format(command))

		returned = handler(rest)
		if returned is None:
			return

		response = for_wire(*returned)
		self.serial.write(response)
		
	def poll_serial(self):
		while True:
			data = self.serial.readline()
			IO.current().add_callback(self.route_command, data)

	def go(self):
		target = self.poll_serial
		Thread(target=target).start()
