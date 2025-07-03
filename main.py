import sys
import os


picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')

if (os.path.exists(libdir)):
	sys.path.append(libdir)

from gpiozero import Button
import json
import glob
import vlc
import time
from PIL import Image,ImageDraw,ImageFont
import logging
import tempfile
import shutil
import subprocess
from waveshare_epd import epd3in52
from evdev import InputDevice, categorize, ecodes
import threading

logging.basicConfig(level=logging.DEBUG)

BluetoothDevicePath = "/dev/input/event2"



#init buttons

leftButton = Button(26, pull_up =False, bounce_time =0.05)
rightButton = Button(19, pull_up =False, bounce_time =0.05)
enterButton = Button(13, pull_up =False, bounce_time =0.05)
menuButton = Button(6, pull_up =False, bounce_time =0.05)
otherButton = Button(5, pull_up =False, bounce_time =0.05)

# menu names "Player" "Chapter" "Book"

menuTitle = "Player"

timesPath = "./times.json"
settingsPath = "./settings.json"
bookpaths = []
chapterTimes = []

def WaitForAudio(mac):
	print("waiting")
	while True:
		output = os.popen(f"bluetoothctl info {mac}").read()
		if "Connected: yes" in output:
			print("connected")
			return
		print("not connected trying again")
		time.sleep(2)

WaitForAudio("E8:EE:CC:F4:D6:3C")




def button_listener():
	dev = InputDevice(BluetoothDevicePath)
	print(f"lisstening to {dev.path}: {dev.name}")
	for event in dev.read_loop():
		if event.type == ecodes.EV_KEY:
			key_event = categorize(event)
			if key_event.keystate == key_event.key_down:
				code = key_event.scancode
    
				if code == 200:
					print("Play pressed")
                    # call your play function
				elif code == 201:
					print("Pause pressed")
                    # call your pause function


def GetChapterTimes():
	global player
	media = player.get_media()
	media.parse()
	currentTime = player.get_time()
	if (player.get_chapter() == -1):
		return -1
	times = []
	time.sleep(0.1)
	chapterCount = player.get_chapter_count()
	for i in range(chapterCount):
		player.set_chapter(i)
		time.sleep(0.1)
		chapterTime = player.get_time()
		times.append(chapterTime)
		time.sleep(0.1)

	player.set_time(currentTime)
	return times


def GetStoredTime(path: str) -> int:
	if (os.path.exists(timesPath)):
		print("get")
		print(path)
		with open(timesPath, 'r') as f:
			data = json.load(f)
		return data.get(path, 0)
	return -1

def StoreTime(path: str, time: int):
	data = {}
	print("store:")
	print(path)
	if (os.path.exists(timesPath)):
		with open(timesPath, 'r') as f:
			try:
				data = json.load(f)
			except json.JSONDecodeError:
				print("JSON CORRUPTED")
				data = {}

	data[path] = time

	dir_name = os.path.dirname(timesPath) or '.'
	with tempfile.NamedTemporaryFile('w', dir = dir_name, delete = False) as tf:
		json.dump(data,tf,indent=2)
		temp_name = tf.name

	shutil.move(temp_name,timesPath)
	#with open(timesPath, 'w') as f:
	#	json.dump(data, f, indent=2)


def GetSettings():
	if (os.path.exists(settingsPath)):
		with open(settingsPath, 'r') as f:
			data = json.load(f)
		return data
	return -1

def StoreSettings(book, volume):
	data = {}
	if (os.path.exists(settingsPath)):
		with open(settingsPath,'r') as f:
			try:
				data = json.load(f)
			except json.JSONDecodeError:
				print("JSON BAD")
				data = {}
	data["book"] = book
	data["volume"] = volume
	
	dir_name = os.path.dirname(timesPath) or '.'
	with tempfile.NamedTemporaryFile('w', dir = dir_name, delete = False) as tf:
		json.dump(data, tf, indent =2)
		temp_name = tf.name
	shutil.move(temp_name, settingsPath)

