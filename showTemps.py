#!/usr/bin/python3.9

import os
import sys
import glob
import time
from datetime import datetime, timezone

date_format = "%Y-%m-%d %H:%M:%S"

def list_txt_files(folder_path):
    return glob.glob(f"{folder_path}/*.txt")

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return lines
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def read_last_line(file_path):
    lines = read_file(file_path)
    if lines:
        return lines[-1] if lines else None
    return None

def convert_celsius_to_fahrenheit(celsius):
    fahrenheit = (celsius * 1.8) + 32
    return fahrenheit

folder_path = "/var/log/goveebttemplogger"
if len(sys.argv) > 1:
    folder_path = sys.argv[1]

sensorsData = read_file("/var/www/html/goveebttemplogger/gvh-titlemap.txt")
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
files = list_txt_files(folder_path)

while True:
    for file in files:
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
            measurement = read_last_line(file)
            if measurement:
                data = measurement.strip().split('\t')
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

    print("\n===================================================\n")

    for s in sensors.values():
        localTime = s['date']
        tempStr = s['temp']
        battery = s['battery']
        humidityStr = s['humidity']
        sensorLabel = s['label']
        line = tempStr + 'F\t' + humidityStr + '%\t' + battery + '%\t' + sensorLabel + '\t' + localTime
        print(line)

    time.sleep(60)