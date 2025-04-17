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
pyvisa.log_to_screen = True 
try:
    rm=pyvisa.ResourceManager()#"@ni"
    print("ok")
    sr4 = rm.open_resource('ASRL5::INSTR')
    if ser.is_open:
        time.sleep(1)
        ser.write(b":w10=1,0.\r\n")#ch1 -1, ch2 ,1
        HZ=100000 #100hz
        time.sleep(0.01)
        ser.write(f":w13={HZ},0.\r\n".encode())#Hz
#еще наверное надо чтобы этот синхруназир с кода Включался
        time.sleep(0.001)
        ser.write(b":w11=3.\r\n")#амплитуда и офсет еще    
#The parameter i is 0,1,or 2 to select counter A,B, or T 
    time.sleep(0.02)
    sr4.write("CR\n")
    # time.sleep(0.1)
    Tset= 0.008*(10**7)
    sr4.write("CP2,"+str(Tset),"\n")
    time.sleep(0.02)
    HZ=Tset+0.002*(10**7)
    ser.write(f":w13={HZ},0.\r\n".encode())
    NumofPeriods=101
    sr4.write("NP"+" "+str(NumofPeriods))#N PERIODS=101 
    sr4.write("NE 0\n\r")#sr4.write("CS\n")
    for i in range(0,5):
        Scanlvl=-1.960 #PORT1 LVL=-1.960 V
        sr4.write("PL 1,"+" "+str(Scanlvl),"\n")
        ScanStep=0.010 #PORT1=SCAN ∆=+0.010 V sr4
        sr4.write("PY 1,"+" "+str(ScanStep)+"\n")
        sr4.write("CS\n")
        time.sleep(1.05)
        Scanlvl= -0.960 #PORT1 LVL=-1.960 V
        sr4.write("PL 1,"+" "+str(Scanlvl),"\n")
        ScanStep= -0.010 #PORT1=SCAN ∆=+0.010 V sr4
        sr4.write("PY 1,"+" "+str(ScanStep)+"\n")
        time.sleep(0.1)
        sr4.write("CR\n")
        sr4.write("CS\n")
        time.sleep(1.2)
        Scanlvl=-1.960 #PORT1 LVL=-1.960 V
        sr4.write("PL 1,"+" "+str(Scanlvl),"\n")
        sr4.write("CR\n")
        i+=1
    sr4.close()
except pyvisa.errors.VisaIOError as e:
    print(f"Error: {e}")

except ValueError as e:
    print(f"VError: {e}.not connected")
finally:
    if 'rm' in locals():
        ser.close() 
        rm.close()
# NP m Set Number of PERIODS in a scan to 1 <= m <= 2000.
# DT x Set DWELL time to 2E-3 <= x
# DY i,v Set DISC i scan step to -0.0200 <= v <= 0.0200 V.
# DL i,v Set DISC i LVL to -0.3000 <= v <= 0.3000 V.
# DZ i Read current DISC i LVL (during scan).
# PM k, j Set PORT k (1 or 2) to mode j; FIXED(0) or SCAN(1).
# PY k,v Set PORT k (1 or 2) scan step to -0.500 <= v <= 0.500 V.
# PL k,v Set PORT k (1 or 2) LVL to -10.000 <= v <= 10.000 V.
# NE j Set end of scan mode to mode j; START(1) or STOP (0)
# HZ=100000 #100hz
# ser.write(f":w13={HZ},0.\r\n")#Hz
# #еще наверное надо чтобы этот синхруназир с кода Включался
# ser.write(b":w11=3.\r\n")#амплитуда и офсет еще
# Tset= 100/HZ-0.002 
# sr4.write("CP2,"+str(Tset),"\n")
# NumofPeriods=101
# sr4.write("NP"+" "+str(NumofPeriods))#N PERIODS=101 
# sr4.write("NE 0\n\r")#sr4.write("CS\n")
# Scanlvl=-1.960 #PORT1 LVL=-1.960 V
# sr4.write("PY 1"+" "+str(Scanlvl),"\n")
# ScanStep=0.010 #PORT1=SCAN ∆=+0.010 V sr4
# sr4.write("PY 1"+" "+str(ScanStep),"\n")
# sr4.write("CS\n")
# Scanlvl=-0.960 #PORT1 LVL=-1.960 V
# sr4.write("PY 1"+" "+str(Scanlvl),"\n")
# ScanStep=-0.010 #PORT1=SCAN ∆=+0.010 V sr4
# sr4.write("PY 1"+" "+str(ScanStep),"\n")
# sr4.write("CR\n")
# sr4.write("CS\n")