def LoadBook(path):
	global player
	global title
	player.set_mrl(path)
	time.sleep(0.1)
	media = player.get_media()
	media.parse()
	time.sleep(0.2)	
	mrl = media.get_mrl()
	time.sleep(0.2)
	chapterCount = player.get_chapter_count()
	currentChapter = player.get_chapter()
	title = player.get_title()
	storedTime = GetStoredTime(mrl)
	player.play()
	print(player.get_state())
	time.sleep(0.1)
	player.set_pause(1)
	print(player.get_state())
	time.sleep(0.1)
	if (storedTime != -1):
		player.set_time(storedTime)
	print("loaded: " + str(storedTime))
	global chapterTimes
	a = GetChapterTimes()
	time.sleep(0.1)
	print(a)
	
	chapterTimes = a
	title = media.get_meta(vlc.Meta.Title)
	# set all chapter menu stuff to 0
	time.sleep(0.1)
	global menuTitle
	menuTitle = "Player"
	DrawUI()


def StoreBook():
	global player
	title = player.get_title()
	current_time = player.get_time()
	if (current_time == -1):
		return -1
	media = player.get_media()
	mrl = media.get_mrl()
	StoreTime(mrl, current_time)
	print("stored: " + str(current_time))

def GetBooks():
	bookpaths.clear()
	root_dir= os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),'player/books')
	print(root_dir)
	for filename in glob.iglob(root_dir + '**//*.m4a', recursive=True):
		bookpaths.append(filename)

titles = []

def GetTitles():
	titles.clear()
	GetBooks()
	for x in bookpaths:
		book = x.split("/")[-1].split(".")[0]
		titles.append(book)

def GetChapters():
	global player
	chapters = []
	chapterCount = player.get_chapter_count()
	for i in range(chapterCount):
		chapters.append(i+1)
	return chapters

def GeneratePagedArray(list):
	itemLimit = 10
	i =0
	page = []
	pages =[]
	for x in list:
		page.append(x)
		i += 1
		if (i %10 == 0):
			pages.append(page)
			page = []
	pages.append(page)
	return pages

chapterMenuPageSelection = False
chapterPageSelection = 0
chapterSelection = 0

def DrawChapters():
	print("chapter menu yay")
	pages = GeneratePagedArray(GetChapters())
	chapterToDisplay = pages[chapterPageSelection]
	global epd
	global player
	font = ImageFont.truetype(os.path.join(picdir,'Font.ttc'), 20)
	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)
	itemYPosition = 3
	currentItem = 0
	for item in chapterToDisplay:
		fillVal =0
		if (currentItem == chapterSelection and chapterMenuPageSelection == False):
			draw.rectangle((0,itemYPosition,360,itemYPosition+24), fill=0)
			fillVal =1
		draw.text((10,itemYPosition), str(item), font = font, fill = fillVal)
		draw.text((280, itemYPosition), str(FormatTime(chapterTimes[item-1]/1000)), font = font, fill = fillVal)
		itemYPosition += 22
		currentItem += 1

	pageFillVal =0
	if (chapterMenuPageSelection == True):
		draw.rectangle((0,228,73,242), fill=0)
		pageFillVal =1

	draw.text((10,227), (f"Page: ({chapterPageSelection+1}/{len(pages)})"), fill = pageFillVal)

	epd.display(epd.getbuffer(image))
	epd.lut_GC()
	epd.refresh()

libraryMenuPageSelection = False
libraryPageSelection = 0
librarySelection = 0



def DrawLibrary():
	print("Library YAY")
	pages = GeneratePagedArray(titlePaths)
	pageToDisplay = pages[libraryPageSelection]
	global epd
	global player
	font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)
	itemYPosition = 3
	currentItem = 0
	for item in pageToDisplay:
		fillVal = 0
		if (currentItem == librarySelection and libraryMenuPageSelection == False):
			draw.rectangle((0,itemYPosition, 360, itemYPosition +24), fill=0)
			fillVal =1
		
		draw.text((10, itemYPosition), item[0], font =  font, fill = fillVal)
		itemYPosition += 22
		currentItem += 1

	pageFillVal = 0
	if (libraryMenuPageSelection == True):
		draw.rectangle((0,228,73,242),fill=0)
		pageFillVal = 1

	draw.text((10,227), (f"Page: ({libraryPageSelection+1}/{len(pages)})"), fill =pageFillVal)

	epd.display(epd.getbuffer(image))
	epd.lut_GC()
	epd.refresh()


volumeIndex = 0
volumeArr = [1,5,10]
volumeMenu = False

