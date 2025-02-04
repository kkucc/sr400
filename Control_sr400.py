import pyvisa
import time
import numpy as np
import sys

pyvisa.log_to_screen = True


class Sr400(object):
    sr4 = None
    numOfPeriods = 1
    t_set = None

    def __init__(self, n_counts, t_set):
        try:
            rm = pyvisa.ResourceManager()  # "@ni"
            print("ok")
            self.sr4 = rm.open_resource('ASRL5::INSTR')
            time.sleep(0.1)
            Cur_Num_ofPeriods = self.sr4.query("NN")  # ругается когда добавляю '\n'
            print(Cur_Num_ofPeriods, "Cur_Num_ofPeriods")
            self.numOfPeriods = n_counts
            print("Read current PORT")
            self.t_set = t_set
        except ValueError as error:
            print("порт не открылся")

    def write_com(self, command):
        self.sr4.write(f"{command.rstrip()}\n")

    def numperiod(self, n_counts):
        self.numOfPeriods = n_counts

    def tset(self, t_set):
        self.t_set = t_set

    def start_count(self):
        self.write_com("CR")
        self.write_com(f"CP 2 {self.t_set*10**7}")
        self.write_com(f"NP {self.numOfPeriods}")
        self.write_com("CS")

    def single_read(self, chanel='A'):
        print("done")
        fa = []
        self.sr4.write(f"E{chanel}")
        for iter_i in range(self.numOfPeriods):
            fa.append(list(map(int, self.sr4.read().rstrip().split(','))))
