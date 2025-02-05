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
        self.experiment_data = {}  # To store data for each experiment
        self.current_experiment_num = 0
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
        self.num_experiments = 0  # Default value, changed by entry
        # --- GUI elements ---
        self.create_widgets()

        # --- Initialization ---
        self.data_list = []
        self.a_value = 0.0
        self.b_value = 0.0
        self.qa_value = 0.0
        self.qb_value = 0.0
        self.x_value = 0.0  # Cumulative average
        self.times = []
        self.a_values = []
        self.b_values = []
        self.x_values = [] # List to store average values
        self.qa_values = []
        self.qb_values = []
        self.num_data_points = 0 # Counter for data points

        self.start_time = 0

        self.is_recording = False
        self.start_record = False
        self.recording_file = None
        self.reading = False
        self.last_plot_time = 0
        self.data_thread = None
        self.qa_thread = None
        self.qb_thread = None
        self.sr400_lock = threading.Lock()
        self.qa_active = False  # Флаг активности для QA
        self.qb_active = False  # Флаг активности для QB
        self.is_between_experiments = False  # Флаг, что сейчас промежуток между экспериментами

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
            self.qa_active = True
            self.qb_active = True
            self.start_qa_update()
            self.start_qb_update()

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

        # Row 1: Start, A, B
        self.create_row_1()

        # Row 2: Stop, QA, QB
        self.create_row_2()

        # Row 3: Record, M, Avg
        self.create_row_3()

        # --- Plot ---
        self.fig = plt.figure(figsize=(8, 5), dpi=100, facecolor="grey")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#333842")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.ax.set_title('Data', fontsize=16)
        self.ax.set_xlabel('Index')  # Изменено на Index
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

        self.A_frame = tk.Frame(self.row1_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.A_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.A_label = tk.Label(self.A_frame, text="A:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.A_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.A_value_label = tk.Label(self.A_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                     bg=self.VALUE_BG)
        self.A_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

        self.B_frame = tk.Frame(self.row1_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.B_frame.grid(row=0, column=2, padx=5, pady=2, sticky="nsew")

        self.B_label = tk.Label(self.B_frame, text="B:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.B_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.B_value_label = tk.Label(self.B_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                     bg=self.VALUE_BG)
        self.B_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

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

        self.QA_frame = tk.Frame(self.row2_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.QA_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.QA_label = tk.Label(self.QA_frame, text="QA:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.QA_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.QA_value_label = tk.Label(self.QA_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                     bg=self.VALUE_BG)
        self.QA_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

        self.QB_frame = tk.Frame(self.row2_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.QB_frame.grid(row=0, column=2, padx=3, pady=2, sticky="nsew")

        self.QB_label = tk.Label(self.QB_frame, text="QB:", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.QB_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.QB_value_label = tk.Label(self.QB_frame, text="0.0", font=self.FONT_STYLE, fg=self.VALUE_FG,
                                     bg=self.VALUE_BG)
        self.QB_value_label.grid(row=0, column=1, padx=20, pady=2, sticky="ew")

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

        # Number of experiments
        self.m_frame = tk.Frame(self.row3_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.m_frame.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")

        self.m_label = tk.Label(self.m_frame, text="M:", font=self.FONT_STYLE,
                                    fg=self.VALUE_FG, bg=self.VALUE_BG, width=self.LABEL_WIDTH)
        self.m_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.m_entry = tk.Entry(self.m_frame, font=self.FONT_STYLE, validate="key",
                                    bg=self.ENTRY_BG, fg=self.ENTRY_FG, width=self.BUTTON_WIDTH)
        self.m_entry.insert(0, "1")
        self.m_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.m_frame.columnconfigure(1, weight=1)
        self.m_entry['validatecommand'] = (self.m_entry.register(self.validate_m_input), '%P')

        self.x_frame = tk.Frame(self.row3_frame, bg=self.VALUE_BG, bd=2, relief=tk.GROOVE)
        self.x_frame.grid(row=0, column=2, padx=5, pady=2, sticky="nsew")

        self.x_label = tk.Label(self.x_frame, text="Avg:", font=self.FONT_STYLE, fg=self.VALUE_FG,
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
            if new_value == "" or (0.000000001 <= float(new_value) <= 10**2):
                return True
            else:
                return False
        except ValueError:
            return False

    def validate_m_input(self, new_value):
        """Validates the input value in the M field."""
        try:
            if new_value == "" or (0 < int(new_value) <= 1000):
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
                if not self.is_recording:
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
            self.current_experiment_num = 0
            self.reading = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            if self.start_record and not self.is_recording:
                self.is_recording = True
                self.toggle_recording()

            try:
                self.num_experiments = int(self.m_entry.get())
            except ValueError:
                print("Invalid value for M. Using default value of 1.")
                self.num_experiments = 1

            if not self.data_thread or not self.data_thread.is_alive():
                if isinstance(self.data_source, str):
                    self.start_realtime_reading()
                else:
                    self.start_time = time.time()  # Reset start time for each experiment
                    self.times = []
                    self.a_values = []
                    self.b_values = []
                    self.x_values = []
                    # Опрос QA и QB не запускаем, т.к. начинается эксперимент
                    self.data_thread = threading.Thread(target=self.read_data_from_device)
                    self.data_thread.daemon = True
                    self.data_thread.start()

    def stop_reading(self):
        """Stops data reading (for both file and device)."""
        if self.reading:
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.is_recording:
                self.toggle_recording()

            if self.data_source and not isinstance(self.data_source, str):
                # Опрос QA и QB не останавливаем, т.к. он должен работать в простое
                self.data_source.stop_acquisition()
                self.start_button.config(state=tk.NORMAL)

    def reset_data(self):
        """Resets all data and the plot."""
        self.data_queue.queue.clear()
        self.times = []
        self.a_values = []
        self.b_values = []
        self.x_values = []
        self.a_value = 0.0
        self.b_value = 0.0
        self.x_value = 0.0
        self.data_list = []
        self.num_data_points = 0

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
                    self.current_experiment_num += 1
                    print(f"Experiment {self.current_experiment_num} completed.")
                    if data:
                        for row in data:
                            self.data_queue.put(row)

                    if self.current_experiment_num >= self.num_experiments:
                        self.stop_reading()
                        print("All experiments completed.")
                        # Запускаем опрос QA и QB после завершения всех экспериментов
                        self.qa_active = True
                        self.qb_active = True
                        self.start_qa_update()
                        self.start_qb_update()
                    else:
                        # Пауза между экспериментами
                        self.is_between_experiments = True
                        time.sleep(5)  # Пауза 5 секунд между экспериментами
                        self.is_between_experiments = False

                except Exception as e:
                    print(f"Error reading data from device: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def update_gui_values(self):
        """Updates values in the interface."""
        self.A_value_label.config(text=f"{self.a_value:.1f}")
        self.B_value_label.config(text=f"{self.b_value:.1f}")
        self.QA_value_label.config(text=f"{self.qa_value:.1f}")
        self.QB_value_label.config(text=f"{self.qb_value:.1f}")
        self.x_value_label.config(text=f"{self.x_value:.4f}") # Display with more precision

    def update_plot(self):
        """Updates data on the plot."""
        current_time = time.time()
        if current_time - self.last_plot_time < self.PLOT_UPDATE_INTERVAL:
            return

        if not self.start_time and self.reading:
          return

        if len(self.a_values) > self.MAX_DATA_POINTS:
            # self.times = self.times[-self.MAX_DATA_POINTS:] # times не нужен тк используется index
            self.a_values = self.a_values[-self.MAX_DATA_POINTS:]
            self.b_values = self.b_values[-self.MAX_DATA_POINTS:]
            self.x_values = self.x_values[-self.MAX_DATA_POINTS:]

        self.ax.clear()
        # Изменено: используем индексы вместо времени
        indices = list(range(len(self.a_values)))
        if indices:
          self.ax.plot(indices, self.a_values, label='A', linestyle='-', color='blue')
          self.ax.plot(indices, self.b_values, label='B', linestyle='-', color='red')
          self.ax.plot(indices, self.x_values, label='Avg', linestyle='-', color='green')

        self.ax.set_title('Data', fontsize=16)
        self.ax.set_xlabel('Index')
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

            current_time = time.time()  # datetime.datetime.now()

            self.a_value = numbers[0] if len(numbers) > 0 else 0.0
            self.b_value = numbers[1] if len(numbers) > 1 else 0.0
            
            # Corrected average calculation:
            self.num_data_points += 1
            self.x_value = self.x_value + ((self.a_value + self.b_value) - self.x_value) / self.num_data_points
            self.x_values.append(self.x_value)

            self.times.append(current_time)
            self.a_values.append(self.a_value)
            self.b_values.append(self.b_value)
            # Изменено: обновляем значение на графике (x_values) и в интерфейсе (x_value_label)

            if self.is_recording:
                # timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")
                timestamp = str(current_time)
                with open(self.recording_file.name, "a") as rec_file:
                    rec_file.write(f"{timestamp} - {formatted_data}\n")

            self.update_gui_values()

        self.update_plot()

    def update_qa_continuously(self):
        """Continuously updates the QA value from the device."""
        while True:
            if self.data_source and self.qa_active and not self.is_between_experiments:  # опрос только когда qa_active=true и не в промежутке
                try:
                    with self.sr400_lock:
                        time.sleep(2)
                        self.qa_value = float(self.data_source.sr400.query("QA").strip('\r\n'))
                        time.sleep(2)
                        self.update_gui_values()
                except Exception as e:
                    print(f"Error reading QA value: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def update_qb_continuously(self):
        """Continuously updates the QB value from the device."""
        while True:
            if self.data_source and self.qb_active and not self.is_between_experiments:
                try:
                    with self.sr400_lock:
                        time.sleep(2)
                        self.qb_value = float(self.data_source.sr400.query("QB").strip('\r\n'))
                        time.sleep(2)
                        self.update_gui_values()
                except Exception as e:
                    print(f"Error reading QB value: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def start_qa_update(self):
        """Starts a separate thread for updating QA value."""
        if not self.qa_thread or not self.qa_thread.is_alive():
            self.qa_thread = threading.Thread(target=self.update_qa_continuously)
            self.qa_thread.daemon = True
            self.qa_thread.start()

    def start_qb_update(self):
        """Starts a separate thread for updating QB value."""
        if not self.qb_thread or not self.qb_thread.is_alive():
            self.qb_thread = threading.Thread(target=self.update_qb_continuously)
            self.qb_thread.daemon = True
            self.qb_thread.start()

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