def DrawVolume():
	global epd
	global player
	font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'),40)
	
	font2 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'),20)
	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)
	draw.text((5,5), "Volume", font = font, fill = 0)
	currentVolume = player.audio_get_volume()
	
	draw.rectangle((3, 100, int(currentVolume*3.4)+3, 140), fill =0 )
	draw.rectangle((305,5, 340,25), fill = not(volumeMenu))
	draw.text((320, 5), str(volumeArr[volumeIndex]), font = font2, fill = volumeMenu)
	epd.display(epd.getbuffer(image))
	epd.lut_GC()
	epd.refresh()


def DrawUI():
	print("DrawUI: " + menuTitle)
	if (menuTitle == "Player"):
		global epd
		global player
		DrawPlayer(epd, player)
		return
	if (menuTitle == "Menu"):
		DrawMenu()
		return
	if (menuTitle == "Chapters"):
		DrawChapters()
		return
	if (menuTitle == "Library"):
		DrawLibrary()
		return
	if (menuTitle == "Volume"):
		DrawVolume()
		return

def Left():
	print("left")
	global menuTitle
	if (menuTitle == "Player"):
		#player.previous_chapter()
		player.set_time(max(player.get_time()-15000, 0))
	elif (menuTitle =="Menu"):
		global menuSelectionIndex
		global menuSelection
		menuSelectionIndex = (menuSelectionIndex - 1)
		if (menuSelectionIndex < 0):
			menuSelectionIndex = len(menuSelection)-1
	elif (menuTitle == "Chapters"):
		global chapterMenuPageSelection
		global chapterPageSelection
		global chapterSelection
		pages = GeneratePagedArray(GetChapters())
		if (chapterMenuPageSelection):
			chapterPageSelection -= 1
			if (chapterPageSelection < 0):
				chapterPageSelection = len(pages) -1
		else:
			chapterSelection = chapterSelection -1
			if (chapterSelection <0):
				chapterSelection = len(pages[chapterPageSelection]) -1
	elif (menuTitle == "Library"):
		global libraryMenuPageSelection
		global libraryPageSelection
		global titlePaths
		global librarySelection
		pages = GeneratePagedArray(titlePaths)
		if (libraryMenuPageSelection):
			libraryPageSelection -= 1
			if (libraryPageSelection < 0):
				libraryPageSelection = len(pages) -1
		else:
			librarySelection = librarySelection - 1
			if (librarySelection <0):
				librarySelection = len(pages[libraryPageSelection])-1
	elif (menuTitle == "Volume"):
		global volumeIndex
		if (not volumeMenu):
			currentVolume = player.audio_get_volume()
			nextVolume = currentVolume - volumeArr[volumeIndex]
			if (nextVolume < 0):
				nextVolume = 0
			player.audio_set_volume(nextVolume)
		else:
			volumeIndex = (volumeIndex -1) % len(volumeArr)
	DrawUI()


def right():
	print("right")
	global player
	if (menuTitle == "Player"):
		#player.next_chapter()
		player.set_time(min(player.get_time()+15000, player.get_length()))
	elif (menuTitle == "Menu"):
		global menuSelectionIndex
		global menuSelection
		menuSelectionIndex = (menuSelectionIndex + 1) % len(menuSelection)
	elif (menuTitle =="Chapters"):
		global chapterMenuPageSelection
		global chapterPageSelection
		global chapterSelection
		pages = GeneratePagedArray(GetChapters())
		if (chapterMenuPageSelection):
			chapterPageSelection += 1
			if (chapterPageSelection > len(pages)-1):
				chapterPageSelection = 0
		else:
			chapterSelection += 1
			chapterSelection = chapterSelection % len(pages[chapterPageSelection])
	elif (menuTitle =="Library"):
		global libraryMenuPageSelection
		global libraryPageSelection
		global titlePaths
		global librarySelection
		pages = GeneratePagedArray(titlePaths)
		if (libraryMenuPageSelection):
			libraryPageSelection += 1
			if (libraryPageSelection > len(pages)-1):
				libraryPageSelection = 0
		else:
			librarySelection += 1
			librarySelection = librarySelection % len(pages[libraryPageSelection])

	elif (menuTitle == "Volume"):
		global volumeIndex
		if (not volumeMenu):
			currentVolume = player.audio_get_volume()
			nextVolume = currentVolume + volumeArr[volumeIndex]
			if (nextVolume > 100):
				nextVolume = 100
			player.audio_set_volume(nextVolume)
		else:
			volumeIndex = (volumeIndex +1) % len(volumeArr)
	DrawUI()





