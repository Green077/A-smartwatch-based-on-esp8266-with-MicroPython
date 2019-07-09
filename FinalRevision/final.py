from machine import PWM
from machine import Pin
from machine import ADC
from machine import Timer
from machine import I2C
from machine import SPI
import machine
import time
import network
import usocket as socket
import ujson
import ubinascii
import ussl
import gc

class My_time(object):
	hour = 0
	minute = 0
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
		return '{:02d}:{:02d}:{:02d}'.format(self.hour,self.minute,self.second)

# extracts command parameters from url encoded string
def parse_command(recv_buf):
	_, path, _= (recv_buf.decode('utf-8')).split(' ', 3)
	path = (path.replace("%20", " "))[2:]
	a_idx = path.find('&')
	
	return path[8:a_idx], path[a_idx+8:]
			
# builds a json request
def build_loc_request(wlan):
    # formats mac address to a string
	mac = ubinascii.hexlify(wlan.config('mac'), ':').decode()
	return bytes('{"considerIP": "true","wifiAccessPoints": [{"macAddress": "%s"}]}' % (mac), 'utf-8')
	
# send HTTP POST message, and parse response
# Modeled after http_get() function in micropython documentation:
# https://docs.micropython.org/en/latest/esp8266/esp8266/tutorial/network_tcp.html?highlight=http	
def http_request(url, port, cmd, content_type='', content=''):
	# get address information
	try:
		scheme, _, host, path= url.split('/',3)
	except:
		host = url
		path = '.'
		scheme = 'http:'
		
	addr = socket.getaddrinfo(host, port)[0][-1]
	
	# create socket and connect to server
	s = socket.socket()
	s.connect(addr)
	print('Connected to: ' + host)
	
	# write commands for POST/GET
	if cmd is 'POST':
		# write POST message
		content_length = len(content)
		request_msg = bytes('POST /%s HTTP/1.1\r\nHost: %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n\r\n%s' % (path, host, content_type, content_length, content), 'utf-8')
	elif cmd is 'GET':
		# write GET message
		request_msg = bytes('GET /%s HTTP/1.1\r\nHost: %s\r\n\r\n' % (path, host), 'utf-8')
		
	# to wrap socket in ssl or not
	if "https" in scheme:
		# enable ssl
		s = ussl.wrap_socket(s)
		s.write(request_msg)
	else:
		s.send(request_msg)
		
	recv_buf = b''
	record_buf = 0
	while True:
		data = s.read(1)
		recv_buf += data
		# keep track of {} if response contains a json object
		if data == b'{':
			record_buf += 1
		if data == b'}':
			record_buf -= 1
			if record_buf == 0:
				break
		# otherwise stop reading once there are no more bytes to read
		if data == b'':
			break
	print(recv_buf)
	s.close()
	return recv_buf

# extract json object from received bytes
def parse_json(recv_buf):
	recv_str = recv_buf.decode('utf-8')
	start_idx = recv_str.find('{')
	end_idx = recv_str.rfind('}')
	return ujson.loads(recv_str[start_idx:end_idx])

# extract response from receieved bytes
def parse_response(recv_buf):
	recv_str = recv_buf.decode('utf-8')
	start_idx = recv_str.find('\r\n\r\n') + 4
	end_idx = len(recv_str)
	return recv_str[start_idx:end_idx]

# returns a list of floats [lat, lng]
def parse_loc(json_obj):
	return [json_obj['location']['lat'], json_obj['location']['lng']]
	
# extract a list of weather parameters from json object	
def parse_weather(json_obj):
	return [json_obj['name'], ('%d F' % (json_obj['main']['temp'])), json_obj['weather'][0]['main']]

# update weather display
def update_weather(loc_request):
	# parse location
	loc = parse_loc(parse_json(http_request('https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyCMS8vOlKEa_6AVp1t9OrKYpSZ6BjHth4Y', 443, 'POST', 'application/json', loc_request)))
	# build GET request
	weather_request = 'http://api.openweathermap.org/data/2.5/weather/?lat=' + str(loc[0]) + '&lon=' + str(loc[1]) +'&units=imperial&appid=c3cfeaf422a68d4920befec353396e21'
	recv_buf = http_request(weather_request, 80, 'GET')
	# parse and display weather information
	return parse_weather(parse_json(recv_buf))

# tweet the weather!
def send_tweet(status):
	tweet = status.replace(" ", "%20")
	recv_buf = http_request('https://api.thingspeak.com/apps/thingtweet/1/statuses/update', 443, 'POST', 'application/x-www-form-urlencoded', ('api_key=XF35PKTWALJJRDU7&status=' + tweet))
	response = parse_response(recv_buf)
	if response == '1':
		print('Successfully Tweeted: "%s"' % (status))
		return 1
	else:
		print('Error: %s' % (response))
		return 0

# adjusts the hour
def set_hour(a):
	my_time.second = 0		
	my_time.hour += 1		
	if my_time.hour == 24:
		my_time.hour = 0
	
# adjusts the minute
def set_minute(b):
	my_time.second = 0	
	my_time.minute += 1
	if my_time.minute == 60:
		my_time.minute = 0	

def set_alarm(c):
		print('UPDATE ALARM BY 30 MINUTE')
		# increment alarm minute by 30 minute each time
		alarm_time.minute += 30
		if alarm_time.minute >= 60:
			alarm_time.minute -= 60
			alarm_time.hour += 1
			if alarm_time.hour == 24:
				alarm_time.hour = 0
		time.sleep_ms(1000)
