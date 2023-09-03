#!/usr/bin/python3.9

import os
import sys
import glob

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
            sensor = data[0].replace(":", "")
            sensors[sensor] = data[1]

print("Sensors", sensors)

print("Data Files in path", folder_path, ":")
files = list_txt_files(folder_path)
for file in files:
    filename = os.path.basename(file)
    parts = filename.split('-')
    sensorId = parts[1]
    if len(sensorId) == 12:
        measurement = read_last_line(file)
        if measurement:
            data = measurement.strip().split('\t')
            temp = data[1] + 'C'
            humidity = data[2] + '%'
            battery = data[3] + '%'
            print(sensorId, [temp, humidity, battery])