def enter():
	print("enter")
	global menuTitle
	global player
	print(menuTitle)
	if (menuTitle == "Player"):
		state = player.get_state()
		print(state)
		player.set_pause(int(state == vlc.State.Playing))
	elif (menuTitle == "Menu"):
		print("menuEnter")
		option = menuSelection[menuSelectionIndex]
		menuTitle = option
		time.sleep(0.1)
		DrawUI()
	elif (menuTitle == "Chapters"):
		global chapterMenuPageSelection
		if (chapterMenuPageSelection == True):
			chapterMenuPageSelection = False
		else:
			chapter = GeneratePagedArray(GetChapters())[chapterPageSelection][chapterSelection]
			player.set_chapter(chapter-1)
			menuTitle = "Player"
			DrawUI()
	elif (menuTitle == "Library"):
		global libraryMenuPageSelection
		if (libraryMenuPageSelection == True):
			libraryMenuPageSelection = False
		else:
			book = GeneratePagedArray(titlePaths)[libraryPageSelection][librarySelection][1]
			global titleIndex
			titleIndex = libraryPageSelection *10 + librarySelection
			print("loadingBook")
			LoadBook(book)

def menu():
	print("menu")

	global menuTitle
	global libraryPageSelection
	global chapterPageSelection
	global chapterSelection
	global librarySelection
	global player
	currentChapter = player.get_chapter()
	global title
	global titleIndex
	chapterSelection = currentChapter % 10 # 10 being the max amount in the page
	chapterPageSelection = currentChapter // 10
	librarySelection = titleIndex % 10
	libraryPageSelection = titleIndex // 10
	if (menuTitle != "Menu"):

		menuTitle= "Menu"
		DrawUI()
def other():
	print("other")
	#if (menuTitle == "Player"):
	#	DrawPlayer(epd, player)

	#if (menuTitle == "Menu"):
	#	DrawMenu()

	if (menuTitle == "Chapters"):
		global chapterMenuPageSelection
		chapterMenuPageSelection = not chapterMenuPageSelection
		print(chapterMenuPageSelection)
	if (menuTitle == "Library"):
		global libraryMenuPageSelection
		libraryMenuPageSelection = not libraryMenuPageSelection
	time.sleep(0.1)
	
	if (menuTitle == "Volume"):
		global volumeMenu
		print (volumeMenu)
		volumeMenu = not volumeMenu
	DrawUI()

def FormatTime(seconds):
	hours = int(seconds) //3600
	mins = (int(seconds) %3600) //60
	secs = int(seconds) % 60
	return f"{hours:02}:{mins:02}:{secs:02}"

def DrawBookSelect(epd):
	print("a")

	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)
def DrawChapterSelect(epd):
	print("b")

	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)

menuSelection = ["Player", "Chapters", "Library", "Volume"]
menuSelectionIndex = 0
def DrawMenu():
	global menuSelection
	global menuSelectionIndex
	global epd
	global player
	font = ImageFont.truetype(os.path.join(picdir,'Font.ttc'),85)
	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)
	draw.text((3,60), (f"{menuSelection[menuSelectionIndex]}"), font = font, fill =0)


	epd.display(epd.getbuffer(image))
	epd.lut_GC()
	epd.refresh()


def DrawPlayer(epd, player):

	global chapterTimes
	global currentTitle
	barMargin = 10
	
	barYBottomMargin = 10
	barHeight = 30
	barYOffset = 10
	media = player.get_media()
	media.parse()
	time.sleep(0.1)
	font24 = ImageFont.truetype(os.path.join(picdir,'Font.ttc'),20)
	font16 = ImageFont.truetype(os.path.join(picdir,'Font.ttc'),16)

	chapterCount = player.get_chapter_count()
	currentChapter = player.get_chapter()
