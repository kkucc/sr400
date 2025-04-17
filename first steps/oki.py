import serial
import time
import pyvisa
import re
ser = serial.Serial(
    port='COM8',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
    ) 
try:
    if ser.is_open:
        time.sleep(1)
        ser.write(b":w10=1,1.\r\n")
except Exception as e:
    print(f"Error: {e}")
finally:
    if ser.is_open:
        ser.close()     
#The parameter i is 0,1,or 2 to select counter A,B, or T 
pyvisa.log_to_screen = True 
try:
    rm=pyvisa.ResourceManager()#"@ni"
    print("ok")
    sr4 = rm.open_resource('ASRL5::INSTR')
    sr4.write("CR\n")
    time.sleep(0.1)
    sr4.write("CS\n")
    time.sleep(10)
    sr4.write("CR\n")
    sr4.close()
except pyvisa.errors.VisaIOError as e:
    print(f"Error: {e}")

except ValueError as e:
    print(f"VError: {e}.not connected")
finally:
    if 'rm' in locals():
        rm.close()
