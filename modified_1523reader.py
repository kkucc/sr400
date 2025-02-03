import tkinter as tk
import threading
import time
import csv
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Queue

class App:
    def __init__(self, root, data_source=None):
        self.root = root
        self.root.title("Data from Sensor/Device")
        self.root.configure(bg="#282c34")
        self.data_source = data_source  # Can be a file path or a device object
        self.data_queue = Queue()

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
        self.times = []
        self.f_values = []
        self.n_values = []
        self.x_values = []
        self.is_recording = False
        self.start_record = False
        self.recording_file = None
        self.reading = False
        self.last_plot_time = 0
        self.data_thread = None

        # --- Data Source Handling ---
        if isinstance(self.data_source, str):  # File path
            self.file_available = self.check_file()
            if self.file_available:
                self.open_data_file()
                self.start_realtime_reading()
                self.start_gui_update()
            else:
                print(f"File {self.data_source} not found.")
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
        elif self.data_source:  # Device object (e.g., SR400)
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.start_gui_update()
        else:
            print("No data source provided.")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

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
        self.ax.set_title('Data', fontsize=16)
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

        # Tset (not used for file reading, but kept for consistency)
        self.coeff_frame = tk.Frame(self.row3_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.coeff_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.coeff_label = tk.Label(self.coeff_frame, text="Tset.s:", font=self.FONT_STYLE,
                                    fg=self.VALUE_FG, bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.coeff_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.coeff_entry = tk.Entry(self.coeff_frame, font=self.FONT_STYLE, validate="key",
                                    bg=self.ENTRY_BG, fg=self.ENTRY_FG, width=self.BUTTON_WIDTH, state='disabled')
        self.coeff_entry.insert(0, "0.01")
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

    def check_file(self):
        """Checks if the file exists."""
        try:
            with open(self.data_source, 'r'):
                return True
        except FileNotFoundError:
            return False

    def open_data_file(self):
        """Opens the data file for reading."""
        try:
            self.data_file = open(self.data_source, 'r')
            self.last_read_pos = 0
        except FileNotFoundError:
            print(f"Error: File {self.data_source} not found.")
            self.file_available = False

    def validate_input(self, new_value):
        """Validates the input value in the Period field."""
        try:
            if new_value == "" or (10**(-9) <= float(new_value) <= 10**2):
                return True
            else:
                return False
        except ValueError:
            return False

    def toggle_start_record(self):
        """Toggles the state of the 'Record on Start' button."""
        self.start_record = not self.start_record
        if self.start_record:
            self.start_record_button.config(text="Record on Start: On", bg="green")
            if self.reading: # Start recording if it is reading
                self.is_recording = True
                self.toggle_recording()
        else:
            self.start_record_button.config(text="Record on Start: Off", bg="#565656")

    def start_realtime_reading(self):
        """Starts a thread for reading data in real-time from a file."""
        if not self.data_thread or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.read_data_realtime)
            self.data_thread.daemon = True
            self.data_thread.start()

    def start_reading(self):
        """Starts the main data reading process (for file reading)."""
        if not self.reading:
            self.reading = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            if self.start_record:
              self.is_recording = True
              self.toggle_recording()

            if not self.data_thread or not self.data_thread.is_alive():
                if isinstance(self.data_source, str):
                    self.start_realtime_reading()
                else:
                    self.data_thread = threading.Thread(target=self.read_data_from_device)
                    self.data_thread.daemon = True
                    self.data_thread.start()

    def stop_reading(self):
        """Stops data reading and resets the plot (for both file and device)."""
        if self.reading:
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.is_recording:
                self.toggle_recording()
            if self.data_source and not isinstance(self.data_source, str):
                # Stop device-specific reading if applicable
                self.data_source.stop_acquisition()
                self.start_button.config(state=tk.NORMAL)
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
        self.data_list = []

        self.update_gui_values()
        self.update_plot()

    def read_data_realtime(self):
        """Reads data from a file in real-time."""
        while True:
            if not self.reading and isinstance(self.data_source, str):
                break
            try:
                self.data_file.seek(self.last_read_pos)
                if self.data_source.endswith('.csv'):
                    reader = csv.reader(self.data_file)
                else:
                    reader = csv.reader(self.data_file, delimiter=' ')
                new_lines = False
                for row in reader:
                    new_lines = True
                    if row:
                        self.data_queue.put(row)
                self.last_read_pos = self.data_file.tell()
                if not new_lines:
                    time.sleep(self.UPDATE_INTERVAL)
            except Exception as e:
                print(f"Error reading data (realtime): {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def start_data_acquisition(self):
        """Starts data acquisition from the connected device (e.g., SR400)."""
        if not self.data_thread or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.read_data_from_device)
            self.data_thread.daemon = True
            self.data_thread.start()

    def read_data_from_device(self):
        """Reads data from the connected device (e.g., SR400)."""
        while self.reading:
            if self.data_source:
                try:
                    data = self.data_source.acquire_data()
                    if data:
                        for row in data:
                            self.data_queue.put(row)
                except Exception as e:
                    print(f"Error reading data from device: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def update_gui_values(self):
        """Updates values in the interface."""
        self.F_value_label.config(text=f"{self.f_value:.1f}")
        self.N_value_label.config(text=f"{self.n_value:.1f}")
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
        self.ax.set_title('Data', fontsize=16)
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
        if hasattr(self, 'data_file') and self.data_file:
            self.data_file.close()
        self.root.destroy()