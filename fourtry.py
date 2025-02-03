import asyncio
import pyvisa
import time
import tkinter as tk
from tkinter import messagebox

class App:
    def __init__(self, root, data_filepath):
        self.root = root
        self.root.title("Данные с датчика")
        self.root.configure(bg="#282c34")
        self.data_filepath = data_filepath
        self.Tset = 0.01 * 10**7
        self.NumofPeriods = 2000
        self.sr4 = None
        self.reading = False
        self.data_points = []
        self.data_queue = asyncio.Queue()
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

    async def start_scan(self):
      """Запускает сканирование асинхронно."""
      if not self.reading:
        try:
          self.sr4 = await self.connect_sr400()
          self.text_area.insert(tk.END, f"Start scanning for {self.NumofPeriods} periods.\n")
          self.reading = True
          asyncio.create_task(self.perform_scan()) # запуск асинхронной функции
          self.update_gui()
        except Exception as e:
          messagebox.showerror("Error", f"Error starting scan: {e}")
          await self.close_sr400()

    async def perform_scan(self):
      """Выполняет сканирование асинхронно."""
      try:
        await self.setup_sr400()
        await self.sr4.write("CS\n")
        data_str = await self.sr4.query("FA\n")
        await self.data_queue.put(data_str.strip())

      except Exception as e:
        await self.data_queue.put(e)
      finally:
        self.reading = False
        await self.close_sr400()

    async def pause_scan(self):
       """Приостанавливает сканирование асинхронно."""
       if self.reading:
          try:
             await self.sr4.write("CH\n")
             await self.data_queue.put("Scan paused.\n")
             self.reading = False
          except Exception as e:
            await self.data_queue.put(e)

    async def reset_scan(self):
      """Сбрасывает сканирование асинхронно."""
      if self.sr4:
        try:
          await self.sr4.write("CR\n")
          self.data_points = []
          await self.data_queue.put("Scan reset.\n")
          self.reading = False
        except Exception as e:
           await self.data_queue.put(e)

    async def connect_sr400(self):
        """Подключается к прибору SR400 асинхронно."""
        try:
            rm = pyvisa.ResourceManager()
            sr4 = await rm.open_resource('ASRL5::INSTR')
            await sr4.write("*IDN?\n")
            await asyncio.sleep(0.1)
            return sr4
        except pyvisa.errors.VisaIOError as e:
            messagebox.showerror("Connection Error", f"Error connecting to SR400: {e}")
            raise
    async def setup_sr400(self):
      """Устанавливает параметры прибора SR400 асинхронно."""
      try:
          await self.sr4.write("CR\n")
          await self.sr4.write(f"CP2,{self.Tset}\n")
          await asyncio.sleep(15)
          print("done")
          fa=[]
          await self.sr4.write("EA\n")
          for iter_i in range(self.NumofPeriods):
            fa.append(list(map(int, self.sr4.read().rstrip().split(','))))
          await self.sr4.write(f"NP {self.NumofPeriods}\n")
          await asyncio.sleep(0.1)
      except Exception as e:
          messagebox.showerror("Setup Error", f"Error setting up SR400: {e}")
          raise
    async def close_sr400(self):
        """Закрывает соединение с прибором SR400 асинхронно."""
        if self.sr4:
           try:
             await self.sr4.close()
           except Exception as e:
               messagebox.showerror("Closing Error", f"Error closing SR400 connection: {e}")
           finally:
              self.sr4 = None

    def update_gui(self):
      """Обновляет GUI в зависимости от данных из очереди."""
      async def update():
         while not self.data_queue.empty():
            data = await self.data_queue.get()
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
                messagebox.showerror("Error", f"Error in async function: {data}")
         self.root.after(100, lambda: asyncio.create_task(update()))
      asyncio.create_task(update())

async def main():
    root = tk.Tk()
    data_file = "data.txt"
    app = App(root, data_file)
    root.mainloop()

if __name__ == "__main__":
    asyncio.run(main())