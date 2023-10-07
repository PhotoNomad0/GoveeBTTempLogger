#!/usr/bin/python3.9

import os
import sys
import glob
import time
from datetime import datetime, timezone
import logging
import subprocess

date_format = "%Y-%m-%d %H:%M:%S"
greenText = '\033[32m'
yellowText = '\033[33m'
defaultColorText = '\033[0m'
blackText = '\033[30m'
redText = '\033[31m'
blueText = '\033[34m'
magentaText = '\033[35m'
cyanText = '\033[36m'
whiteText = '\033[37m'
whiteBackground = '\033[47m'
clearScreen = '\033[2J'

logging.basicConfig(filename='GoveeBTTempLogger.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

gardenLow = 41
limits = {
    "all": {
        "battery": {
            "low": 25
        }
    },
    "crawl": {
        "humidity": {
            "hi": 55
        }
    },
    "garage": {
        "temp" : {
            "low": 40
        }
    },
    "garden": {
        "temp" : {
            "low": gardenLow
        }
    },
    "porch": {
        "temp" : {
            "low": gardenLow + 5
        }
    },
    "living": {
        "temp": {
            "low": 55,
            "hi": 85
        },
        "humidity": {
            "hi": 60
        }
    }
}

# this is for testing on machine without HW
simulateData = [
    [
        "A4:C1:38:E7:2A:5F\tGarden (A4:C1:38:E7:2A:5F)",
        "A4:C1:38:7C:05:A8\tCrawl (A4:C1:38:7C:05:A8)",
    ],
    {
        "A4C138E72A5F": "2023-09-10 09:09:50	-5	56.4	100",
        "A4C1387C05A8": "2023-09-10 09:09:51	19	80	15"
    }
]
simulate = None # set to simulateData for testing


def logInfo(msg):
    print(msg)
    logging.info(msg)


def logError(msg):
    print(msg)
    logging.error(msg)


def checkLimits_(value, type, sensor):
    sensor = sensor.lower()
    hiLimit = False
    lowLimit = False
    if isinstance(value, str):
        value = float(value)
    if sensor in limits:
        sensorLimits = limits[sensor]
        if type in sensorLimits:
            typeLimits = sensorLimits[type]
            if "hi" in typeLimits:
                hiLimit = value >= typeLimits["hi"]
            if "low" in typeLimits:
                lowLimit = value <= typeLimits["low"]

    return hiLimit or lowLimit

def checkLimits(value, type, sensor):
    atLimit = checkLimits_(value, type, sensor)
    allAtLimit = checkLimits_(value, type, 'all')
    return atLimit or allAtLimit


def setColor(value, type, sensor, defaultColor=greenText):
    atLimit = checkLimits(value, type, sensor)
    return setColorIfLimit(atLimit, redText, defaultColor)


def setColorIfLimit(atLimit, limitColor, defaultColor):
    if atLimit:
        return limitColor
    return defaultColor


def list_txt_files(folder_path):
    return glob.glob(f"{folder_path}/*.txt")

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.read()
            return lines
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def extractLine(data, pos, endPos):
    line = data[pos:(endPos + 1)].strip()
    line = line.replace('\x00', '')  # for some reason starting to see null character at end of file, so we remove it
    return line

def extract_last_line(data):
    endPos = len(data)
    while endPos > 0:
        pos = data.rfind('\n', 0, endPos)
        if pos >= 0:
            line = extractLine(data, pos + 1, endPos)
            if line and len(line) > 0:
                print ("Found at pos=", pos, "len=", len(line), ", line", line)
                return line
            else:
                print ("Line not found at pos=", pos, "to endPos=", endPos, "len=", len(line))

        if pos < 0:
            npos = 0
            line = extractLine(data, npos, endPos)
            if line and len(line) > 0:
                print ("Found at pos=", npos, "len=", len(line), ", line", line)
                return line
            else:
                print ("Line not found at pos=", npos, "to endPos=", endPos, "len=", len(line))

        endPos = pos - 1

    return None

# line = "2023-09-10 09:09:50	-5	56.4	100\n2023-09-10 09:09:51	-5	56.4	99\n"
# lline = extract_last_line(line)
# print(lline)

def latest_files(file_list):
    # Initialize a dictionary to store the latest files
    latest_files = {}

    for file in file_list:
        try:
            filename = os.path.basename(file)
            # Split the file name into components
            parts = filename.split('-')

            # Extract the ID and date
            id = parts[1]
            dateStr = parts[2] + '-' + parts[3].split('.')[0]
            date = datetime.strptime(dateStr, '%Y-%m')

            # If this ID is not in the dictionary or this file is more recent, update the dictionary
            if id not in latest_files or date > latest_files[id][1]:
                latest_files[id] = (file, date)
        except Exception as e:
            print(f"Skipping file {file}: {e}")

    # Return only the file names from the dictionary
    return [file for file, date in latest_files.values()]

# # Test with a list of file names
# file_list = ["path/stuff", "/path/gvh-A4C1383BB160-2023-09.txt", "/path/gvh-A4C1383BB160-2023-08.txt", "/path/gvh-B4D1383BB161-2023-07.txt", "/path/gvh-B4D1383BB161-2023-10.txt"]
# print(latest_files(file_list))


def read_last_line(file_path):
    data = read_file(file_path)
    line = extract_last_line(data)
    return line

def convert_celsius_to_fahrenheit(celsius):
    fahrenheit = (celsius * 1.8) + 32
    return fahrenheit


def findMatch(array, target):
    for string in array:
        if string == target:
            return True
    return False


folder_path = "/var/log/goveebttemplogger"

idx = 0
system = False
backupInterval = 0
backupCount = 0
sleepTime = 60
if len(sys.argv) > 1:
    if findMatch(sys.argv, '--system'):
        idx = 1
        system = True
        logInfo("System mode is on")
        sleepTime = 60 * 60 * 2 # 2 hours

    if findMatch(sys.argv, '--backup'):
        backup = True
        backupTime = 60 * 60 * 2 # 2 hours
        backupInterval = int(backupTime/sleepTime)
        logInfo(f"backup mode is on, every {backupInterval} counts of {sleepTime}")
        backupCount = -1

if len(sys.argv) > idx + 1:
    folder_path = sys.argv[idx]
    logInfo(f"Starting APP - Folder path on command line is: {folder_path}")
else:
    logInfo(f"Starting APP - Default Folder path is: {folder_path}")

if simulate:
    sensorsData = simulate[0]
else:
    sensorsData = read_file("/var/www/html/goveebttemplogger/gvh-titlemap.txt").split('\n')

logInfo(f"Print Interval seconds: {sleepTime}")
logInfo(f"Sensor Data: {sensorsData}")
sensors = {}
files = []

if sensorsData:
    for sensorLine in sensorsData:
        if sensorLine:
            data = sensorLine.strip().split('\t')
            print("Data", data)
            sensorAddr = data[0].replace(":", "")
            labelParts = data[1].split('(')
            sensors[sensorAddr] = {
                'label': labelParts[0].strip()
            }

logInfo(f"Sensors: {sensors}")

def getTime():
    return datetime.now().astimezone()


def runCommand(command, title):
    try:
        result = subprocess.run(command.split(), capture_output=True)
        if result.returncode == 0:
            print(f"Command '{title}' was successful")
            return True

        else:
            logError(f"Command '{title}' failed with error: {result.stderr}")
            logError(f"Failed to run '{command}'")

    except Exception as e:
        logError(f"An error occurred running Command '{title}': {e}")

    return False


def backupData():
    global backupCount, backupInterval

    if (backupCount <= 0):
        print("Doing backup")
        command = "rsync -arvWutpO --modify-window=61 --ignore-errors --progress /var/log/goveebttemplogger/* /mnt/macExtern/temp-temp/Govee/log/"
        runCommand(command, "Backup Log")
        command = "rsync -arvWutpO --modify-window=61 --ignore-errors --progress /var/www/html/goveebttemplogger/* /mnt/macExtern/temp-temp/Govee/html/"
        runCommand(command, "Backup HTML")
        backupCount = backupInterval

    backupInterval -= 1

def restartMeasurementService():
    logError('### Measurements are HUNG!')
    command = "systemctl restart goveebttemplogger"
    runCommand(command, "Templogger Service restarted")


while True:
    # print(clearScreen)
    if backup:
        backupData()
        print("backupCount=", backupCount)

    if simulate:
        files_ = list(simulate[1].keys())
    else:
        files_ = list_txt_files(folder_path)
        files_ = latest_files(files_)

    if files != files_: # see if changed
        files = files_
        logging.info(F"Data Files found in path: {files}")

    for file in files:
        measurement = None
        if simulate:
            sensorId = file
            measurement = simulate[1][file]
        else:
            filename = os.path.basename(file)
            parts = filename.split('-')
            sensorId = parts[1]
            sensorLabel = sensorId

        if sensorId in sensors:
            if 'label' in sensors[sensorId]:
                sensorLabel = sensors[sensorId]['label']
        else:
            sensors[sensorId] = {}

        if len(sensorId) == 12:
            if not simulate:
                measurement = read_last_line(file)
            if measurement:
                data = measurement.strip().split('\t')
                # print(file,"='", measurement, "'")
                time_ = datetime.strptime(data[0], date_format).replace(tzinfo=timezone.utc)
                temp = float(data[1])
                temp = convert_celsius_to_fahrenheit(temp)
                tempStr = "{:.1f}".format(temp)
                humidity = float(data[2])
                humidityStr = "{:.0f}".format(humidity)
                battery = data[3]
                sampleTime = time_.astimezone()

                sensors[sensorId]['date'] = sampleTime
                sensors[sensorId]['temp'] = tempStr
                sensors[sensorId]['battery'] = battery
                sensors[sensorId]['humidity'] = humidityStr

    print(blackText + "\n===================================================\n" +
          "Temp\tHumidty\tBattery\tLocation\tTime"
          )

    now = getTime()
    timeout = False

    for s in sensors.values():
        if ('label' in s) and ('temp' in s):
            sensorLabel = s['label']
            temp_ = s['temp']
            tempState = setColor(temp_, 'temp', sensorLabel)
            humidity_ = s['humidity']
            humidityState = setColor(humidity_, 'humidity', sensorLabel)
            battery_ = s['battery']
            batteryState = setColor(battery_, 'battery', sensorLabel, blueText)

            sampleTime = s['date']
            # Calculate time difference
            diff = now - sampleTime
            # Convert time difference to minutes
            minutes = diff.total_seconds() / 60
            oldMeasurement = abs(minutes) >= 10
            if oldMeasurement:
                timeout = True

            sampleTimeState = setColorIfLimit(oldMeasurement, redText, defaultColorText)
            sampleTimeStr = sampleTimeState + sampleTime.strftime(date_format)
            tempStr = tempState + temp_ + 'F'
            battery = batteryState + battery_ + '%'
            humidityStr = humidityState + humidity_ + '%'
            line = greenText + tempStr + '\t' + humidityStr + '\t' + battery + '\t' + blackText + sensorLabel + '\t' + sampleTimeStr + blackText
            print(line)

    if timeout and system:
        restartMeasurementService()

    time.sleep(sleepTime)


