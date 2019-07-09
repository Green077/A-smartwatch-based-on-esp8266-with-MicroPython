from machine import Pin
from machine import I2C
import ssd1306
import network
import usocket as socket
import ujson
import ubinascii
import ussl

LOC_API_KEY = 'AIzaSyCMS8vOlKEa_6AVp1t9OrKYpSZ6BjHth4Y'
location_url = 'https://www.googleapis.com/geolocation/v1/geolocate?key=' + LOC_API_KEY

WEATHER_API_KEY= 'c3cfeaf422a68d4920befec353396e21'
weather_url = 'http://api.openweathermap.org/data/2.5/weather'

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
	
# builds a json request
def build_loc_request():
    # formats mac address to a string
	mac = ubinascii.hexlify(wlan.config('mac'), ':').decode()
	ap_object = '{"macAddress": "' + (mac) + '"}'
	json_request = '{"considerIP": "true","wifiAccessPoints": [' + ap_object + ']}'
	return json_request
	
# send HTTP POST message, and parse response
# Modeled after http_get() function in micropython documentation:
# https://docs.micropython.org/en/latest/esp8266/esp8266/tutorial/network_tcp.html?highlight=http	
def http_request(url, port, cmd, content_type='', content=''):
	# get address information
	scheme, _, host, path= url.split('/',3)
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
		
	# parse response
	recv_buf = ''
	
	data = s.read(9)
	data = s.read(3)
	if data == b'200':
		data = b''
		record_buf = 0
		while True:
			data = s.read(1)
			# begin recording data into buffer at first '{'
			if data == b'{':
				record_buf += 1
			if record_buf > 0:
				recv_buf += data.decode('utf-8')
			# stop recording data at once all braces have closed
			if data == b'}':
				record_buf -= 1
				if record_buf == 0:
					break
	else:
		print('HTTP ERROR: ' + data.decode('utf-8'))
		data = s.read(512)
		print(data)
	s.close()
	return recv_buf
		
# returns a list of floats [lat, lng]
def parse_loc(json_str):
	json_obj = ujson.loads(json_str)
	lat = json_obj['location']['lat']
	lng = json_obj['location']['lng']
	loc = [lat, lng]
	return loc
		
def parse_weather(json_str):
	json_obj = ujson.loads(json_str)
	name = json_obj['name']
	temperature = json_obj['main']['temp']
	weather = json_obj['weather'][0]['main']
	weather_list = [name, str(temperature) + 'F', weather]
	return weather_list
	
# write list of strings onto the display
def display_list(disp_list):
	# erase framebuffer
	oled.fill(0x00)
	# add strings to frame buffer and display
	for i in range(0, len(disp_list)):
		oled.text(disp_list[i], 0, i*11)
	oled.show()

# connect to wifi network	
do_connect()

# build and send location request
loc_request = build_loc_request()
json_reply = http_request(location_url, 443, 'POST', 'application/json', loc_request)

# parse location
loc = parse_loc(json_reply)

# build GET request
weather_request = weather_url + '/?lat=' + str(loc[0]) + '&lon=' + str(loc[1]) + '&units=imperial' +'&appid=' + WEATHER_API_KEY
json_reply = http_request(weather_request, 80, 'GET')

# parse and display weather information
weather_list = parse_weather(json_reply)
print('Displaying Weather')
display_list(weather_list)