#	time.sleep(0.1)
#	GetChapterTimes()
#	time.sleep(0.1)
	image = Image.new('1', (epd.height, epd.width), 255)
	draw = ImageDraw.Draw(image)

	total_seconds = player.get_length() /1000
	current_seconds = player.get_time() / 1000
	current_chapter_time = player.get_time() - chapterTimes[currentChapter]
	chapter_end_time = chapterTimes[currentChapter + 1] - chapterTimes[currentChapter]
	if (chapter_end_time == 0):
		chapter_end_time = 1
	print("end time ")
	print(chapter_end_time)
	progress = max(0.0, min(1.0, current_chapter_time / chapter_end_time if total_seconds else 1))

	barWidth = epd.height - (2*barMargin)
	barY =epd.width - barYBottomMargin - barHeight
	filled = int(progress * barWidth)
	draw.rectangle((barMargin, barY, barMargin+filled, barY+barHeight),fill=0)

	# current time text
	chapterTimeText =(f"{FormatTime(current_chapter_time/1000)}/{FormatTime(chapter_end_time/1000)}")

	draw.text((100, 132), (f"Chapter: {player.get_chapter()+1}"), font = font24, fill =0)
	draw.text((100,153), (f"{FormatTime(current_seconds)}/{FormatTime(total_seconds)}"), font = font24, fill = 0)
	draw.text((100,175), chapterTimeText, font = font24, fill =0)
	#display image

	draw.text((5,5), (f"{title}"), font = font16, fill =0)

	epd.display(epd.getbuffer(image))
	epd.lut_GC()
	epd.refresh()


#button callbacks
leftButton.when_pressed = Left
rightButton.when_pressed = right
enterButton.when_pressed = enter
menuButton.when_pressed = menu
otherButton.when_pressed = other

settings = GetSettings()
if (settings == -1):
	print("settings grab fail")




GetBooks()

#start book load this with previously played book later
titleIndex = 0
book = bookpaths[titleIndex]


player = 0
#player = vlc.MediaPlayer("/home/audiopi/e-Paper/RaspberryPi_JetsonNano/python/player/books/Arcanum Unbounded: Cosmere Collection.m4a")
instance = vlc.Instance("--intf=dummy", "--extraintf=dbus")
media = 0
if (settings != -1):
	print("loadingbook" )
	media = instance.media_new(settings["book"])
	player = instance.media_player_new()
	player.set_media(media)
	#player =  vlc.MediaPlayer(settings["book"], "--extraintf=dbus")
else:
	media = instance.media_new(book)
	player = instance.media_player_new()
	player.set_media(media)
	#player =  vlc.MediaPlayer(book, "--extraintf=dbus")

if (settings != -1):

	player.audio_set_volume(settings["volume"])
else:
	player.audio_set_volume(33)
media = player.get_media()
media.parse()
title = media.get_meta(vlc.Meta.Title)

print (GetChapters())
print (GeneratePagedArray(GetChapters()))
print(player.get_state())


GetBooks()



GetTitles()

print(titles)
print(bookpaths)

titlePaths = []

for i in range(len(titles)):
	titlePath = []
	titlePath.append(titles[i])
	titlePath.append(bookpaths[i])
	titlePaths.append(titlePath)

print(GeneratePagedArray(titlePaths))




try:
	epd = epd3in52.EPD()
	epd.init()
	epd.display_NUM(epd.WHITE)
	epd.lut_GC()
	epd.refresh()
	epd.send_command(0x50)
	epd.send_data(0x17)
	time.sleep(1)
	font24 = ImageFont.truetype(os.path.join(picdir,'Font.ttc'),16)
	font18 = ImageFont.truetype(os.path.join(picdir,'Font.ttc'),16)

	#Himage = Image.new('1', (epd.height, epd.width), 255)
	#draw = ImageDraw.Draw(Himage)
	#draw.text((10,0), '24', font = font24, fill =0)
	#draw.text((10,20), '18', font = font18, fill =0)
	GetTitles()
	#startPos = 40
	#for i in titles:
	#	draw.text((10,startPos), i, font = font18, fill = 0)
	#	startPos += 20



	#epd.display(epd.getbuffer(Himage))
	#epd.lut_GC()
	#epd.refresh()
	#time.sleep(1)
	if (settings != -1):
	
		LoadBook(settings["book"])
	t = 1
	#DrawPlayer(epd, player)

	listener_thread = threading.Thread(target=button_listener, daemon=True)
	listener_thread.start()	

	while True:
		time.sleep(1)
		
		t+= 1 
		if (t % 25 == 0):
			StoreBook()
		if (t%60 ==0):
			media = player.get_media()
			media.parse()
			StoreSettings(media.get_mrl(), player.audio_get_volume())

except IOError as e:
	logging.info(e)

except	KeyboardInterrupt:
	logging.info("ctrl + c:")
	epd3in52.epdconfig.module_exit(cleanup=True)
	exit()
