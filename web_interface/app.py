#############################################
# Robot Webinterface - Python Script
# Simon Bluett, https://wired.chillibasket.com
# V1.4, 16th February 2020
#############################################

from flask import Flask, request, session, redirect, url_for, jsonify, render_template
import queue 		# for serial command queue
import threading 	# for multiple threads
import os
import pygame		# for sound
import serial 		# for Arduino serial access
import serial.tools.list_ports
import subprocess 	# for shell commands


#--------------Driver Library-----------------#
import RPi.GPIO as GPIO
import OLED_Driver as OLED
#--------------Image Library---------------#
from PIL  import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageColor
#-------------Test Display Functions---------------#
import sys
import cv2
import numpy as np
import time

import gtts


import getopt
import scipy.io.wavfile as wavfile
import math
import sys
import pydub 
from waveshaper import Waveshaper

app = Flask(__name__)


##### VARIABLES WHICH YOU CAN MODIFY #####
loginPassword = "12345"                                  # Password for web-interface
arduinoPort = "ARDUINO"                                              # Default port which will be selected
streamScript = "/home/pi/mjpg-streamer.sh"                           # Location of script used to start/stop video stream
soundFolder = "/home/pi/walle-replica/web_interface/static/sounds/"  # Location of the folder containing all audio files
oledFolder = "/home/pi/walle-replica/web_interface/oled/"  # Location of the folder containing all audio files
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)      # Secret key used for login session cookies


#-------------OLED-----------------#
WIDTH = 128
HEIGHT = 128 # Change to 32 depending on your screen resolution
##########################################



#------------ Constants for robot VOICE-----------------#
# Diode constants (must be below 1; paper uses 0.2 and 0.4)
VB = 0.01
VL = 0.02
# Controls distortion
H = 1
# Controls N samples in lookup table; probably leave this alone
LOOKUP_SAMPLES = 1024
# Frequency (in Hz) of modulating frequency
MOD_F = 50


# Start sound mixer
pygame.mixer.init()

# Set up runtime variables and queues
exitFlag = 0
arduinoActive = 0
streaming = 0
volume = 5
batteryLevel = -999
queueLock = threading.Lock()
workQueue = queue.Queue()
threads = []
videothreads = []
videoFlag = 0
stopVideo = 0
#############################################
# Set up the multithreading stuff here
#############################################
# The second thread will be used to send data to the Arduino
class arduino (threading.Thread):
	def __init__(self, threadID, name, q, port):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		self.q = q
		self.port = port
	def run(self):
		print("Starting Arduino Thread", self.name)
		process_data(self.name, self.q, self.port)
		print("Exiting Arduino Thread", self.name)

# Function to send data to the Arduino from a buffer queue
def process_data(threadName, q, port):
	global exitFlag
	
	ser = serial.Serial(port,115200)
	ser.flushInput()
	dataString = ""
	while not exitFlag:
		try:
			queueLock.acquire()
			if not workQueue.empty():
				data = q.get() + '\n'
				queueLock.release()
				ser.write(data.encode())
				print(data)
			else:
				queueLock.release()
			if (ser.inWaiting() > 0):
				data = ser.read()
				if (data.decode() == '\n' or data.decode() == '\r'):
					print(dataString)
					parseArduinoMessage(dataString)
					dataString = ""
				else:
					dataString += data.decode()
			if (videoFlag == 1):
				print("A video is already active,sleeping queue")
				time.sleep(0.100)
		# If an error occured in the Arduino Communication
		except Exception as e: 
			print(e)
			exitFlag = 1
	ser.close()

# Function to parse messages received from the Arduino
def parseArduinoMessage(dataString):
	global batteryLevel
	
	# Battery level message
	if "Battery" in dataString:
		dataList = dataString.split('_')
		
		print("len(dataList)=" + str(len(dataList)) )
		try:
			int(dataList[1])
			is_dig = True
		except ValueError:
			is_dig = False

		if len(dataList) > 1 and is_dig:
			batteryLevel = dataList[1]
			DisplayBatteryLevel();

