import pyvisa
import time
import numpy as np
import re
#The parameter i is 0,1,or 2 to select counter A,B, or T 
pyvisa.log_to_screen = True 
try:
    rm=pyvisa.ResourceManager()#"@ni"
    print("ok")
    sr4 = rm.open_resource('ASRL5::INSTR')
    #inst = rm.open_resource('GPIB0::23::INSTR')#12 devise addres и я хз какой он
    #sr4.write("*IDN?")#реакция
    #sr4.write("PL 2,4\n")
    time.sleep(0.1)
    #Counter T preset to 10 counts T SET = 1E1  # CP i, n Set counter i preSET to 1 <= n <= 9E11.
    #Tset=3*10**3

    #sr4.write("CR","\n")
    #sr4.write("CP2,"+str(Tset),"\n")
    #Data points in scan = 100 N PERIODS = 100 # NN Read current count period number or scan position # NP m Set Number of PERIODS in a scan to 1 <= m <= 2000.
    Cur_Num_ofPeriods=sr4.query("NN")#ругается когда добавляю '\n'
    print(Cur_Num_ofPeriods,"Cur_Num_ofPeriods")
    NumofPeriods = int(Cur_Num_ofPeriods.rstrip())
    #NumofPeriods=5
   # sr4.write("NP"+" "+str(NumofPeriods))
      # NE j Set end of scan mode to mode j; START(1) or STOP (0). #CS Count start, same as START key.# CH Count pause, same as STOP key while counting.# CR Count reset, same as STOP key pressed twice. 
    # DM i,j Set DISC i to mode j; FIXED(0) or SCAN(1).  ?



    #sr4.write("DM2"+" "+"1","\n")
    #sr4.write("NE"+ " " +"1","\n")
    #reade=sr4.write("PZ"+" "+"2","\n")?
    #print(reade,"Read current PORT")?
    #sr4.write("FA","\n")
    #Cur_Num_ofPeriods=sr4.query("NN")
    #print(Cur_Num_ofPeriods,"lkjhgfd")
    print("Read current PORT")
    #sig = []
    
    #sig.append(sr4.query('QA 1'))
    #sig.append(sr4.query('QA 2'))
    #sig.append(sr4.query('QA 3'))
        #reade=sr4.query('QA 5')
    #print(sig)
    #print(type(sig[2]))
    #sr4.write("CS\n")
    #time.sleep(10)
    #fa = ['1']*2000



    sr4.write("CR\n")
    #sr4.write("CS\n") #.strip().splitlines()
    time.sleep(1)
    print("done")
    fa=sr4.query("QA ")
    # fa=[]
    # sr4.write("EA\n")
    # for iter_i in range(NumofPeriods):
    #     fa.append(list(map(int, sr4.read().rstrip().split(','))))

    print(repr(fa))
    # print('split')
    
    # fb=[]
    # time.sleep(0.1)
    # sr4.write("EB\n")
    # time.sleep(0.1)
    # for iter_i in range(NumofPeriods):
    #     fb.append(list(map(int, sr4.read().rstrip().split(','))))

    # print(*fb)
    # sr4.write("CR\n")

    #print(sig)
    #print(type(sig[2]))
    # time.sleep(0.1)
    #print(reade,"Read current PORT")
    #sr4.write("NE"+" "+"0","\n")
    # PZ k Read current PORT k (1 or 2) LVL (during scan).
    # DZ i Read current DISC i LVL (during scan). ?
    #response = inst.read()#'\n'
    #print(response)
    #sr4.write('CR')
    sr4.close()



except pyvisa.errors.VisaIOError as e:
    print(f"Error: {e}")

except ValueError as e:
    print(f"VError: {e}.not connected")
finally:
    if 'rm' in locals():
        rm.close()

# curPeriod= int(sr400.query("NN"))
#     print(curPeriod)
#this has to do with the syntax or the sr400 commands,1E7 = 1second
        #set the sr400 to that time period
        # sr400.write('CP2, ' + TSET)
    #Counter T to count triggers T = TRIG 
    #Counter T preset to 10 counts T SET = 1E1 # CP i, n Set counter i preSET to 1 <= n <= 9E11.
    #Data points in scan = 100 N PERIODS = 100 # NN Read current count period number or scan position # NP m Set Number of PERIODS in a scan to 1 <= m <= 2000.
    #AT N=STOP DWELL=2E-3 Single scan, 2 ms dwell SCAN AND DWELL
    # GM i,j Set GATE i to mode j; CW(0), FIXED(1), or SCAN(2). 
    # CI i,j Set counter i to input j; 10 MHz(0), INP 1(1), INP 2(2), TRIG(3). 

    # NE j Set end of scan mode to mode j; START(1) or STOP (0). 
#CS Count start, same as START key.
# CH Count pause, same as STOP key while counting.
# CR Count reset, same as STOP key pressed twice. 
    # DM i,j Set DISC i to mode j; FIXED(0) or SCAN(1).  ?
    # PZ k Read current PORT k (1 or 2) LVL (during scan).
    # DZ i Read current DISC i LVL (during scan). ?
#     QA Read last count in counter A.
# QB Read last count in counter B.
# QA m Read from scan buffer point m(1-2000) for counter A.
# QB m Read from scan buffer point m(1-2000) for counter B.
# EA Send entire counter A buffer.
# EB Send entire counter B buffer.
# ET Send entire counter A and B buffer.
# FA Start scan and send N PERIODS data points from counter A.
# FB Start scan and send N PERIODS data points from counter B.
# FT Start scan and send N PERIODS data points from both counters.
# XA Read current contents of counter A.
# XB Read current contents of counter B. 
