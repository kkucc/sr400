import serial
import time

ser = serial.Serial('COM7', baudrate=9600, timeout=1)

ser.write(b"_mesd 1\r")
data1 = ser.readline().decode('utf-8').strip()
time.sleep(1)
ser.write(b"mp\r")
data2 = ser.readline().decode('utf-8')
data2 = ser.readline().decode('utf-8')
ser.write(b"mm 100000\rmgs\r")


data3 = ser.readlines()

ser.close()
print(data2, data3)