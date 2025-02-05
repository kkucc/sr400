import tkinter as tk
import threading
import time
import csv
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Queue
import numpy as np  # Import numpy

class App:
    def __init__(self, root, data_source=None):
        self.root = root
        self.root.title("Data from Sensor/Device")
        self.root.configure(bg="#282c34")
        self.data_source = data_source
        self.data_queue = Queue()
        self.experiment_data = {}
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
        self.PLOT_UPDATE_INTERVAL = 0.1 # Unused now
        self.MAX_DATA_POINTS = 100
        self.num_experiments = 0
        # --- GUI elements ---
        self.create_widgets()

        # --- Initialization ---
        self.data_list = []
        self.a_value = 0.0
        self.b_value = 0.0
        self.qa_value = 0.0
        self.qb_value = 0.0
        self.x_value = 0.0  # Average of the *entire* experiment
        self.times = []
        self.a_values = []
        self.b_values = []
        self.x_values = [] # Now stores the average *per experiment*
        self.qa_values = []
        self.qb_values = []
        self.experiment_averages = [] # To store averages for plotting

        self.start_time = 0  # Keep track of the *overall* start time

        self.is_recording = False
        self.start_record = False  # "Record on Start" flag
        self.recording_file = None
        self.reading = False
        self.last_plot_time = 0 # Unused now
        self.data_thread = None
        self.qa_thread = None
        self.qb_thread = None
        self.sr400_lock = threading.Lock() # Lock for SR400 access
        self.qa_active = False
        self.qb_active = False
        self.is_between_experiments = False # Flag for experiment pause

        # --- Data Source Handling ---
        if isinstance(self.data_source, str):
            self.file_available = self.check_file()
            if self.file_available:
                self.open_data_file()
                self.start_realtime_reading()
                self.start_gui_update()
            else:
                print(f"File {self.data_source} not found.")
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
        elif self.data_source:
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.start_gui_update()  # Start the GUI update loop
            self.qa_active = True # QA/QB should run continuously
            self.qb_active = True
            self.start_qa_update()
            self.start_qb_update()
        else:
            print("No data source provided.")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def create_widgets(self):
        """Creates and places widgets."""
        self.top_frame = tk.Frame(self.root, bg="#282c34")
        self.top_frame.pack(padx=5, pady=5, fill=tk.X)
        self.top_frame.columnconfigure(0, weight=1, uniform="all_elements")
        self.top_frame.columnconfigure(1, weight=1, uniform="all_elements")
        self.top_frame.columnconfigure(2, weight=1, uniform="all_elements")
        self.create_row_1()
        self.create_row_2()
        self.create_row_3()
        self.fig = plt.figure(figsize=(8, 5), dpi=100, facecolor="grey")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#333842")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.ax.set_title('Data', fontsize=16)
        self.ax.set_xlabel('Experiment Index')
        self.ax.set_ylabel('Average Value')
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
            self.last_read_pos = 0  # Track the last read position
        except FileNotFoundError:
            print(f"Error: File {self.data_source} not found.")
            self.file_available = False

    def validate_input(self, new_value):
        """Validates input for the Period field (not used)."""
        try:
            if new_value == "" or (0.000000001 <= float(new_value) <= 10**2):
                return True
            else:
                return False
        except ValueError:
            return False

    def validate_m_input(self, new_value):
        """Validates input for the M field (number of experiments)."""
        try:
            if new_value == "" or (0 < int(new_value) <= 1000):
                return True
            else:
                return False
        except ValueError:
            return False

    def toggle_start_record(self):
        """Toggles the 'Record on Start' option."""
        self.start_record = not self.start_record
        if self.start_record:
            self.start_record_button.config(text="Record on Start: On", bg="green")
            # If we're already reading, start recording immediately
            if self.reading and not self.is_recording:
                self.is_recording = True
                self.toggle_recording()
        else:
            self.start_record_button.config(text="Record on Start: Off", bg="#565656")


    def start_realtime_reading(self):
        """Starts a thread for reading data from a file in real time."""
        if not self.data_thread or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.read_data_realtime)
            self.data_thread.daemon = True  # Allow the thread to exit when the main program exits
            self.data_thread.start()

    def start_reading(self):
        """Starts the main data reading process."""
        if not self.reading:
            self.current_experiment_num = 0 # Reset experiment counter
            self.reading = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Start recording if "Record on Start" is enabled
            if self.start_record and not self.is_recording:
                self.is_recording = True
                self.toggle_recording()

            try:
                self.num_experiments = int(self.m_entry.get())
            except ValueError:
                print("Invalid value for M. Using default value of 1.")
                self.num_experiments = 1

            if not self.data_thread or not self.data_thread.is_alive():
                if isinstance(self.data_source, str):  # If reading from file
                    self.start_realtime_reading()
                else: # If reading from SR400
                    self.start_time = time.time()  # Record the *overall* start time
                    self.experiment_averages = []  # Clear previous averages
                    self.a_values = []
                    self.b_values = []
                    self.x_values = []
                    self.data_thread = threading.Thread(target=self.read_data_from_device)
                    self.data_thread.daemon = True
                    self.data_thread.start()

    def stop_reading(self):
        """Stops data reading."""
        if self.reading:
            self.reading = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.is_recording:
                self.toggle_recording()  # Stop recording

            if self.data_source and not isinstance(self.data_source, str):
                # If using SR400, stop acquisition, but keep QA/QB running
                self.data_source.stop_acquisition()
                self.start_button.config(state=tk.NORMAL) # Re-enable Start


    def reset_data(self):
        """Resets all data and clears the plot."""
        self.data_queue.queue.clear()
        self.times = []
        self.a_values = []
        self.b_values = []
        self.x_values = []
        self.experiment_averages = []
        self.a_value = 0.0
        self.b_value = 0.0
        self.x_value = 0.0
        self.data_list = []
        self.update_gui_values()
        self.update_plot()

    def read_data_realtime(self):
        """Reads data from a file in real time (for file input)."""
        while True:
            if not self.reading and isinstance(self.data_source, str):
                # If reading is stopped and we're reading from a file, break the loop
                break
            try:
                self.data_file.seek(self.last_read_pos) # Seek to last read position
                if self.data_source.endswith('.csv'):
                    reader = csv.reader(self.data_file)
                else:
                    reader = csv.reader(self.data_file, delimiter=' ')

                new_lines = False
                for row in reader:
                    new_lines = True
                    if row:
                        self.data_queue.put(row) # Add data to the queue
                self.last_read_pos = self.data_file.tell()  # Update last read position

                if not new_lines:
                    # If no new lines were read, pause briefly to avoid busy-waiting
                    time.sleep(self.UPDATE_INTERVAL)
            except Exception as e:
                print(f"Error reading data (realtime): {e}")
            time.sleep(self.UPDATE_INTERVAL)  # Regular update interval

    def start_data_acquisition(self):
        """Starts data acquisition from the connected device (SR400)."""
        if not self.data_thread or not self.data_thread.is_alive():
            self.data_thread = threading.Thread(target=self.read_data_from_device)
            self.data_thread.daemon = True
            self.data_thread.start()

    def read_data_from_device(self):
        """Reads data from the connected SR400 device."""
        while self.reading:
            if self.data_source:
                try:
                    # Acquire data for *one* experiment
                    data = self.data_source.acquire_data()
                    self.current_experiment_num += 1
                    print(f"Experiment {self.current_experiment_num} completed.")

                    if data:
                        # Calculate the average of A and B *for this experiment*
                        a_vals = [row[0] for row in data if len(row) > 0]
                        b_vals = [row[1] for row in data if len(row) > 1]


                        if a_vals :  # Avoid division by zero
                           avg_a = sum(a_vals) / len(a_vals)
                           self.a_values.append(avg_a) #for plot
                           self.a_value = avg_a # for value show
                        else:
                            avg_a = 0.0
                            self.a_values.append(0)


                        if b_vals:
                            avg_b = sum(b_vals) / len(b_vals)
                            self.b_values.append(avg_b)
                            self.b_value = avg_b
                        else:
                            avg_b = 0.0
                            self.b_values.append(0)

                        if a_vals or b_vals:
                            self.x_value = avg_a # (avg_a + avg_b) / 2 # Use A value now.
                            self.experiment_averages.append(self.x_value)
                        else:
                             self.x_value = 0.0
                             self.experiment_averages.append(0)

                        self.x_values.append(self.x_value) #for plot
                        self.update_gui_values()
                        self.update_plot()

                        # Put the raw data into the queue for processing (if needed)
                        for row in data:
                            self.data_queue.put(row)


                    if self.current_experiment_num >= self.num_experiments:
                        # All experiments completed
                        self.stop_reading()
                        print("All experiments completed.")
                        # Keep QA/QB running
                        self.qa_active = True
                        self.qb_active = True
                        self.start_qa_update()
                        self.start_qb_update()
                    else:
                        # Pause *briefly* between experiments.  Crucially, set the flag.
                        self.is_between_experiments = True
                        time.sleep(0.5)  # Short pause.  Long enough for QA/QB to run.
                        self.is_between_experiments = False


                except Exception as e:
                    print(f"Error reading data from device: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def update_gui_values(self):
        """Updates the displayed values in the GUI."""
        self.A_value_label.config(text=f"{self.a_value:.1f}")
        self.B_value_label.config(text=f"{self.b_value:.1f}")
        self.QA_value_label.config(text=f"{self.qa_value:.1f}")
        self.QB_value_label.config(text=f"{self.qb_value:.1f}")
        self.x_value_label.config(text=f"{self.x_value:.1f}")

    def update_plot(self):
        """Updates the plot with the experiment averages."""
        self.ax.clear()
        if self.experiment_averages:
            indices = list(range(len(self.experiment_averages)))
            self.ax.plot(indices, self.experiment_averages, marker='o', linestyle='-', color='green')

        self.ax.set_title('Data', fontsize=16)
        self.ax.set_xlabel('Experiment Index')
        self.ax.set_ylabel('Average Value')
        self.ax.grid(True)
        self.canvas.draw()


    def process_data_queue(self):
        """Processes data from the queue (less critical now)."""
        while not self.data_queue.empty():
            row = self.data_queue.get()
            # We don't use the individual data points for the main average anymore,
            # but we still process the queue for recording and other potential uses.
            numbers = list(map(float, row))
            formatted_data = " ".join(map(str, numbers))
            self.data_list.append(formatted_data)
            if len(self.data_list) > 10:
                self.data_list.pop(0)

            if self.is_recording:
                timestamp = str(time.time())  # Use raw time for recording
                with open(self.recording_file.name, "a") as rec_file:
                    rec_file.write(f"{timestamp} - {formatted_data}\n")

            # You *could* update a_value and b_value here with the *instantaneous*
            # values, but it's less important now that the main average is
            # calculated per experiment.
            # self.a_value = numbers[0] if len(numbers) > 0 else 0.0
            # self.b_value = numbers[1] if len(numbers) > 1 else 0.0
            # self.update_gui_values()  # This would show the *instantaneous* A/B


        # We no longer need to call update_plot here, as it's done per-experiment.
        # self.update_plot()

    def update_qa_continuously(self):
        """Continuously updates the QA value from the SR400."""
        while True:
            # Only update QA if we're NOT in the middle of an experiment
            if self.data_source and self.qa_active and not self.is_between_experiments:
                try:
                    with self.sr400_lock:  # Acquire lock before SR400 access
                        time.sleep(0.2)  # Short pause
                        self.qa_value = float(self.data_source.sr400.query("QA").strip('\r\n'))
                        time.sleep(0.2)
                        self.update_gui_values() # Update after getting QA
                except Exception as e:
                    print(f"Error reading QA value: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def update_qb_continuously(self):
        """Continuously updates the QB value from the SR400."""
        while True:
            # Only update QB if we're NOT in the middle of an experiment
            if self.data_source and self.qb_active and not self.is_between_experiments:
                try:
                    with self.sr400_lock:
                        time.sleep(0.2)
                        self.qb_value = float(self.data_source.sr400.query("QB").strip('\r\n'))
                        time.sleep(0.2)
                        self.update_gui_values()
                except Exception as e:
                    print(f"Error reading QB value: {e}")
            time.sleep(self.UPDATE_INTERVAL)

    def start_qa_update(self):
        """Starts a separate thread for updating the QA value."""
        if not self.qa_thread or not self.qa_thread.is_alive():
            self.qa_thread = threading.Thread(target=self.update_qa_continuously)
            self.qa_thread.daemon = True
            self.qa_thread.start()

    def start_qb_update(self):
        """Starts a separate thread for updating the QB value."""
        if not self.qb_thread or not self.qb_thread.is_alive():
            self.qb_thread = threading.Thread(target=self.update_qb_continuously)
            self.qb_thread.daemon = True
            self.qb_thread.start()

    def start_gui_update(self):
        """Starts the periodic GUI update loop."""
        self.process_data_queue()  # Process any data in the queue
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
                self.is_recording = False  # Reset flag if file creation failed
                self.record_button.config(text="Record")

    def on_closing(self):
        """Handles application closing."""
        self.stop_reading()  # Stop any ongoing reading
        if hasattr(self, 'data_file') and self.data_file:
            self.data_file.close()  # Close data file if open
        self.root.destroy() # Destroy the Tkinter window