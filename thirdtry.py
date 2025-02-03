import pyvisa
import time
import tkinter as tk
from tkinter import messagebox

pyvisa.log_to_screen = True

class App:
    def __init__(self, root, data_filepath):
        self.root = root
        self.root.title("Данные с датчика")
        self.root.configure(bg="#282c34")
        self.data_filepath = data_filepath
        self.Tset = 0.01 * 10**7  # Задаем значение предустановки счетчика T
        self.NumofPeriods = 2000  # Задаем количество периодов сканирования
        self.sr4 = None
        self.reading = False
        self.data_points = []
        self.create_widgets()
    def create_widgets(self):
      # Основной фрейм
        main_frame = tk.Frame(self.root, bg="#282c34")
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
      # Фрейм для кнопок управления
        control_frame = tk.Frame(main_frame, bg="#282c34")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5)


        # Кнопка "Start"
        start_button = tk.Button(control_frame, text="Start", command=self.start_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        start_button.pack(side=tk.LEFT, padx=5)

        # Кнопка "Pause"
        pause_button = tk.Button(control_frame, text="Pause", command=self.pause_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        pause_button.pack(side=tk.LEFT, padx=5)

        # Кнопка "Reset"
        reset_button = tk.Button(control_frame, text="Reset", command=self.reset_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        reset_button.pack(side=tk.LEFT, padx=5)

        #Текстовая область для вывода
        self.text_area = tk.Text(main_frame, bg="#333842", fg="white", font=("Arial", 10))
        self.text_area.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
      
    def start_scan(self):
      """Начинает сканирование."""
      if not self.reading:
        try:
          self.sr4 = self.connect_sr400()
          self.setup_sr400()
          self.text_area.insert(tk.END, f"Start scanning for {self.NumofPeriods} periods.\n")
          self.sr4.write("CS\n")
          self.reading = True
          self.get_data_sr400()
        except Exception as e:
          messagebox.showerror("Error", f"Error starting scan: {e}")
          self.close_sr400()


    def pause_scan(self):
      """Приостанавливает сканирование."""
      if self.reading:
          try:
            self.sr4.write("CH\n")
            self.text_area.insert(tk.END, "Scan paused.\n")
            self.reading = False
          except Exception as e:
            messagebox.showerror("Error", f"Error pausing scan: {e}")

    def reset_scan(self):
      """Сбрасывает сканирование."""
      if self.sr4:
        try:
          self.sr4.write("CR\n")
          self.text_area.insert(tk.END, "Scan reset.\n")
          self.data_points = []
          self.reading = False
        except Exception as e:
            messagebox.showerror("Error", f"Error resetting scan: {e}")

    def connect_sr400(self):
      """Подключается к прибору SR400."""
      try:
        rm = pyvisa.ResourceManager()
        sr4 = rm.open_resource('ASRL5::INSTR')
        sr4.write("*IDN?\n")
        time.sleep(0.1)
        return sr4
      except pyvisa.errors.VisaIOError as e:
        messagebox.showerror("Connection Error", f"Error connecting to SR400: {e}")
        raise

    def setup_sr400(self):
      """Устанавливает параметры прибора SR400."""
      try:
          self.sr4.write("CR\n")  # Reset count
          self.sr4.write(f"CP2,{self.Tset}\n")  # Set preset
          self.sr4.write(f"NP {self.NumofPeriods}\n")  # Set number of periods
          time.sleep(0.1)
      except Exception as e:
          messagebox.showerror("Setup Error", f"Error setting up SR400: {e}")
          raise
    def get_data_sr400(self):
      """Получает данные с прибора SR400."""
      try:
        self.sr4.write("CR\n")
        self.sr4.write("CS\n") #.strip().splitlines()
        time.sleep(15)
        print("done")
        data_str=[]
        self.sr4.write("EA\n")
        for iter_i in range(self.NumofPeriods):
          data_str.append(list(map(int, self.sr4.read().rstrip().split(','))))
        self.sr4.write("CR\n")
        print(f"Raw data: {data_str}")
        try:
            self.data_points = data_str
            self.text_area.insert(tk.END, f"Data points: {self.data_points}\n")
        except ValueError:
              messagebox.showerror("Data Error", "Error converting data to integers. Check format")
      except Exception as e:
        messagebox.showerror("Data Error", f"Error getting data from SR400: {e}")
      finally:
        self.reading = False
        self.close_sr400()
        

    def close_sr400(self):
      """Закрывает соединение с прибором SR400."""
      if self.sr4:
        try:
          self.sr4.close()
        except Exception as e:
            messagebox.showerror("Closing Error", f"Error closing SR400 connection: {e}")
        finally:
          self.sr4 = None


root = tk.Tk()
data_file = "data.txt"  # Имя файла с данными
app = App(root, data_file)
root.mainloop()