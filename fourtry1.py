import pyvisa
import time
import tkinter as tk
from tkinter import messagebox
import threading
from queue import Queue

pyvisa.log_to_screen = True

class App:
    def __init__(self, root, data_filepath):
        self.root = root
        self.root.title("Данные с датчика")
        self.root.configure(bg="#282c34")
        self.data_filepath = data_filepath
        self.Tset = 3 * 10**3
        self.NumofPeriods = 5
        self.sr4 = None
        self.reading = False
        self.data_points = []
        self.data_queue = Queue()  # Очередь для передачи данных из потока в основной поток
        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg="#282c34")
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        control_frame = tk.Frame(main_frame, bg="#282c34")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        start_button = tk.Button(control_frame, text="Start", command=self.start_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        start_button.pack(side=tk.LEFT, padx=5)

        pause_button = tk.Button(control_frame, text="Pause", command=self.pause_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        pause_button.pack(side=tk.LEFT, padx=5)

        reset_button = tk.Button(control_frame, text="Reset", command=self.reset_scan,
                                    width=7, bg="#565656", fg="green", font=("Arial", 10))
        reset_button.pack(side=tk.LEFT, padx=5)

        self.text_area = tk.Text(main_frame, bg="#333842", fg="white", font=("Arial", 10))
        self.text_area.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    def start_scan(self):
      """Начинает сканирование в отдельном потоке."""
      if not self.reading:
        try:
          self.sr4 = self.connect_sr400()
          self.text_area.insert(tk.END, f"Start scanning for {self.NumofPeriods} periods.\n")
          self.reading = True
          thread = threading.Thread(target=self.perform_scan)
          thread.daemon = True # Daemon потоки завершаются при закрытии программы
          thread.start()
          self.update_gui() # Запускаем периодическое обновление GUI
        except Exception as e:
            messagebox.showerror("Error", f"Error starting scan: {e}")
            self.close_sr400()


    def perform_scan(self):
      """Выполняет сканирование в отдельном потоке."""
      try:
        self.setup_sr400()
        self.sr4.write("CS\n")
        data_str = self.sr4.query("FA\n").strip()
        self.data_queue.put(data_str)
      except Exception as e:
        self.data_queue.put(e) # Передаем ошибку в главный поток
      finally:
        self.reading = False
        self.close_sr400()


    def pause_scan(self):
       """Приостанавливает сканирование."""
       if self.reading:
          try:
             self.sr4.write("CH\n")
             self.data_queue.put("Scan paused.\n")
             self.reading = False
          except Exception as e:
            self.data_queue.put(e)

    def reset_scan(self):
      """Сбрасывает сканирование."""
      if self.sr4:
        try:
          self.sr4.write("CR\n")
          self.data_points = []
          self.data_queue.put("Scan reset.\n")
          self.reading = False
        except Exception as e:
          self.data_queue.put(e)

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
          self.sr4.write("CR\n")
          self.sr4.write(f"CP2,{self.Tset}\n")
          #self.sr4.write("DM2 1\n")
          #self.sr4.write("NE 1\n")
          self.sr4.write(f"NP {self.NumofPeriods}\n")
          time.sleep(0.1)
      except Exception as e:
          messagebox.showerror("Setup Error", f"Error setting up SR400: {e}")
          raise

    def close_sr400(self):
      """Закрывает соединение с прибором SR400."""
      if self.sr4:
        try:
           self.sr4.close()
        except Exception as e:
             messagebox.showerror("Closing Error", f"Error closing SR400 connection: {e}")
        finally:
           self.sr4 = None

    def update_gui(self):
      """Обновляет GUI в зависимости от данных из очереди."""
      while not self.data_queue.empty():
        data = self.data_queue.get()
        if isinstance(data, str):
            if "Scan paused" in data or "Scan reset" in data:
              self.text_area.insert(tk.END, data)
            else:
             try:
                self.data_points = [int(val) for val in data.split(',')]
                self.text_area.insert(tk.END, f"Data points: {self.data_points}\n")
             except ValueError:
                messagebox.showerror("Data Error", "Error converting data to integers. Check format")

        elif isinstance(data, Exception):
            messagebox.showerror("Error", f"Error in thread: {data}")
      self.root.after(100, self.update_gui)  # Проверяем очередь каждые 100 мс



root = tk.Tk()
data_file = "data.txt"
app = App(root, data_file)
root.mainloop()