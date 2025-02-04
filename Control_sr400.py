import pyvisa
import time
import numpy as np
import sys

pyvisa.log_to_screen = True


class Sr400(object):
    sr4 = None
    numOfPeriods = 1

    def __init__(self, n_counts):
        try:
            rm = pyvisa.ResourceManager()  # "@ni"
            print("ok")
            self.sr4 = rm.open_resource('ASRL5::INSTR')
            time.sleep(0.1)
            Cur_Num_ofPeriods = self.sr4.query("NN")  # ругается когда добавляю '\n'
            print(Cur_Num_ofPeriods, "Cur_Num_ofPeriods")
            self.numOfPeriods = n_counts
            print("Read current PORT")
        except ValueError as error:
            print("порт не открылся")

    def write_com(self, command):
        self.sr4.write(f"{command.rstrip()}\n")

    def numperiod(self, n_counts):
        self.numOfPeriods = n_counts

    def single_read(self, chanel='A'):
        self.write_com("CR\n")
        self.write_com("CS\n")  # .strip().splitlines()
        time.sleep(10)
        print("done")
        fa = []
        self.sr4.write(f"E{chanel}\n")
        for iter_i in range(self.numOfPeriods):
            fa.append(list(map(int, self.sr4.read().rstrip().split(','))))
