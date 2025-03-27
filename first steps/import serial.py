import serial
import time
ser = serial.Serial(
    port='COM8',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
    ) 
#ser.open() #500 гц макс частота
try:
    if ser.is_open:
        # ser.open()
#         ser.write(b":w13=1000,0.\r\n")#Hz
#         time.sleep(0.02)
#         ser.write(b":w14=18,0.\r\n")#Hz
#         time.sleep(0.02)
#         print("hi11")
#         # ser.write(b":w12=6.\r\n")
#         # time.sleep(0.02)
# #ser.write(b":w55=1000000000.\r\n")#Period
#         ser.write(b":w14=100,0.\r\n")#a=0.7
#         time.sleep(0.02)
        ser.write(b":w60=0,0.\r\n")
        time.sleep(0.02)
        ser.write(b":w74=1,1.\r\n")
        time.sleep(0.01)
        ser.write(b":w10=1,1.\r\n")
        time.sleep(0.02)
        ser.write(b":w12=6.\r\n")
        time.sleep(0.1)
        ser.write(b":w11=6.\r\n")
        time.sleep(0.1)
        offset2=0
        while offset2<101:
            # aplit2=1000
            # ser.write(f":w16={aplit2}.\r\n".encode())
            APL = 0.005
            offset = 0
            n = 0
            while n < 100:
                # ser.write(f":w15={1000*APL}.\r\n".encode())
                # time.sleep(APL+0.001)
                # ser.write(b":w11=10.\r\n")  # 2
                # time.sleep(2*(APL+0.001))
                print("hi111")
                w17_value = 950 + offset
                ser.write(f":w17={w17_value}.\r\n".encode())
                time.sleep(0.005)
                offset += 1

                n += 1
            time.sleep(0.005)
            offset2+=1
            ser.write(f":w18={900+offset2}.\r\n".encode())
            time.sleep(0.005)
            offset = 0
            n = 0
            while n < 100:
                # ser.write(f":w15={1000*APL}.\r\n".encode())
                # time.sleep(APL+0.001)
                # ser.write(b":w11=11.\r\n")  # 2
                # time.sleep(2*(APL+0.001))
                print("hi112")
                w17_value = 1050 - offset
                ser.write(f":w17={w17_value}.\r\n".encode())
                time.sleep(0.005)

                offset += 1

                n += 1
            time.sleep(0.005)
            offset2+=1
            ser.write(f":w18={900+offset2}.\r\n".encode())
            time.sleep(0.005)
        ser.write(b":w10=0,0.\r\n")        
        # p=250
        # offset=0
        # for i in range(p):
        #     w17_value = 1160 + offset
        #     ser.write(f":w17={w17_value}.\r\n".encode())
        #     offset-=1
        #     time.sleep(0.1)
        # ser.write(b":w14=10,0.\r\n")#Hz
        # ser.write(b":w10=0,0.\r\n")
        # ser.write(b":w15=200.\r\n")#A*0.001
        # time.sleep(0.002)
        # ser.write(b":w11=10.\r\n")#1
        # time.sleep(0.2)
        # ser.write(b":w17=1050.\r\n")# 1000 - 0v offset
        # time.sleep(0.7)
        # ser.write(b":w17=1080.\r\n")
        # time.sleep(0.7)
        # ser.write(b":w17=1107.\r\n")
        # time.sleep(0.7)
        # ser.write(b":w16=1000.\r\n")
        # time.sleep(0.002)
        # ser.write(b":w12=11.\r\n")#2
        # time.sleep(0.002)
        # print("hi")
        # time.sleep(2)
        # ser.write(b":w15=200.\r\n")
        # time.sleep(0.002)
        # ser.write(b":w11=11.\r\n")
#         time.sleep(0.2)
#         response = ser.read_all().decode().strip()
        # print(response)
except Exception as e:
    print(f"Error: {e}")
finally:
    if ser.is_open:
        ser.close()     