import pyvisa
import time
import numpy as np
import sys

pyvisa.log_to_screen = True


class Sr400(object):
    sr4 = None
    numOfPeriods = 1
    t_set = None
    dwel_time = None

    def __init__(self, n_counts, t_set, dwel_time):
        """:param n_counts - количество усреднения, t_set - время накопления"""
        try:
            self.rm = pyvisa.ResourceManager()  # "@ni"
            print("ok")
            self.sr4 = rm.open_resource('ASRL5::INSTR')
            time.sleep(0.1)
            Cur_Num_ofPeriods = self.sr4.query("NN")  # ругается когда добавляю '\n'
            print(Cur_Num_ofPeriods, "Cur_Num_ofPeriods")
            self.numOfPeriods = n_counts
            self.t_set = t_set
            self.dwel_time = dwel_time
            print("Read current PORT")
            self.write_com(f"CP 2 {self.t_set * 10 ** 7}")
            self.write_com(f"NP {self.numOfPeriods}")

        except ValueError as error:
            print("порт не открылся")

    def write_com(self, command):
        self.sr4.write(f"{command.rstrip()}\n")

    def numperiod(self, n_counts):
        self.numOfPeriods = n_counts
        self.write_com(f"NP {self.numOfPeriods}")

    def tset(self, t_set):
        self.t_set = t_set
        self.write_com(f"CP2,{self.t_set * 10 ** 7}")

    def start_count(self):
        self.write_com("CR")
        self.write_com(f"CP2,{int(self.t_set * 10 ** 7)}")
        self.write_com(f"NP {self.numOfPeriods}")
        self.write_com("CS")

    def single_read(self, chanel='A'):
        f = []
        self.sr4.write(f"E{chanel}")
        for iter_i in range(self.numOfPeriods):
            f.append(list(map(int, self.sr4.read().rstrip().split(','))))
        return f

    def close(self):
        self.sr4.close()
        self.rm.close()
