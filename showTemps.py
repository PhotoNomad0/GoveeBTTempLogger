#!/usr/bin/python3.9

import os
import sys
import glob
import time
from datetime import datetime, timezone

date_format = "%Y-%m-%d %H:%M:%S"
greenText = '\033[32m'
yellowText = '\033[33m'
defaultText = '\033[0m'
blackText = '\033[30m'
redText = '\033[31m'
blueText = '\033[34m'
magentaText = '\033[35m'
cyanText = '\033[36m'
whiteText = '\033[37m'
whiteBackground = '\033[47m'

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

# A4:C1:38:E7:2A:5F	Garden (A4:C1:38:E7:2A:5F)
# A4:C1:38:3F:B0:01	Porch (A4:C1:38:3F:B0:01)
# A4:C1:38:D0:1B:A5	Garage (A4:C1:38:D0:1B:A5)
# A4:C1:38:7C:05:A8	Crawl (A4:C1:38:7C:05:A8)
# A4:C1:38:3B:B1:60	Living (A4:C1:38:3B:B1:60)

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
    if atLimit:
        return redText
    return defaultColor


# expr = "setColor('24.9', 'battery', 'garage', blueText)"
# expr = "setColor(24.9, 'temp', 'garden')"
#
# print(expr, "at limit =", eval(expr))

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

def read_last_line(file_path):
    data = read_file(file_path)
    endPos = len(data)
    while endPos > 0:
        pos = data.rfind('\n', 0, endPos)
        if pos >= 0:
            line = data[(pos+1):(endPos+1)].strip()
            line = line.replace('\x00', '')
            if line and len(line) > 0:
                print ("Found at pos=", pos, "len=", len(line), ", line", line)
                return line
            else:
                print ("Line not found at pos=", pos, "to endPos=", endPos, "len=", len(line))
        endPos = pos - 1
    return None

# could not read file with seek - got error FileNotFoundError.  Saw comment that some unix systems not seekable?
# def read_last_line(file_path, chunk_size=128):
#     try:
#         with open(filename, 'r') as file:
#             print("opened", file_path)
#             file.seek(-128, 2)  # Move the pointer 128 characters from the end of the file
#             print("seeked", file_path)
#             data = file.read()
#             print("read", file_path)
#             if data:
#                 lines = data.split('\n')
#                 return lines[-1] if lines else None
#     except FileNotFoundError:
#         print(f"File {file_path} not found.")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#     return None

def convert_celsius_to_fahrenheit(celsius):
    fahrenheit = (celsius * 1.8) + 32
    return fahrenheit

folder_path = "/var/log/goveebttemplogger"
if len(sys.argv) > 1:
    folder_path = sys.argv[1]

if simulate:
    sensorsData = simulate[0]
else:
    sensorsData = read_file("/var/www/html/goveebttemplogger/gvh-titlemap.txt").split('\n')
print("Sensor Data", sensorsData)
sensors = {}

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

print("Sensors", sensors)

print("Data Files in path", folder_path, ":")
if simulate:
    files = list(simulate[1].keys())
else:
    files = list_txt_files(folder_path)

while True:
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
                localTime = time_.astimezone().strftime(date_format)

                sensors[sensorId]['date'] = localTime
                sensors[sensorId]['temp'] = tempStr
                sensors[sensorId]['battery'] = battery
                sensors[sensorId]['humidity'] = humidityStr

    print(blackText + "\n===================================================\n" +
          "Temp\tHumidty\tBattery\tLocation\tTime"
          )

    for s in sensors.values():
        if 'label' in s:
            sensorLabel = s['label']
            temp_ = s['temp']
            tempState = setColor(temp_, 'temp', sensorLabel)
            humidity_ = s['humidity']
            humidityState = setColor(humidity_, 'humidity', sensorLabel)
            battery_ = s['battery']
            batteryState = setColor(battery_, 'battery', sensorLabel, blueText)

            localTime = s['date']
            tempStr = tempState + temp_ + 'F'
            battery = batteryState + battery_ + '%'
            humidityStr = humidityState + humidity_ + '%'
            line = greenText + tempStr + '\t' + humidityStr + '\t' + battery + '\t' + blackText + sensorLabel + '\t' + localTime
            print(line)

    time.sleep(60)