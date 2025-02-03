import pyvisa
import time

pyvisa.log_to_screen = True

try:
    rm = pyvisa.ResourceManager()
    print("ok")
    sr4 = rm.open_resource('ASRL5::INSTR')

    sr4.write("*IDN?")
    time.sleep(0.1)
    
    Tset = 3 * 10**3  # Задаем значение предустановки счетчика T
    NumofPeriods = 5 # Задаем количество периодов сканирования
    
    sr4.write("CR\n") # CR Count reset
    sr4.write(f"CP2,{Tset}\n") # CP i, n 
    
    #sr4.write("DM2 1\n") # Устанавливаем режим работы дискриминатора 2 
    #sr4.write("NE 1\n")   # Устанавливаем режим окончания сканирования 

    sr4.write(f"NP {NumofPeriods}\n")  # Устанавливаем количество периодов сканирования
    #CS Count start, same as START key. 
    sr4.write("CR\n")
    sr4.write("CS\n") #.strip().splitlines()
    time.sleep(15)
    print("done")
    data_str=[]
    sr4.write("EA\n")
    for iter_i in range(NumofPeriods):
        data_str.append(list(map(int, sr4.read().rstrip().split(','))))
    print(f"fa: {data_str}") 

    # Разделяем полученную строку на отдельные значения
    try:
        data_points = [int(val) for val in data_str.split(',')]
        print(f"Data points: {data_points}")
    except ValueError:
       print("Error converting data to integers. Check for formatting problems in the response")
    sr4.write("CH\n")
    sr4.write("CR\n")
    # CH Count pause, same as STOP key while counting.# CR Count reset, same as STOP key pressed twice. 
    sr4.close()


except pyvisa.errors.VisaIOError as e:
    print(f"Error: {e}")
except ValueError as e:
    print(f"ValueError: {e}. Check connection and input parameters")
finally:
    if 'rm' in locals():
        rm.close()