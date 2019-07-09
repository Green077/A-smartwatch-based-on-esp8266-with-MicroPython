from machine import PWM
from machine import Pin
from machine import ADC
from machine import Timer
from machine import I2C
from machine import SPI
import machine
import time
import ssd1306
import network
import usocket as socket
import ujson
import ubinascii
import ussl
import gc
import ustruct
import mymodule

# initialize oled screen
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)
oled = ssd1306.SSD1306_I2C(128,32,i2c)

# start network interface
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# connect to CU Wifi network
if not wlan.isconnected():
	print('connecting to network...')
	wlan.connect('Columbia University')
	while not wlan.isconnected():
		pass
print('network config:', wlan.ifconfig())

# writes disp_string onto the display
def display(disp_string, mode):
	oled.fill(0x00)
	if mode == 0:
		oled.text(disp_string,0,0)
	else:
		for i in range(0, len(disp_string)):
			oled.text(disp_string[i], 0, i*11)
	oled.show()
		
# adjusts the brightness/contrast of the display
def sample_brightness():
	oled.contrast(int((adc.read()/4) - 1))

def my_clock(display_time):
	my_time.increment()
	if display_time:
		time = my_time.string()
		display(time,0)
	if alarm_time.hour == my_time.hour and alarm_time.minute == my_time.minute:
		display([my_time.string(), "ALARM"], 1)
		alarm_led.value(not alarm_led.value())
		if alarm_time.minute != my_time.minute:
			alarm_led.off()
			
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
	display(alarm_time.string(),0)
	time.sleep_ms(1000)
	
def Write_Data(Addr,DataW):
	Addr_b=ustruct.pack('B',Addr)
	Data_b=ustruct.pack('B',DataW)
	cs.off()
	spi.write(Addr_b)
	spi.write(Data_b)
	cs.on()	
	
def Read_Data(Address):
	Address = 0x80 | Address
	Addr_b = ustruct.pack('B',Address)
	cs.off()
	spi.write(Addr_b)
	Data_byt = spi.read(1)
	#Data = ustruct.unpack('B',Data_byt)
	cs.on()
	Data=ustruct.unpack('h',Data_byt)
	return Data

def Read_Data_16(Address):
	Address = Address | 0x80
	Address = Address | 0x40
	Addr_b = ustruct.pack('B',Address)
	cs.off()
	spi.write(Addr_b)
	Data_byt = spi.read(2)
	#Data = ustruct.unpack('B',Data_byt)
	cs.on()
	Data=ustruct.unpack('h',Data_byt)
	Data = int(Data[0])
	return Data
	
def sample_accel():
	x = []
	y = []
	z = []
	count = 0
	print('sampling...')
	while count < 20:
		count = count+1
		x.append(Read_Data_16(0x32))
		y.append(Read_Data_16(0x34))
		z.append(Read_Data_16(0x36))
		
		if count == 20:
			gesture_samples = '{"x": %s ,"y": %s , "z": %s }' % (str(x), str(y), str(z))
			print(gesture_samples)
			recv_buf = mymodule.http_request('34.215.0.88', 3001, 'POST', 'application/json', gesture_samples)
			#command, string = mymodule.parse_command(recv_buf)
			path = recv_buf.decode('utf-8')
			path = (path.replace("%20", " "))[2:]
			a_idx = path.find('&')
			return path[89:a_idx], 'Gesture: ' + path[a_idx+9:len(path)-1]
		else:
			time.sleep_ms(50)
	
# setup pins
alarm_led = Pin(0, Pin.OUT)
button_a = Pin(0, Pin.IN, Pin.PULL_UP)
button_b = Pin(13, Pin.IN, Pin.PULL_UP)
button_c = Pin(2, Pin.IN, Pin.PULL_UP)
adc = ADC(0)
	
# initialize timer
tim = Timer(-1)
tim2 = Timer(-1)	

# initalize accelerometer
spi = SPI(-1, baudrate=100000, polarity=1, phase=0, sck=Pin(14), mosi=Pin(15), miso=Pin(16))
spi.init(baudrate=100000) # set the baudrate
cs = machine.Pin(12,machine.Pin.OUT)
cs.on()

#Read_Data(0x00)
#Read_Data(0x2D)
#Read_Data(0x31)
#print(Read_Data(0x2C))
#print("The address is ", Read_Data(0x00))
Write_Data(0x31, 0x0F)
Write_Data(0x2D, 0x08)
#print(Read_Data(0x31))
#print(Read_Data(0x2D))
Write_Data(0x2E, 0x80)

my_time = mymodule.My_time(0,0,0)
alarm_time = mymodule.My_time(0,1,0)
display_time = True;
display_weather = False;
tweet = ''

tim.init(period = 100, mode=Timer.PERIODIC, callback=lambda t:sample_brightness())
tim2.init(period = 1000, mode=Timer.PERIODIC, callback=lambda t:my_clock(display_time))
button_a.irq(trigger=(Pin.IRQ_FALLING), handler = set_hour)
button_b.irq(trigger=(Pin.IRQ_FALLING), handler = set_minute)
button_c.irq(trigger=(Pin.IRQ_FALLING), handler = set_alarm)

# build and send location request
loc_request = mymodule.build_loc_request(wlan).decode('utf-8')
weather_list = mymodule.update_weather(loc_request)

# initialize server 
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
recv_buf = b''
status = 0

while True:
	print('awaiting connections...')
	cl, addr = s.accept()
	print('client connected from', addr)
	
	cl_file = cl.makefile('rwb', 0)
	recv_buf = cl_file.readline()
	while True:
		line = cl_file.readline()
		if not line or line == b'\r\n':
			break	
	command, string = mymodule.parse_command(recv_buf)
	
	print('Recieved: {"command": %s, "string": %s}' % (command, string))
	
	if command == 'show time':
		display_time = True
		display_weather = False
		status = 1
	elif command == 'show weather':
		display_time = False
		display_weather = True
		display(weather_list, 1)
		status = 1
	elif command == 'update weather':
		temp_time = display_time
		temp_weather = display_weather
		display_time = False
		display_weather = False
		display(['Updating','Weather','...'],1)
		
		# build and send location request
		loc_request = mymodule.build_loc_request(wlan).decode('utf-8')
		weather_list = mymodule.update_weather(loc_request)
		
		display_time = temp_time
		display_weather = temp_weather
		status = 1
	elif command == 'send signal':
		display_time = False
		display_weather = False
		display(['Sending','Gesture','...'],1)
		
		command, string = sample_accel()
		print(command + ' ' + string)
		
		if(command == 'show gesture'):
			display(string,0)
			status = 1
		else:
			status = 0
	elif command == 'send tweet':
		tweet = string
		
		temp_time = display_time
		temp_weather = display_weather
		display_time = False
		display_weather = False
		
		display('Sending Tweet...',0)
		mymodule.send_tweet(tweet)
		display('Success!', 0)
		time.sleep_ms(500)
		
		display_time = temp_time
		display_weather = temp_weather
		status = 1
	elif command == 'show tweet':
		display_time = False
		display_weather = False
		display(tweet,0)
	else:
		status = 0

	HTTP_HEADER = 'HTTP/1.1 %s \r\n' % ('200' if (status == 1) else '400')
	# build a response
	json_response = '{"command": %s,"status": %d}' % (command, status)
	response = '%sContent-Length:%d\r\nContent-Type:application/json\r\n\r\n%s' % (HTTP_HEADER, len(json_response), json_response)
	# send response and close socket
	cl.send(response)
	cl.close()
	
	print('Response: %s' % (json_response))