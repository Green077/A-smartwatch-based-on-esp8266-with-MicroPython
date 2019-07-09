from machine import PWM
from machine import Pin
from machine import ADC
from machine import Timer
from machine import I2C
from machine import RTC
import machine
import time
import ssd1306
import network
import usocket as socket
import ujson
import ubinascii
import ussl

class My_time(object):

	hour = 0;
	minute = 0;
	second = 0;
	
	def __init__(self, hour, minute, second):
		self.hour = hour
		self.minute = minute
		self.second = second		
	
	# increments the time
	def increment(self):
		# increment second
		self.second += 1
	
		# increment/reset other parameters
		if self.second == 60:
			self.second = 0
			self.minute += 1
			if self.minute == 60:
				self.minute = 0
				self.hour += 1
				if self.hour == 24:
					self.second = 0
					self.minute = 0
					self.hour = 0
	
	# returns a formatted string with the time
	def string(self):			
		# format string for display
		f_hour = str('{:02d}'.format(self.hour))
		f_minute = str('{:02d}'.format(self.minute))
		f_second = str('{:02d}'.format(self.second))
		time_string = f_hour + ':' + f_minute + ':' + f_second
		return time_string


# define commands for the ssd1306
DEACTIVATE_SCROLL = 0x2E
ACTIVATE_SCROLL = 0x2F
RIGHT_SCROLL = 0x26
LEFT_SCROLL = 0x27
DUMMY_BYTE_0 = 0x00
DUMMY_BYTE_F = 0xFF
PAGE_7 = 0x07
FRAMES_5 = 0x00
PAGE_0 = 0x00

# initialize timer
tim = Timer(-1)

# initialize oled screen
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)
oled = ssd1306.SSD1306_I2C(128,32,i2c)

# start network interface
wlan = network.WLAN(network.STA_IF)
wlan.active(True)	

# connect to CU Wifi network
# Taken from micropython documentation: 
# https://docs.micropython.org/en/latest/esp8266/esp8266/quickref.html#networking
def do_connect():
	if not wlan.isconnected():
		print('connecting to network...')
		wlan.connect('Columbia University')
		while not wlan.isconnected():
			pass
	print('network config:', wlan.ifconfig())

# extracts command parameters from url encoded string
def parse_command(recv_buf):
	recv_str = recv_buf.decode('utf-8')
	_, path, _= recv_str.split(' ', 3)
	path = path[2:]
	path = path.replace("%20", " ")
	a_idx = path.find('&')
	
	command = path[8:a_idx]
	string = path[a_idx+8:]

	return command, string
	
# writes disp_string onto the display
def display(disp_string):
	# erase framebuffer
	oled.fill(0x00)
	# add time string to frame buffer and display
	oled.text(disp_string,0,0)
	oled.show()
	
# increments the time and displays it
def update_time(display_time):
	state = machine.disable_irq()
	
	my_time.increment()
	if display_time:
		time = my_time.string()
		display(time)
	
	machine.enable_irq(state)
	
my_time = My_time(0,0,0)
display_time = False;

tim.init(period = 1000, mode=Timer.PERIODIC, callback=lambda t:update_time(display_time))
	
do_connect()

# initialize server 
# code modified from HTTP Server Example on:
# https://docs.micropython.org/en/latest/esp8266/esp8266/tutorial/network_tcp.html#simple-http-server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
recv_buf = b''
status = 0

while True:
	cl, addr = s.accept()
	print('client connected from', addr)
	cl_file = cl.makefile('rwb', 0)
	#save first line
	recv_buf = cl_file.readline()
	while True:
		line = cl_file.readline()
		if not line or line == b'\r\n':
			break
			
	# parse command arguments
	command, string = parse_command(recv_buf)
	print('Recieved: {"command": ' + command + ', "string": ' + string + '}')
	
	# test received command against available commands
	if command == 'turn on':
		display('HELLO!')
		time.sleep_ms(250)
		display_time = True
		status = 1
	elif command == 'turn off':
		display_time = False
		display('BYE BYE!')
		time.sleep_ms(250)
		display('')
		status = 1
	elif command == 'show time':
		display_time = True
		status = 1
	elif command == 'show string':
		display_time = False
		display(string)
		status = 1
	else:
		status = 0

	HTTP_HEADER = 'HTTP/1.1 ' + ('200' if (status == 1) else '400') + '\r\n'
	# build a response
	json_response = '{"command": ' + command + ',"status": ' + str(status) + '}'
	response = HTTP_HEADER + 'Content-Length:' + str(len(json_response)) + '\r\nContent-Type: application/json\r\n\r\n' + json_response
	
	# send response and close socket
	cl.send(response)
	cl.close()
	
	print('Response: ' + json_response)