# Turn on/off the Arduino Thread system
def onoff_arduino(q, portNum):
	global arduinoActive
	global exitFlag
	global threads
	global batteryLevel
	
	if not arduinoActive:
		# Set up thread and connect to Arduino
		exitFlag = 0

		usb_ports = [
			p.device
			for p in serial.tools.list_ports.comports()
		]
		
		thread = arduino(1, "Arduino", q, usb_ports[portNum])
		thread.start()
		threads.append(thread)

		arduinoActive = 1

	else:
		# Disconnect Arduino and exit thread
		exitFlag = 1
		batteryLevel = -999

		# Clear the queue
		queueLock.acquire()
		while not workQueue.empty():
			q.get()
		queueLock.release()

		# Join any active threads up
		for t in threads:
			t.join()

		threads = []
		arduinoActive = 0

	return 0


# Test whether the Arduino connection is still active
def test_arduino():
	global arduinoActive
	global exitFlag
	global workQueue
	
	if arduinoActive and not exitFlag:
		return 1
	elif exitFlag and arduinoActive:
		onoff_arduino(workQueue, 0)
	else:
		return 0


# Turn on/off the MJPG Streamer
def onoff_streamer():
	global streaming
	
	if not streaming:
		# Turn on stream
		subprocess.call([streamScript, 'start'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
		result = ""
		# Check whether the stream is on or not
		try:
			result = subprocess.run([streamScript, 'status'], stdout=subprocess.PIPE).stdout.decode('utf-8')
		except subprocess.CalledProcessError as e:
			result = e.output.decode('utf-8')
		print(result)
		
		if 'stopped' in result:
			streaming = 0
			return 1
		else:
			streaming = 1
			return 0

	else:
		# Turn off stream
		subprocess.call([streamScript, 'stop'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
		
		streaming = 0
		return 0


#############################################
# Flask Pages and Functions
#############################################

# Main Page
@app.route('/')
def index():
	if session.get('active') != True:
		return redirect(url_for('login'))

	# Get list of audio files
	files = []
	for item in sorted(os.listdir(soundFolder)):
		if item.endswith(".ogg"):
			audiofiles = os.path.splitext(os.path.basename(item))[0]
			
			# Set up default details
			audiogroup = "Other"
			audionames = audiofiles;
			audiotimes = 0;
			
			# Get item details from name, and make sure they are valid
			if len(audiofiles.split('_')) == 2:
				if audiofiles.split('_')[1].isdigit():
					audionames = audiofiles.split('_')[0]
					audiotimes = float(audiofiles.split('_')[1])/1000.0
				else:
					audiogroup = audiofiles.split('_')[0]
					audionames = audiofiles.split('_')[1]
			elif len(audiofiles.split('_')) == 3:
				audiogroup = audiofiles.split('_')[0]
				audionames = audiofiles.split('_')[1]
				if audiofiles.split('_')[2].isdigit():
					audiotimes = float(audiofiles.split('_')[2])/1000.0
			
			# Add the details to the list
			files.append((audiogroup,audiofiles,audionames,audiotimes))
	
	# Get list of connected USB devices
	ports = serial.tools.list_ports.comports()
	usb_ports = [
		p.description
		for p in serial.tools.list_ports.comports()
		#if 'ttyACM0' in p.description
	]
	
	# Ensure that the preferred Arduino port is selected by default
	selectedPort = 0
	for index, item in enumerate(usb_ports):
		if arduinoPort in item:
			selectedPort = index
	
	return render_template('index.html',sounds=files,ports=usb_ports,portSelect=selectedPort,connected=arduinoActive)

# Login
@app.route('/login')
def login():
	if session.get('active') == True:
		return redirect(url_for('index'))
	else:
		return render_template('login.html')

# Login Request
@app.route('/login_request', methods = ['POST'])
def login_request():
	password = request.form.get('password')
	if password == loginPassword:
		session['active'] = True
		return redirect(url_for('index'))
	return redirect(url_for('login'))

# Motor Control
@app.route('/motor', methods=['POST'])
def motor():
	if session.get('active') != True:
		return redirect(url_for('login'))

	stickX =  request.form.get('stickX')
	stickY =  request.form.get('stickY')
	if stickX is not None and stickY is not None:
		#I need to reverse X
		xVal = int( - float(stickX)*100)
		yVal = int(float(stickY)*100)
		print("Motors:", xVal, ",", yVal)
		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put("X" + str(xVal))
			workQueue.put("Y" + str(yVal))
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Arduino not connected'})
	else:
		print("Error: unable to read POST data from motor command")
		return jsonify({'status': 'Error','msg':'Unable to read POST data'})

# Update Settings
@app.route('/settings', methods=['POST'])
def settings():
	if session.get('active') != True:
		return redirect(url_for('login'))

	thing = request.form.get('type');
	value = request.form.get('value');

	if thing is not None and value is not None:
		if thing == "motorOff":
			print("Motor Offset:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("O" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Arduino not connected'})
		elif thing == "steerOff":
			print("Steering Offset:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("S" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Arduino not connected'})
		elif thing == "animeMode":
			print("Animation Mode:", value)
			if test_arduino() == 1:
				queueLock.acquire()
				workQueue.put("M" + value)
				queueLock.release()
			else:
				return jsonify({'status': 'Error','msg':'Arduino not connected'})
		elif thing == "soundMode":
			print("Sound Mode:", value)
		elif thing == "volume":
			global volume
			volume = int(value)
			print("Change Volume:", value)
		elif thing == "streamer":
			print("Turning on/off MJPG Streamer:", value)
			if onoff_streamer() == 1:
				return jsonify({'status': 'Error', 'msg': 'Unable to start the stream'})

			if streaming == 1:
				return jsonify({'status': 'OK','streamer': 'Active'})
			else:
				return jsonify({'status': 'OK','streamer': 'Offline'})
		elif thing == "shutdown":
			print("Shutting down Raspberry Pi!", value)
			result = subprocess.run(['sudo','nohup','shutdown','-h','now'], stdout=subprocess.PIPE).stdout.decode('utf-8')
			return jsonify({'status': 'OK','msg': 'Raspberry Pi is shutting down'})
		else:
			return jsonify({'status': 'Error','msg': 'Unable to read POST data'})

		return jsonify({'status': 'OK' })
	else:
		return jsonify({'status': 'Error','msg': 'Unable to read POST data'})

# Play Audio
@app.route('/audio', methods=['POST'])
def audio():
	if session.get('active') != True:
		return redirect(url_for('login'))

	clip =  request.form.get('clip')
	if clip is not None:
		clip = soundFolder + clip + ".ogg"
		print("Play music clip:", clip)
		pygame.mixer.music.load(clip)
		pygame.mixer.music.set_volume(volume/10.0)
		#start_time = time.time()
		pygame.mixer.music.play()
		#while pygame.mixer.music.get_busy() == True:
		#	continue
		#elapsed_time = time.time() - start_time
		#print(elapsed_time)
		return jsonify({'status': 'OK' })
	else:
		return jsonify({'status': 'Error','msg':'Unable to read POST data'})


def playsoundclip(clipname):
	if clipname is not None:
		clip = soundFolder + clipname
		print("Play music clip:", clip)
		pygame.mixer.music.load(clip)
		pygame.mixer.music.set_volume(volume/10.0)
		#start_time = time.time()
		pygame.mixer.music.play()


# Play TTS
@app.route('/tts', methods=['POST'])
def tts():
	if session.get('active') != True:
		return redirect(url_for('login'))

	lng =  request.form.get('lang')
	txt =  request.form.get('txt')
	if txt is not None:		
		robotvoice(lng, txt)
		return jsonify({'status': 'OK' })
	else:
		return jsonify({'status': 'Error','msg':'Unable to read POST data'})
	
# Animate
@app.route('/animate', methods=['POST'])
def animate():
	if session.get('active') != True:
		return redirect(url_for('login'))

	clip = request.form.get('clip')
	if clip is not None:
		print("Animate:", clip)
		if ( clip == '3'):			
			#PlayMovie('BandL')
			thread = videoPlayer(1, "BandL")
			thread.start()
			videothreads.append(thread)
		if ( clip == '4'):	
			#PlayMovie('PutOnYourSundayClothes')
			thread = videoPlayer(1, "PutOnYourSundayClothes")
			thread.start()
			videothreads.append(thread)	
			clip = "30"
		if ( clip == '5'):	
			#PlayMovie('LaVieenRose')
			thread = videoPlayer(1, "LaVieenRose")
			thread.start()
			videothreads.append(thread)	
			clip = "30"
		if ( clip == '6'):	
			#PlayMovie('DowntoEarth')
			thread = videoPlayer(1, "DowntoEarth")
			thread.start()
			videothreads.append(thread)	
			clip = "30"
		if ( clip == '7'):	
			#PlayMovie('WALL-E-Trailer')
			thread = videoPlayer(1, "WALL-E-Trailer")
			thread.start()
			videothreads.append(thread)
		if ( clip == '8'):	
			#PlayMovie('WALL-E-TrailerGR')
			thread = videoPlayer(1, "WALL-E-TrailerGR")
			thread.start()
			videothreads.append(thread)
		if ( clip == '9'):	
			#PlayMovie('WALL-EVignettes')
			thread = videoPlayer(1, "WALL-EVignettes")
			thread.start()
			videothreads.append(thread)
		if ( clip == '10'):	
			#PlayMovie('WALL-E-Ending')
			thread = videoPlayer(1, "WALL-E-Ending")
			thread.start()
			videothreads.append(thread)
		if ( clip == '11'):	
			#PlayMovie('WallEMeetsEve')
			thread = videoPlayer(1, "WallEMeetsEve")
			thread.start()
			videothreads.append(thread)
		if ( clip == '40'):	
			playsoundclip("GR_Hug.ogg")	
		if ( clip == '51'):	
			playsoundclip("GR_ImSad.ogg")	
		if ( clip == '52'):	
			playsoundclip("GR_ImHappy.ogg")	
			clip = "40"
		if ( clip == '60'):	
			playsoundclip("GR_LookThere.ogg")	
		if ( clip == '70'):	
			playsoundclip("GR_StelioWhereareYou.ogg")	
			
		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put("A" + clip)
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Arduino not connected'})
	else:
		return jsonify({'status': 'Error','msg':'Unable to read POST data'})
		
# Servo Control
@app.route('/servoControl', methods=['POST'])
def servoControl():
	if session.get('active') != True:
		return redirect(url_for('login'))

	servo = request.form.get('servo');
	value = request.form.get('value');
	if servo is not None and value is not None:
		print("servo:", servo)
		print("value:", value)
		
		if test_arduino() == 1:
			queueLock.acquire()
			workQueue.put(servo + value)
			queueLock.release()
			return jsonify({'status': 'OK' })
		else:
			return jsonify({'status': 'Error','msg':'Arduino not connected'})
	else:
		return jsonify({'status': 'Error','msg':'Unable to read POST data'})

# Arduino Connection
@app.route('/arduinoConnect', methods=['POST'])
def arduinoConnect():
	if session.get('active') != True:
		return redirect(url_for('login'))
		
	action = request.form.get('action');
	
	if action is not None:
		# Update drop-down selection with list of connected USB devices
		if action == "updateList":
			print("Reload list of connected USB ports")
			
			# Get list of connected USB devices
			ports = serial.tools.list_ports.comports()
			usb_ports = [
				p.description
				for p in serial.tools.list_ports.comports()
				#if 'ttyACM0' in p.description
			]
			
			# Ensure that the preferred Arduino port is selected by default
			selectedPort = 0
			for index, item in enumerate(usb_ports):
				if arduinoPort in item:
					selectedPort = index
					
			return jsonify({'status': 'OK','ports':usb_ports,'portSelect':selectedPort})
		
		# If we want to connect/disconnect Arduino device
		elif action == "reconnect":
			
			print("Reconnect to Arduino")
			
			if test_arduino():
				onoff_arduino(workQueue, 0)
				return jsonify({'status': 'OK','arduino': 'Disconnected'})
				
			else:	
				port = request.form.get('port')
				if port is not None and port.isdigit():
					portNum = int(port)
					print("Reconnect to portNum = " + str(portNum))
					# Test whether connection to the selected port is possible
					usb_ports = [
						p.device
						for p in serial.tools.list_ports.comports()
					]
					if portNum >= 0 and portNum < len(usb_ports):
						# Try opening and closing port to see if connection is possible
						try:
							ser = serial.Serial(usb_ports[portNum],115200)
							if (ser.inWaiting() > 0):
								ser.flushInput()
							ser.close()
							onoff_arduino(workQueue, portNum)
							return jsonify({'status': 'OK','arduino': 'Connected'})
						except:
							return jsonify({'status': 'Error','msg':'Unable to connect to selected serial port'})
					else:
						return jsonify({'status': 'Error','msg':'Invalid serial port selected'})
				else:
					return jsonify({'status': 'Error','msg':'Unable to read [port] POST data'})
		else:
			return jsonify({'status': 'Error','msg':'Unable to read [action] POST data'})
	else:
		return jsonify({'status': 'Error','msg':'Unable to read [action] POST data'})
		
# Arduino Status (only looks at battery level at the moment)
@app.route('/arduinoStatus', methods=['POST'])
def arduinoStatus():
	if session.get('active') != True:
		return redirect(url_for('login'))
		
	action = request.form.get('type');
	
	if action is not None:
		if action == "battery":
			if test_arduino():
				return jsonify({'status': 'OK','battery':batteryLevel})
			else:
				return jsonify({'status': 'Error','msg':'Arduino not connected'})
	
	return jsonify({'status': 'Error','msg':'Unable to read POST data'})



class videoPlayer (threading.Thread):
	def __init__(self, threadID, name):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
	def run(self):
		print("Starting Video Thread", self.name)
		PlayMovie(self.name)
		print("Exiting Video Thread", self.name)


def Display_Picture(File_Name):
    image = Image.open(File_Name)
    OLED.Display_Image(image)

def DisplayBatteryLevel():
    global videoFlag
    if ( videoFlag ==1  ):
        return;
    print("Will DisplayBatteryLevel")	
    global batteryLevel
	# oledFolder
    #image = Image.new("RGB", (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT), "BLACK")
    image = Image.open( oledFolder + 'bsun.jpg' )
    draw = ImageDraw.Draw(image)
    fontTitle = ImageFont.truetype(oledFolder + 'cambriab.ttf',10)
    draw.text((16, 0), 'SOLAR CHARGE LEVEL', fill = "YELLOW", font = fontTitle)
    
    font = ImageFont.truetype(oledFolder + 'cambriab.ttf',8)    
    #draw.text((0, 12), 'Level:' + str(batteryLevel), fill = "BLUE", font = font)
    #draw.text((0, 36), 'Electronic', fill = "BLUE",font = font)
    #draw.text((20, 72), '1.5 inch', fill = "CYAN", font = font)
    #draw.text((10, 96), 'R', fill = "RED", font = font)
    #draw.text((25, 96), 'G', fill = "GREEN", font = font)
    #draw.text((40, 96), 'B', fill = "BLUE", font = font)
    #draw.text((55, 96), ' OLED', fill = "CYAN", font = font)
    
    batteryLevelNorm = int(batteryLevel);
    
    #draw.rectangle([(0, 100), (101, 121)], fill = None, outline = "GREEN")
    #draw.rectangle([(1, 101), (batteryLevelNorm, 120)], fill = "GREEN", outline = None)

    if (batteryLevelNorm>110):
        draw.text((0, 118), 'Charging ' + str(batteryLevel), fill = "BLUE", font = font)
        batteryLevelNorm = 100
    elif (batteryLevelNorm<0):
        draw.text((0, 118), 'ERR:No Con ' +  str(batteryLevel), fill = "RED", font = font)
        batteryLevelNorm = 0
    else:
        draw.text((0, 118), str(batteryLevel) + '%', fill = "WHITE", font = font)

    bl = 0
    for y in range(9, -1, -1):
    	if (bl<batteryLevelNorm):
    		draw.rectangle([(60, 25+y*10), (120, 34+y*10)], fill = "YELLOW", outline = "BLACK")
    	bl = bl + 10
   
    if (batteryLevelNorm<4):
       draw.rectangle([(60, 116), (120, 127)], fill = "BLACK", outline = "RED")
       draw.text((64, 116), 'WARNING!', fill = "RED", font = fontTitle)

    	
    	
    OLED.Display_Image(image)

def TryInitArduinoCon():
	portNum = 0
	usb_ports = [
		p.device
		for p in serial.tools.list_ports.comports()
	]

	try:
		ser = serial.Serial(usb_ports[portNum],115200)
		if (ser.inWaiting() > 0):
			ser.flushInput()
		ser.close()
		onoff_arduino(workQueue, portNum)
		print("TryInitArduinoCon Connect to Arduino OK")
	except Exception as e:
		print("TryInitArduinoCon:FAILED! Unable to connect to selected serial port")
		print(e)


def PlayMovie(File_Name):

   global videoFlag
   global stopVideo
   if (videoFlag == 1):
    print("A video is already active")
    stopVideo = 1
    while ( stopVideo == 1):
     print("Waiting to stop previous")
     time.sleep(1)
    
   videoFlag = 1
   clip = soundFolder + File_Name + ".ogg"
   print("Play music clip:", clip)
   pygame.mixer.music.load(clip)
   pygame.mixer.music.set_volume(volume/10.0)
   pygame.mixer.music.play()
   
   videoclip = soundFolder + File_Name + ".webm"
	
   print("Play video clip:", videoclip)
   
   
   captvid = cv2.VideoCapture(videoclip) #Enter the name of your video in here
   #image = Image.new('1', (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT))
   image = Image.new("RGB", (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT), "BLACK")
   draw = ImageDraw.Draw(image)
   frameCounter = 0
   frameSkip = 2 #Change to adjust frame rate
   lowerThresh = 0# Adjust threshold according to video
   #image = Image.new("RGB", (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT), "YELLOW")
   #OLED.Display_Image(image)
   #OLED.Delay(1000)
   while(captvid.isOpened()):
       ret, frame = captvid.read()
       frameStart = time.time()
       if ret==True:
           if frameCounter%frameSkip == 0:
               # Import image as grayscale
   ###            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
               resized = cv2.resize(frame, (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT))

               # Resize to fit OLED screen dimensions
   #            resized = cv2.resize(gray, (OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT))
   #            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                # Threshold it to B&W
   #               (thresh, bw) = cv2.threshold(gray, lowerThresh, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                # Clear screen for next frame
               draw.rectangle((0, 0, OLED.SSD1351_WIDTH, OLED.SSD1351_HEIGHT), outline=0, fill=0)
   ##            oled.fill(0)
               # Convert to OLED format, and print
   #            screenframe = Image.fromarray(bw).convert("1")
   #            OLED.Display_Image(screenframe)
               screenframe = Image.fromarray(resized)
               OLED.Display_Image(screenframe)
               frameEnd = time.time()
               print(1/(frameEnd-frameStart))
           frameCounter=frameCounter+1
           if ( stopVideo == 1):
             stopVideo = 0
             videoFlag = 0
             break
       else:
       	   videoFlag = 0
           stopVideo = 0
           print("Video end")
           break

   stopVideo = 0





def diode_lookup(n_samples):
    result = np.zeros((n_samples,))
    for i in range(0, n_samples):
        v = float(i - float(n_samples)/2)/(n_samples/2)
        v = abs(v)
        if v < VB:
            result[i] = 0
        elif VB < v <= VL:
            result[i] = H * ((v - VB)**2)/(2*VL - 2*VB)
        else:
            result[i] = H*v - H*VL + (H*(VL-VB)**2)/(2*VL-2*VB)

    return result

def raw_diode(signal):
    result = np.zeros(signal.shape)
    for i in range(0, signal.shape[0]):
        v = signal[i]
        if v < VB:
            result[i] = 0
        elif VB < v <= VL:
            result[i] = H * ((v - VB)**2)/(2*VL - 2*VB)
    else:
        result[i] = H*v - H*VL + (H*(VL-VB)**2)/(2*VL-2*VB)
    return result


def robotvoice(lng, txt):
	tts = gtts.gTTS( txt , lang= lng)
	clip = soundFolder + "txt.mp3"
	tts.save(clip)
	

	"""
	Program to make a robot voice by simulating a ring modulator;
	procedure/math taken from
	http://recherche.ircam.fr/pub/dafx11/Papers/66_e.pdf
	"""
	#clip = soundFolder + "sample.wav
	import tempfile
	mp3 = pydub.AudioSegment.from_mp3(clip)
	clip = soundFolder + "txt.wav"
	mp3.export(clip, format="wav")
	left_channel =  pydub.AudioSegment.from_wav(clip)
	right_channel =  pydub.AudioSegment.from_wav(clip)
	audiofile = pydub.AudioSegment.from_mono_audiosegments(left_channel, right_channel)
	audiofile.export(clip, format="wav")
	print("Convert wav clip:", clip)
	rate, data = wavfile.read(clip)

	print(data)
	length = data.shape[0] / rate
	print(f"length = {length}s")

	print(f"number of channels = {data.shape[1]}")

	data = data[:,1]

	# get max value to scale to original volume at the end
	scaler = np.max(np.abs(data))

	# Normalize to floats in range -1.0 < data < 1.0
	data = data.astype(np.float)/scaler

	# Length of array (number of samples)
	n_samples = data.shape[0]

	# Create the lookup table for simulating the diode.
	d_lookup = diode_lookup(LOOKUP_SAMPLES)
	diode = Waveshaper(d_lookup)

	# Simulate sine wave of frequency MOD_F (in Hz)
	tone = np.arange(n_samples)
	tone = np.sin(2*np.pi*tone*MOD_F/rate)

	# Gain tone by 1/2
	tone = tone * 0.5

        # Junctions here
	tone2 = tone.copy() # to top path
	data2 = data.copy() # to bottom path

        # Invert tone, sum paths
	tone = -tone + data2 # bottom path
	data = data + tone2 #top path

        #top
	data = diode.transform(data) + diode.transform(-data)

        #bottom
	tone = diode.transform(tone) + diode.transform(-tone)

	result = data - tone

        #scale to +-1.0
	result /= np.max(np.abs(result))
        #now scale to max value of input file.
	result *= scaler
        # wavfile.write wants ints between +-5000; hence the cast
	clip = soundFolder + "robot.wav"
	wavfile.write(clip, rate, result.astype(np.int16))
	print("Play TTS clip:", clip)
	pygame.mixer.music.load(clip)
	pygame.mixer.music.play()

if __name__ == '__main__':
	#-------------OLED Init------------#
	OLED.Device_Init()	
	thread = videoPlayer(1, "BandL")
	thread.start()
	videothreads.append(thread)	
	TryInitArduinoCon()
	DisplayBatteryLevel()
	time.sleep(5)
	playsoundclip("GR_myNameIsWallE.ogg")	
	app.run(debug=False, host='0.0.0.0')
