from machine import PWM
from machine import Pin
from machine import ADC
from machine import Timer
from machine import I2C
from machine import RTC
from machine import SPI
import machine
import time
import ssd1306

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

# setup pins
button_a = Pin(12, Pin.IN, Pin.PULL_UP)
button_b = Pin(13, Pin.IN, Pin.PULL_UP)
button_c = Pin(14, Pin.IN, Pin.PULL_UP)
adc = ADC(0)
alarm_led= Pin(2, Pin.OUT)

# initalize timers
tim = Timer(-1)
tim2 = Timer(-1)
tim3 = Timer(-1)
tim4 = Timer(-1)
rtc = machine.RTC()

# initialize oled screen
i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)
oled = ssd1306.SSD1306_I2C(128,32,i2c)
alarm_led.value(not alarm_led.value())

#initialize adxl345
spi = machine.SPI(baudrate=100000, polarity=0, phase=0, sck=machine.Pin(16), mosi=machine.Pin(0), miso=machine.Pin(15))
cs = machine.Pin(2,machine.Pin.OUT)

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

# writes disp_string onto the display
def display(disp_string):
	# erase framebuffer
	oled.fill(0x00)
	# add time string to frame buffer and display
	oled.text(disp_string,0,0)
  #  if alarm_flag == True:
    #    oled.text("alarming",0,10)
	oled.show()

# adjusts the brightness/contrast of the display
def sample_brightness():
	val = adc.read()
	# map ADC values to 0-256
	val = int((val/4) - 1)
	# dim the OLED as it gets brighter
	oled.contrast(val)

# scroll_left/right use hardware scrolling available on ssd1306
def scroll_left():
	# deactivate scroll
	oled.write_cmd(DEACTIVATE_SCROLL)
	# set left scroll
	oled.write_cmd(LEFT_SCROLL)
	# dummy byte
	oled.write_cmd(DUMMY_BYTE_0)
	# start page address
	oled.write_cmd(PAGE_0)
	# define number of frames
	oled.write_cmd(FRAMES_5)
	# end page address
	oled.write_cmd(PAGE_7)
	oled.write_cmd(DUMMY_BYTE_0)
	oled.write_cmd(DUMMY_BYTE_F)
	# activate scroll
	oled.write_cmd(ACTIVATE_SCROLL)

def scroll_right():
	# deactivate scroll
	oled.write_cmd(DEACTIVATE_SCROLL)
	#set right scroll
	oled.write_cmd(RIGHT_SCROLL)
	# dummy byte
	oled.write_cmd(DUMMY_BYTE_0)
	# start page address
	oled.write_cmd(PAGE_7)
	# define number of frames
	oled.write_cmd(FRAMES_5)
	# end page address
	oled.write_cmd(PAGE_0)
	oled.write_cmd(DUMMY_BYTE_0)
	oled.write_cmd(DUMMY_BYTE_F)
	# activate scroll
	oled.write_cmd(ACTIVATE_SCROLL)

# scroll_up/down adjust the display start line
def scroll_up():
	# deactivate scroll
	oled.write_cmd(DEACTIVATE_SCROLL)

	i = 64
	while True:
		time.sleep_ms(50)
		# reset display start line
		oled.write_cmd(i)
		i += 1
		if i == 127:
			i = 64

def scroll_down():
	# deactivate scroll
	oled.write_cmd(DEACTIVATE_SCROLL)

	i = 127
	while True:
		time.sleep_ms(50)
		# reset display start line
		oled.write_cmd(i)
		i -= 1
		if i == 64:
			i = 127

# increments the time and displays it
def update_time(my_time):
	state = machine.disable_irq()

	my_time.increment()
	time = my_time.string()
	display(time)

	machine.enable_irq(state)

# adjusts the hour
def set_hour(a):
	state = machine.disable_irq()
	print('INTERRUPT_hour')
	switch_state = button_a.value()
	#delay
	time.sleep_ms(20)
	#if the button has the same value (has finished bouncing), continue
	if button_a.value() == switch_state:
		if(not switch_state):
			print('UPDATE HOUR')
			# set second to 0
			my_time.second = 0
			# increment hour
			my_time.hour += 1
			if my_time.hour == 24:
				my_time.hour = 0
			display(my_time.string())

	else:
		print('BOUNCE')
	machine.enable_irq(state)

