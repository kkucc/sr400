import tkinter as tk
import threading
import time
import csv
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Queue
import pyvisa
import numpy as np
import re

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SR400 Control and Data Acquisition")
        self.root.configure(bg="#282c34")

        # --- Constants ---
        self.BUTTON_WIDTH = 7
        self.LABEL_WIDTH = 5
        self.ENTRY_WIDTH = self.BUTTON_WIDTH
        self.FONT_STYLE = ("Arial", 10)
        self.BUTTON_BG = "#565656"
        self.BUTTON_FG = "green"
        self.ENTRY_BG = "#333842"
        self.ENTRY_FG = "grey"
        self.VALUE_BG = "#333842"
        self.VALUE_FG = "white"
        self.UPDATE_INTERVAL = 0.1
        self.PLOT_UPDATE_INTERVAL = 0.1
        self.MAX_DATA_POINTS = 100

        # --- GUI elements ---
        self.create_widgets()

        # --- Initialization ---
        self.data_list = []
        self.f_value = 0.0
        self.n_value = 0.0
        self.x_value = 0.0
        self.f_value_small = 0.0
        self.n_value_small = 0.0
        self.times = []
        self.f_values = []
        self.n_values = []
        self.x_values = []
        self.is_recording = False
        self.start_record = False 
        self.recording_file = None
        self.reading = False
        self.last_read_pos = 0
        self.last_plot_time = 0
        self.data_thread = None
        self.sr400 = None
        self.rm = None
        self.data_queue = Queue()

        # --- Connect to SR400 ---
        self.connect_to_sr400()

    def create_widgets(self):
        """Creates and places widgets."""
        # --- Buttons and values ---
        self.top_frame = tk.Frame(self.root, bg="#282c34")
        self.top_frame.pack(padx=5, pady=5, fill=tk.X)

        self.top_frame.columnconfigure(0, weight=1, uniform="all_elements")
        self.top_frame.columnconfigure(1, weight=1, uniform="all_elements")
        self.top_frame.columnconfigure(2, weight=1, uniform="all_elements")

        # Row 1: Start, F, N
        self.create_row_1()

        # Row 2: Stop, f, n
        self.create_row_2()

        # Row 3: Record, Tset, X
        self.create_row_3()

        # --- Plot ---
        self.fig = plt.figure(figsize=(8, 5), dpi=100, facecolor="grey")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#333842")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.ax.set_title('Data from SR400', fontsize=16)
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Values')
        self.ax.grid(True)

    def create_row_1(self):
        """Creates elements for the first row."""
        self.row1_frame = tk.Frame(self.top_frame, bg="#282c34")
        self.row1_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")

        self.start_button_frame = tk.Frame(self.row1_frame, bg=self.BUTTON_BG, bd=2, relief=tk.GROOVE)
        self.start_button_frame.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")

        self.start_button = tk.Button(self.start_button_frame, text="Start", command=self.start_reading,
                                    width=self.BUTTON_WIDTH, bg=self.BUTTON_BG, fg=self.BUTTON_FG,
                                    font=self.FONT_STYLE)
        self.start_button.pack(fill=tk.BOTH, expand=True)

        self.F_frame = tk.Frame(self.row1_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.F_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.F_label = tk.Label(self.F_frame, text="F:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.F_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.F_value_label = tk.Label(self.F_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                    bg=self.VALUE_BG)
        self.F_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

        self.N_frame = tk.Frame(self.row1_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.N_frame.grid(row=0, column=2, padx=5, pady=2, sticky="nsew")

        self.N_label = tk.Label(self.N_frame, text="N:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.N_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.N_value_label = tk.Label(self.N_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                    bg=self.VALUE_BG)
        self.N_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

    def create_row_2(self):
        """Creates elements for the second row."""
        self.row2_frame = tk.Frame(self.top_frame, bg="#282c34")
        self.row2_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        self.stop_button_frame = tk.Frame(self.row2_frame, bg=self.BUTTON_BG, bd=2, relief=tk.GROOVE)
        self.stop_button_frame.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")

        self.stop_button = tk.Button(self.stop_button_frame, text="Stop", command=self.stop_reading,
                                    width=self.BUTTON_WIDTH, bg=self.BUTTON_BG, fg=self.BUTTON_FG,
                                    font=self.FONT_STYLE)
        self.stop_button.pack(fill=tk.BOTH, expand=True)

        self.f_frame = tk.Frame(self.row2_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.f_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.f_label = tk.Label(self.f_frame, text="f:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.f_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.f_value_label = tk.Label(self.f_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                    bg=self.VALUE_BG)
        self.f_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

        self.n_frame = tk.Frame(self.row2_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.n_frame.grid(row=0, column=2, padx=3, pady=2, sticky="nsew")

        self.n_label = tk.Label(self.n_frame, text="n:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.n_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.n_value_label = tk.Label(self.n_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                    bg=self.VALUE_BG)
        self.n_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

    def create_row_3(self):
        """Creates elements for the third row."""
        self.row3_frame = tk.Frame(self.top_frame, bg="#282c34")
        self.row3_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")

        self.record_button_frame = tk.Frame(self.row3_frame, bg=self.BUTTON_BG, bd=2, relief=tk.GROOVE)
        self.record_button_frame.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")

        self.record_button = tk.Button(self.record_button_frame, text="Record", command=self.toggle_recording,
                                    width=self.BUTTON_WIDTH, bg=self.BUTTON_BG, fg=self.BUTTON_FG,
                                    font=self.FONT_STYLE)
        self.record_button.pack(fill=tk.BOTH, expand=True)

        self.coeff_frame = tk.Frame(self.row3_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.coeff_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.coeff_label = tk.Label(self.coeff_frame, text="Tset(s):", font=self.FONT_STYLE,
                                    fg=self.VALUE_FG, bg=self.VALUE_BG, width=self.LABEL_WIDTH+2)
        self.coeff_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.coeff_entry = tk.Entry(self.coeff_frame, font=self.FONT_STYLE, validate="key",
                                    bg=self.ENTRY_BG, fg=self.ENTRY_FG, width=self.BUTTON_WIDTH)
        self.coeff_entry.insert(0, "1")
        self.coeff_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.coeff_frame.columnconfigure(1, weight=1)
        self.coeff_entry['validatecommand'] = (self.coeff_entry.register(self.validate_input), '%P')

        self.x_frame = tk.Frame(self.row3_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.x_frame.grid(row=0, column=2, padx=5, pady=2, sticky="nsew")

        self.x_label = tk.Label(self.x_frame, text="X:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.x_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.x_value_label = tk.Label(self.x_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                    bg=self.VALUE_BG)
        self.x_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

        self.start_record_button = tk.Button(self.row3_frame, text="Record on Start: Off",
                                            bg="#565656", fg="white", font=self.FONT_STYLE,
                                            command=self.toggle_start_record)
        self.start_record_button.grid(row=0, column=3, padx=10, pady=5, sticky='w')

    def connect_to_sr400(self):
        """Connects to the SR400 instrument."""
        try:
            self.rm = pyvisa.ResourceManager()
            resources = self.rm.list_resources()
            
            
            # Find SR400 resource
            sr400_resource = None
            for resource in resources:
                if 'ASRL' in resource:  # You might need a more specific identifier
                    try:
                        temp_inst = self.rm.open_resource(resource)
                        # Check if it's an SR400 using *IDN? or a similar command
                        temp_inst.close()
                        sr400_resource = resource
                        break 
                    except Exception:
                        continue

            if sr400_resource:
                self.sr400 = self.rm.open_resource(sr400_resource)
                print(f"Connected to SR400 on {sr400_resource}")
                self.start_button.config(state=tk.NORMAL)
            else:
                print("SR400 not found.")
                self.start_button.config(state=tk.DISABLED)

        except pyvisa.errors.VisaIOError as e:
            print(f"Error connecting to SR400: {e}")
            self.start_button.config(state=tk.DISABLED)
        except ValueError as e:
            print(f"Error: {e}")
            self.start_button.config(state=tk.DISABLED)

    def validate_input(self, new_value):
        """Validates input in the Period field."""
        try:
            if new_value == "" or (10**(-9) <= float(new_value) <= 10**2):
                return True
            else:
                return False
        except ValueError:
            return False

    def toggle_start_record(self):
        """Handler for changing the state of the 'Record on Start' button."""
        self.start_record = not self.start_record
        if self.start_record:
            self.start_record_button.config(text="Record on Start: On", bg="green")
            
        else:
            self.start_record_button.config(text="Record on Start: Off", bg="#565656")
           

    def start_reading(self):
      """Starts the main data reading process."""
      if not self.reading:
          self.reading = True
          self.start_button.config(state=tk.DISABLED)
          self.stop_button.config(state=tk.NORMAL)

          if self.start_record:
            self.is_recording = True
            self.toggle_recording()
          
          # Start reading data
          if not self.data_thread or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.read_data)
            self.data_thread.daemon = True
            self.data_thread.start()

    def stop_reading(self):
        """Stops data reading and resets the plot."""
        if self.reading:
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.is_recording:
                self.toggle_recording()
        self.reset_data()

    def reset_data(self):
        """Resets all data and the plot."""
        self.data_queue.queue.clear()
        self.times = []
        self.f_values = []
        self.n_values = []
        self.x_values = []
        self.f_value = 0.0
        self.n_value = 0.0
        self.x_value = 0.0
        self.f_value_small = 0.0
        self.n_value_small = 0.0
        self.data_list = []
        self.last_read_pos = 0

        self.update_gui_values()
        self.update_plot()

    def read_data(self):
        """Reads data from the SR400 instrument."""
        while self.reading:
            try:
                if not self.sr400:
                    raise Exception("SR400 not connected")
                
                tset_str = self.coeff_entry.get()
                if not tset_str:
                  tset_str = "1"
                tset = float(tset_str)

                num_periods = int(1/tset)
                if num_periods < 1 :
                    num_periods = 1
                elif num_periods > 2000:
                    num_periods = 2000
                
                
                self.sr400.write(f"NP {num_periods}\n")
                #self.sr400.write(f"DT {tset}\n")
                self.sr400.write("CR\n")
                self.sr400.write("CS\n")
                time.sleep(tset * (num_periods + 1))

                fa = []
                self.sr400.write("EA\n")
                for _ in range(num_periods):
                    response = self.sr400.read().rstrip()
                    if response:
                        fa.append(list(map(int, response.split(','))))
                    else:
                        print("Empty response received")
                
                for row in fa:
                    self.data_queue.put(row)
                    
                self.sr400.write("CR\n")

            except Exception as e:
                print(f"Error reading data from SR400: {e}")
                time.sleep(self.UPDATE_INTERVAL)

            time.sleep(self.UPDATE_INTERVAL)

    def update_gui_values(self):
        """Updates values in the interface."""
        self.F_value_label.config(text=f"{self.f_value:.1f}")
        self.f_value_label.config(text=f"{self.f_value_small:.3f}")
        self.N_value_label.config(text=f"{self.n_value:.1f}")
        self.n_value_label.config(text=f"{self.n_value_small:.3f}")
        self.x_value_label.config(text=f"{self.x_value:.1f}")

    def update_plot(self):
        """Updates data on the plot."""
        current_time = time.time()
        if current_time - self.last_plot_time < self.PLOT_UPDATE_INTERVAL:
            return

        if len(self.times) > self.MAX_DATA_POINTS:
            self.times = self.times[-self.MAX_DATA_POINTS:]
            self.f_values = self.f_values[-self.MAX_DATA_POINTS:]
            self.n_values = self.n_values[-self.MAX_DATA_POINTS:]
            self.x_values = self.x_values[-self.MAX_DATA_POINTS:]

        self.ax.clear()
        self.ax.plot(self.times, self.f_values, label='F', linestyle='-', color='blue')
        self.ax.plot(self.times, self.n_values, label='N', linestyle='-', color='red')
        self.ax.plot(self.times, self.x_values, label='X', linestyle='-', color='green')
        self.ax.set_title('Data from SR400', fontsize=16)
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Values')
        self.ax.grid(True)
        self.ax.legend()
        self.canvas.draw()
        self.last_plot_time = current_time

    def process_data_queue(self):
      """Processes the data queue and updates the GUI."""
      while not self.data_queue.empty():
          row = self.data_queue.get()
          numbers = list(map(float, row))
          formatted_data = " ".join(map(str, numbers))

          self.data_list.append(formatted_data)
          if len(self.data_list) > 10:
              self.data_list.pop(0)

          current_time = datetime.datetime.now()

          try:
              coeff = float(self.coeff_entry.get())
          except ValueError:
              coeff = 0.1

          self.f_value = numbers[0] if len(numbers) > 0 else 0.0
          self.n_value = numbers[1] if len(numbers) > 1 else 0.0
          self.x_value = numbers[2] if len(numbers) > 2 else 0.0
          

          self.times.append(current_time)
          self.f_values.append(self.f_value)
          self.n_values.append(self.n_value)
          self.x_values.append(self.x_value)

          if self.is_recording:
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            with open(self.recording_file.name, "a") as rec_file:
               rec_file.write(f"{timestamp} - {formatted_data}\n")

          self.update_gui_values()

      self.update_plot()

    def start_gui_update(self):
        """Starts periodic GUI update."""
        self.process_data_queue()
        self.root.after(int(self.UPDATE_INTERVAL * 1000), self.start_gui_update)

    def toggle_recording(self):
        """Toggles data recording to a file."""
        if self.is_recording:
            self.is_recording = False
            self.record_button.config(text="Record")
            if self.recording_file:
                self.recording_file.close()
                self.recording_file = None
        else:
            self.is_recording = True
            try:
                filename = f"recorded_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                self.recording_file = open(filename, "w")
                self.record_button.config(text="Stop Rec")
            except Exception as e:
                print(f"Error creating file: {e}")
                self.is_recording = False
                self.record_button.config(text="Record")

    def on_closing(self):
      """Handles the closing of the application."""
      self.stop_reading() 
      if self.sr400:
          self.sr400.close()
      if self.rm:
          self.rm.close()
      self.root.destroy()

root = tk.Tk()
app = App(root)
root.protocol("WM_DELETE_WINDOW", app.on_closing)
root.mainloop()