# adjusts the minute
def set_minute(b):
	state = machine.disable_irq()
	print('INTERRUPT_minute')
	switch_state = button_b.value()
	#delay
	time.sleep_ms(20)
	#if the button has the same value (has finished bouncing), continue
	if button_b.value() == switch_state:
		if(not switch_state):
			print('UPDATE MINUTE')
			# set second to 0
			my_time.second = 0
			# increment hour
			my_time.minute += 1
			if my_time.minute == 60:
				my_time.minute = 0
			display(my_time.string())

	else:
		print('BOUNCE')
	machine.enable_irq(state)

def set_alarm(c):
	state = machine.disable_irq()
	print('INTERRUPT_alarm')
	switch_state = button_c.value()
	#delay
	time.sleep_ms(20)
	#if the button has the same value (has finished bouncing), continue
	if button_c.value() == switch_state:
		if(not switch_state):
			print('UPDATE ALARM BY 30 MINUTE')
			# increment alarm minute by 30 minute each time
			alarm_time.minute += 30
			if alarm_time.minute >= 60:
				alarm_time.minute -= 60
				alarm_time.hour += 1
				if alarm_time.hour == 24:
					alarm_time.hour = 0
			display(alarm_time.string())
			time.sleep_ms(1000)
	else:
		print('BOUNCE')
	machine.enable_irq(state)

def show_alarm():
    if alarm_time.hour == my_time.hour and alarm_time.minute == my_time.minute:
        #alarm_flag = True
		oled.text(my_time.string(),0,0)
		oled.text("alarming",0,10)
		oled.show()
		alarm_led.value(not alarm_led.value())
		if alarm_time.minute != my_time.minute:
			alarm_led.off()

			
#Detect the accelormeter and scroll
def scroll_olde():
	direction = Direction_cal()
	if direction == 1:
		scroll_right()
	elif direction == 2:
		scroll_left()
	elif direction == 3:
		scroll_up()
	elif direction == 4:
		scroll_down()
	else:

#Connect with adxl345
#Write data to register to set mode
def Write_Data(Addr,DataW):
	Addr_b=ustruct.pack('B',Addr)
	Data_b=ustruct.pack('B',DataW)
	cs.off()
	spi.write(Addr_b)
	spi.write(Data_b)
	cs.on()
	
#Read from certain register
def Read_Data(Address):
	Address = 0x80 | Address
	Addr_b = ustruct.pack('B',Address)
	cs.off()
	spi.write(Addr_b)
	Data_byt = spi.read(1)
	cs.on()
	Data=ustruct.unpack('H',Data_byt)
	return Data
	
#Read 16bits data from x,y,z
def Read_Data_16(Address):
	Address = Address | 0x80
	Address = Address | 0x40
	Addr_b = ustruct.pack('B',Address)
	cs.off()
	spi.write(Addr_b)
	Data_byt = spi.read(2)
	#Data = ustruct.unpack('B',Data_byt)
	cs.on()
	Data=ustruct.unpack('H',Data_byt)
	return Data

#Calculate the direction of adxl345
def Direction_cal():
	Angle_xz=atan(Read_Data_16(0x32)/Read_Data_16(0x36))
	Angle_yz=atan(Read_Data_16(0x34)/Read_Data_16(0x36))
	#Angle of x,y,z direction
	if Angle_xz > math.pi/4:
		print ('SCROLL to +x')
		return 1
	elif Angle_xz < -math.pi/4:
		print ('SCROLL to -x')
		return 2
	elif Angle_yz > math.pi/4:
		print ('SCROLL to +y')
		return 3
	elif Angle_yz < -math.pi/4:
		print ('SCROLL to -y')
		return 4
	else return 0
	
#alarm_flag = False
my_time = My_time(0,0,0)
alarm_time = My_time(0,1,0)
tim.init(period = 100, mode=Timer.PERIODIC, callback=lambda t:sample_brightness())
tim2.init(period = 1000, mode=Timer.PERIODIC, callback=lambda t:update_time(my_time))
tim3.init(period = 1000, mode=Timer.PERIODIC, callback=lambda t:show_alarm())
tim4.init(period = 100, mode=Timer.PERIODIC, callback=lambda t:scroll_oled())
button_a.irq(trigger=(Pin.IRQ_FALLING), handler = set_hour)
button_b.irq(trigger=(Pin.IRQ_FALLING), handler = set_minute)
button_c.irq(trigger=(Pin.IRQ_FALLING), handler = set_alarm)

