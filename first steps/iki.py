import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import serial
import time
import threading
import pyvisa

class SR400Controller:
    """Handles communication with the SR400 using pyvisa."""

    def __init__(self):
        self.rm = None
        self.sr4 = None
        self.resource_name = 'ASRL5::INSTR' 

    def connect(self, resource_name):
        """Connects to the SR400."""
        self.resource_name = resource_name
        try:
            self.rm = pyvisa.ResourceManager()
            self.sr4 = self.rm.open_resource(self.resource_name)
            print(f"Connected to SR400 at {self.resource_name}")
            return True
        except pyvisa.errors.VisaIOError as e:
            print(f"Error connecting to SR400 at {self.resource_name}: {e}")
            self.sr4 = None
            return False
        except Exception as e:
            print(f"Unexpected error connecting to SR400: {e}")
            self.sr4 = None
            return False

    def disconnect(self):
        """Disconnects from the SR400."""
        if self.sr4:
            try:
                self.sr4.close()
                print(f"Disconnected from SR400 at {self.resource_name}")
            except Exception as e:
                print(f"Error disconnecting from SR400: {e}")
            finally:
                self.sr4 = None
        if self.rm:
            try:
                self.rm.close()
            except Exception as e:
                print(f"Error closing Resource Manager: {e}")
            finally:
                self.rm = None

    def is_connected(self):
        """Checks if the SR400 is connected."""
        return self.sr4 is not None

    def send_command(self, command):
        """Sends a command to the SR400."""
        if not self.is_connected():
            print("Error: Not connected to SR400.")
            return False
        try:
            self.sr4.write(command + "\n")  # Append newline for SR400
            print(f"Sent to SR400: {command}")  # Log command
            return True
        except pyvisa.errors.VisaIOError as e:
            print(f"Error sending command '{command}' to SR400: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending command '{command}' to SR400: {e}")
            return False

class SerialDeviceController:
    """Handles communication and sequence execution for the serial device."""

    def __init__(self):
        self.ser = None
        self.port = 'COM8'
        self.baudrate = 115200
        self.timeout = 1
        self.is_running = False
        self.stop_event = threading.Event()

    def connect(self, port, baudrate):
        """Connects to the serial port."""
        self.port = port
        self.baudrate = int(baudrate)
        if self.ser and self.ser.is_open:
            print("Already connected.")
            return True
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            print(f"Connected to {self.port} at {self.baudrate} baud.")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            self.ser = None
            return False
        except ValueError as e:
            print(f"Error: Invalid baud rate '{baudrate}'. {e}")
            self.ser = None
            return False

    def disconnect(self):
        """Disconnects from the serial port."""
        if self.ser and self.ser.is_open:
            try:
                # a stop command before closing
                if self.is_running:
                    self.stop_sequence() 
                self.send_command(":w10=0,0.")
                time.sleep(0.1)
            except Exception as e:
                print(f"Warning: Error sending stop command during disconnect: {e}")
            finally:
                self.ser.close()
                print(f"Disconnected from {self.port}.")
        self.ser = None
        self.is_running = False

    def is_connected(self):
        """Checks if the serial port is connected and open."""
        return self.ser and self.ser.is_open

    def send_command(self, command, delay=0.002):
        """Sends a command to the serial device."""
        if not self.is_connected():
            print("Error: Not connected.")
            return False
        try:
            full_command = command + "\r\n"
            self.ser.write(full_command.encode())
            #print(f"Sent: {command}") # Log sent command
            if delay > 0:
                time.sleep(delay)
            # Optional: Read response if expected
            # response = self.ser.read_all().decode().strip()
            # if response:
            #     print(f"Rcvd: {response}")
            return True
        except serial.SerialException as e:
            print(f"Error sending command '{command}': {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending command '{command}': {e}")
            return False

    def run_sequence(self, params, log_callback, sr400_controller):
        """Runs the main control sequence in a separate thread."""
        if not self.is_connected():
            log_callback("Error: Cannot start sequence, not connected to serial.")
            self.is_running = False
            return

        if not sr400_controller.is_connected():
            log_callback("Error: Cannot start sequence, not connected to SR400.")
            self.is_running = False
            return


        self.is_running = True
        self.stop_event.clear() # stop flag

        try:
            # --- Parameters ---
            hz = params.get('hz', 1) # Default Hz if 
            wavefront = params.get('wavefront', 3) # Default wavefront if 
            # start_offset_w17 = params.get('start_offset_w17', 950)
            # start_offset_w18 = params.get('start_offset_w18', 900)
            num_cycles = params.get('num_cycles', 101)
            inner_sleep = params.get('inner_sleep', 0.005)
            inner_ramp_steps = params.get('inner_ramp_steps', 100) # N value
            sr400_tset_multiplier = params.get('sr400_tset_multiplier', 0.008) # Default  Tset multiplier
            DWELL = params.get('DWELL', 0.002) #Default tset offset multiplier
            scan_lvl = params.get('scan_lvl', -1.960) # Default scan level
            scan_step = params.get('scan_step', 0.010) # Default scan step

            log_callback("Starting sequence...")

            # --- Initial Configuration ---
            self.send_command(f":w13={hz},0.", delay=0.002)
            log_callback(f"Set Hz (w13): {hz}")
            self.send_command(f":w14=18,0.", delay=0.002) # 14 static

            # self.send_command(":w60=0,0.", delay=0.002) # Fixed init
            # log_callback("Sent: :w60=0,0.")
            # self.send_command(":w74=1,1.", delay=0.001) # Fixed init
            # log_callback("Sent: :w74=1,1.")
            self.send_command(":w10=1,0.", delay=0.002) # Enable output
            log_callback(" :w10=1,0.")

            # Set Wavefront Type
            self.send_command(f":w12={wavefront}.", delay=0.001)
            log_callback(f"Set Wavefront (w12): {wavefront}")
            self.send_command(f":w11={wavefront}.", delay=0.001)
            log_callback(f"Set Wavefront (w11): {wavefront}")
            
            # --- SR400 Initialization ---
            sr400_controller.send_command("CR")
            Tset = sr400_tset_multiplier * (10**7)
            sr400_controller.send_command(f"CP2,{Tset}")
            time.sleep(0.02)
            sr400_hz = 10**10//(Tset + DWELL * (10**7))
            self.send_command(f":w13={sr400_hz},0.") # Set Hz on serial device based on SR400 calculation
            sr400_controller.send_command(f"NP {num_cycles}")
            sr400_controller.send_command("NE 0")

            # Main Loop
            current_offset_w18 = 950
            for cycle in range(num_cycles):
                if self.stop_event.is_set():
                    log_callback("Stop signal received, aborting sequence.")
                    break
                # for i in range(musorsoffset):
                    log_callback(f"--- Cycle {cycle + 1} / {num_cycles} ---")

                    #  Ramp Up (Inner Loop 1)
                    log_callback("Ramping w17 up...")
                    offset_ramp = 0
                    self.send_command(f":w18={current_offset_w18}.", delay=inner_sleep) # Set w18 for this sub-cycle
                    log_callback(f"Set w18 = {current_offset_w18}")

                    for n in range(inner_ramp_steps):
                        if self.stop_event.is_set(): break
                        w17_value = start_offset_w17 + offset_ramp
                        if not self.send_command(f":w17={w17_value}.", delay=inner_sleep):
                            raise Exception("Failed to send w17 command (ramp up)") # Stop if send fails
                        # log_callback(f"  Set w17 = {w17_value}") # Too verbose for log
                        offset_ramp += 1
                    if self.stop_event.is_set(): break
                    log_callback(f"  Ramp up complete (w17 reached ~{start_offset_w17 + inner_ramp_steps -1})")
                    time.sleep(inner_sleep) # Pause after ramp

                    current_offset_w18 += 1 # Increment w18 for next part

                    # Ramp Down
                    log_callback("Ramping w17 down...")
                    offset_ramp = 0
                    self.send_command(f":w18={current_offset_w18}.", delay=inner_sleep) # Set new w18
                    log_callback(f"Set w18 = {current_offset_w18}")

                    for n in range(inner_ramp_steps):
                        if self.stop_event.is_set(): break
                        w17_value = (start_offset_w17 + inner_ramp_steps -1) - offset_ramp # Start from high value
                        if not self.send_command(f":w17={w17_value}.", delay=inner_sleep):
                            raise Exception("Failed to send w17 command (ramp down)")
                        # log_callback(f"  Set w17 = {w17_value}") # Too verbose
                        offset_ramp += 1
                    if self.stop_event.is_set(): break
                    log_callback(f"  Ramp down complete (w17 reached ~{start_offset_w17})")
                    time.sleep(inner_sleep)

                current_offset_w18 += 1
                
                #SR400 Scan sequence
                # log_callback("Starting SR400 Scan...")
                sr400_controller.send_command(f"PL 1, {scan_lvl}")
                sr400_controller.send_command(f"PY 1, {scan_step}")
                sr400_controller.send_command("CS")
                time.sleep(1.05)  # Adjust timing if needed

                # Reverse Scan
                sr400_controller.send_command(f"PL 1, {scan_lvl + (inner_ramp_steps - 1) * scan_step}")
                sr400_controller.send_command(f"PY 1, {-scan_step}")  # Reverse the step
                time.sleep(0.1)  # Adjust timing if needed
                sr400_controller.send_command("CR")  # Clear
                sr400_controller.send_command("CS")
                time.sleep(1.2)

                sr400_controller.send_command(f"PL 1, {scan_lvl}")
                sr400_controller.send_command("CR")

            # End of Sequence
            if not self.stop_event.is_set():
                log_callback("Sequence completed normally.")

        except serial.SerialException as e:
            log_callback(f"Serial Error during sequence: {e}")
        except Exception as e:
            log_callback(f"Error during sequence: {e}")
        finally:
            # Clean up
            log_callback("Sending stop command :w10=0,0.")
            self.send_command(":w10=0,0.")
            self.is_running = False
            log_callback("Sequence finished.")

    def stop_sequence(self):
        """Signals the running sequence to stop."""
        if self.is_running:
            print("Sending stop signal to sequence...")
            self.stop_event.set()
        else:
            print("Sequence not running.")


class SerialControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Device Control")
        self.root.geometry("750x700")  # Increased height
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.serial_controller = SerialDeviceController()
        self.sr400_controller = SR400Controller()  # Instance for SR400 control
        self.sequence_thread = None

        # Style
        self.root.configure(bg="#f0f0f0")
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=2, background="#f0f0f0")
        style.configure("TEntry", padding=4)

        # GUI Frames
        conn_frame = ttk.Frame(root, padding="10")
        conn_frame.pack(fill=tk.X)

        sr400_conn_frame = ttk.Frame(root, padding="10")  # New frame for SR400
        sr400_conn_frame.pack(fill=tk.X)

        param_frame = ttk.Frame(root, padding="10")
        param_frame.pack(fill=tk.X)

        action_frame = ttk.Frame(root, padding="10")
        action_frame.pack(fill=tk.X)

        log_frame = ttk.Frame(root, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Connection Frame GUI (Serial Device)
        ttk.Label(conn_frame, text="Serial Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.insert(0, self.serial_controller.port)
        self.port_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(conn_frame, text="Baud:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.baud_entry = ttk.Entry(conn_frame, width=10)
        self.baud_entry.insert(0, str(self.serial_controller.baudrate))
        self.baud_entry.grid(row=0, column=3, padx=5, pady=5)

        self.connect_button = ttk.Button(conn_frame, text="Connect Serial", command=self.connect_serial)
        self.connect_button.grid(row=0, column=4, padx=10, pady=5)

        self.disconnect_button = ttk.Button(conn_frame, text="Disconnect Serial", command=self.disconnect_serial, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=5, padx=5, pady=5)

        self.status_label = ttk.Label(conn_frame, text="Serial Status: Disconnected", foreground="red")
        self.status_label.grid(row=0, column=6, padx=10, pady=5, sticky="e")
        conn_frame.columnconfigure(6, weight=1) # Make status label expand

        # Connection Frame GUI (SR400)
        ttk.Label(sr400_conn_frame, text="SR400 Resource:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.sr400_resource_entry = ttk.Entry(sr400_conn_frame, width=25)
        self.sr400_resource_entry.insert(0, self.sr400_controller.resource_name)
        self.sr400_resource_entry.grid(row=0, column=1, padx=5, pady=5)

        self.sr400_connect_button = ttk.Button(sr400_conn_frame, text="Connect SR400", command=self.connect_sr400)
        self.sr400_connect_button.grid(row=0, column=2, padx=10, pady=5)

        self.sr400_disconnect_button = ttk.Button(sr400_conn_frame, text="Disconnect SR400", command=self.disconnect_sr400, state=tk.DISABLED)
        self.sr400_disconnect_button.grid(row=0, column=3, padx=5, pady=5)

        self.sr400_status_label = ttk.Label(sr400_conn_frame, text="SR400 Status: Disconnected", foreground="red")
        self.sr400_status_label.grid(row=0, column=4, padx=10, pady=5, sticky="e")
        sr400_conn_frame.columnconfigure(4, weight=1)

        # Parameter Frame
        param_col1 = 0
        param_col2 = 2
        param_col3 = 4  # New column for SR400 related parameters
        param_row = 0

        ttk.Label(param_frame, text="Hz (e.g., w13):").grid(row=param_row, column=param_col1, padx=5, pady=3, sticky="w")
        self.hz_entry = ttk.Entry(param_frame, width=10)
        self.hz_entry.insert(0, "1")
        self.hz_entry.grid(row=param_row, column=param_col1+1, padx=5, pady=3)
        param_row += 1

        ttk.Label(param_frame, text="Wavefront (w11/12):").grid(row=param_row, column=param_col1, padx=5, pady=3, sticky="w")
        self.wavefront_entry = ttk.Entry(param_frame, width=10)
        self.wavefront_entry.insert(0, "3")
        self.wavefront_entry.grid(row=param_row, column=param_col1+1, padx=5, pady=3)
        param_row += 1

        # ttk.Label(param_frame, text="Start Offset w17:").grid(row=param_row, column=param_col1, padx=5, pady=3, sticky="w")
        # self.start_offset_w17_entry = ttk.Entry(param_frame, width=10)
        # self.start_offset_w17_entry.insert(0, "950")
        # self.start_offset_w17_entry.grid(row=param_row, column=param_col1+1, padx=5, pady=3)

        # Reset row counter for second column
        param_row = 0

        # ttk.Label(param_frame, text="Start Offset w18:").grid(row=param_row, column=param_col2, padx=5, pady=3, sticky="w")
        # self.start_offset_w18_entry = ttk.Entry(param_frame, width=10)
        # self.start_offset_w18_entry.insert(0, "900")
        # self.start_offset_w18_entry.grid(row=param_row, column=param_col2+1, padx=5, pady=3)
        # param_row += 1

        ttk.Label(param_frame, text="Num Cycles:").grid(row=param_row, column=param_col2, padx=5, pady=3, sticky="w")
        self.num_cycles_entry = ttk.Entry(param_frame, width=10)
        self.num_cycles_entry.insert(0, "101")
        self.num_cycles_entry.grid(row=param_row, column=param_col2+1, padx=5, pady=3)
        param_row += 1

        ttk.Label(param_frame, text="Inner Sleep (s):").grid(row=param_row, column=param_col2, padx=5, pady=3, sticky="w")
        self.inner_sleep_entry = ttk.Entry(param_frame, width=10)
        self.inner_sleep_entry.insert(0, "0.005")
        self.inner_sleep_entry.grid(row=param_row, column=param_col2+1, padx=5, pady=3)
        param_row += 1

        ttk.Label(param_frame, text="Scan Level:").grid(row=param_row, column=param_col2, padx=5, pady=3, sticky="w")
        self.scan_lvl_entry = ttk.Entry(param_frame, width=10)
        self.scan_lvl_entry.insert(0, "-1.960")
        self.scan_lvl_entry.grid(row=param_row, column=param_col2 + 1, padx=5, pady=3)
        param_row += 1

        # SR400 Parameters (Third Column)
        param_row = 0
        ttk.Label(param_frame, text="SR400 Tset :").grid(row=param_row, column=param_col3, padx=5, pady=3, sticky="w")
        self.sr400_tset_multiplier_entry = ttk.Entry(param_frame, width=10)
        self.sr400_tset_multiplier_entry.insert(0, "0.008")
        self.sr400_tset_multiplier_entry.grid(row=param_row, column=param_col3 + 1, padx=5, pady=3)
        param_row += 1

        ttk.Label(param_frame, text="SR400 DWELL:").grid(row=param_row, column=param_col3, padx=5, pady=3, sticky="w")
        self.DWELL_entry = ttk.Entry(param_frame, width=10)
        self.DWELL_entry.insert(0, "0.002")
        self.DWELL_entry.grid(row=param_row, column=param_col3 + 1, padx=5, pady=3)
        param_row += 1


        ttk.Label(param_frame, text="Scan Step:").grid(row=param_row, column=param_col3, padx=5, pady=3, sticky="w")
        self.scan_step_entry = ttk.Entry(param_frame, width=10)
        self.scan_step_entry.insert(0, "0.010")
        self.scan_step_entry.grid(row=param_row, column=param_col3 + 1, padx=5, pady=3)
        param_row += 1


        # Action Frame
        self.start_button = ttk.Button(action_frame, text="Start Sequence", command=self.start_sequence, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=10, pady=5)

        self.stop_button = ttk.Button(action_frame, text="Stop Sequence", command=self.stop_sequence, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=5)

        # Log Frame
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, width=80)  # Increased height and width
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.configure(state='disabled') # Read-only

    def log_message(self, message):
        """Appends a message to the log area (thread-safe)."""
        def append():
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
            self.log_area.configure(state='disabled')
            self.log_area.see(tk.END) # Auto-scroll
        # Schedule the GUI update to run in the main thread
        self.root.after(0, append)

    def connect_serial(self):
        """Handles the Connect Serial button click."""
        port = self.port_entry.get()
        baud = self.baud_entry.get()
        if self.serial_controller.connect(port, baud):
            self.status_label.config(text="Serial Status: Connected", foreground="green")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            # Only enable start button if SR400 is also connected
            if self.sr400_controller.is_connected():
                self.start_button.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
            self.baud_entry.config(state=tk.DISABLED)
            self.log_message(f"Successfully connected to serial port {port}.")
        else:
            self.status_label.config(text="Serial Status: Connection Failed", foreground="red")
            self.log_message(f"Failed to connect to serial port {port}.")

    def disconnect_serial(self):
        """Handles the Disconnect Serial button click."""
        if self.serial_controller.is_running:
            self.stop_sequence()
        self.serial_controller.disconnect()
        self.status_label.config(text="Serial Status: Disconnected", foreground="red")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.baud_entry.config(state=tk.NORMAL)
        self.log_message("Disconnected from serial port.")

    def connect_sr400(self):
        """Handles the Connect SR400 button click."""
        resource_name = self.sr400_resource_entry.get()
        if self.sr400_controller.connect(resource_name):
            self.sr400_status_label.config(text="SR400 Status: Connected", foreground="green")
            self.sr400_connect_button.config(state=tk.DISABLED)
            self.sr400_disconnect_button.config(state=tk.NORMAL)
            # Only enable start button if serial is also connected
            if self.serial_controller.is_connected():
                self.start_button.config(state=tk.NORMAL)
            self.sr400_resource_entry.config(state=tk.DISABLED)
            self.log_message(f"Successfully connected to SR400 at {resource_name}.")
        else:
            self.sr400_status_label.config(text="SR400 Status: Connection Failed", foreground="red")
            self.log_message(f"Failed to connect to SR400 at {resource_name}.")

    def disconnect_sr400(self):
        """Handles the Disconnect SR400 button click."""
        self.sr400_controller.disconnect()
        self.sr400_status_label.config(text="SR400 Status: Disconnected", foreground="red")
        self.sr400_connect_button.config(state=tk.NORMAL)
        self.sr400_disconnect_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.sr400_resource_entry.config(state=tk.NORMAL)
        self.log_message("Disconnected from SR400.")

    def get_params(self):
        """Reads parameters from GUI entries."""
        params = {}
        try:
            params['hz'] = int(self.hz_entry.get())
            params['wavefront'] = int(self.wavefront_entry.get())
            # params['start_offset_w17'] = int(self.start_offset_w17_entry.get())
            # params['start_offset_w18'] = int(self.start_offset_w18_entry.get())
            params['num_cycles'] = int(self.num_cycles_entry.get())
            params['inner_sleep'] = float(self.inner_sleep_entry.get())
            params['sr400_tset_multiplier'] = float(self.sr400_tset_multiplier_entry.get())
            params['DWELL'] = float(self.DWELL_entry.get())
            params['scan_lvl'] = float(self.scan_lvl_entry.get())
            params['scan_step'] = float(self.scan_step_entry.get())
            # Add validation if needed (e.g., range checks)
            if params['num_cycles'] <= 0 or params['inner_sleep'] < 0:
                raise ValueError("Cycles must be > 0 and Sleep >= 0")
            return params
        except ValueError as e:
            self.log_message(f"Invalid parameter input: {e}. Please enter valid numbers.")
            return None

    def start_sequence(self):
        """Starts the device sequence in a new thread."""
        if not self.serial_controller.is_connected():
            self.log_message("Error: Not connected to serial port.")
            return
        if not self.sr400_controller.is_connected():
            self.log_message("Error: Not connected to SR400.")
            return
        if self.serial_controller.is_running:
            self.log_message("Sequence already running.")
            return

        params = self.get_params()
        if params is None:
            return # Error message already logged by get_params

        # Disable Start, enable Stop
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.set_param_entries_state(tk.DISABLED) # Disable editing during run
        self.sr400_connect_button.config(state=tk.DISABLED)  # Disable the SR400 connect button
        self.sr400_disconnect_button.config(state=tk.DISABLED)

        # Pass the log_message method as the callback
        self.sequence_thread = threading.Thread(
            target=self.serial_controller.run_sequence,
            args=(params, self.log_message, self.sr400_controller),
            daemon=True # Allows app to exit even if thread is stuck
        )
        self.sequence_thread.start()
        self.check_sequence_thread() # Start checking if thread finished

    def stop_sequence(self):
        """Handles the Stop Sequence button click."""
        self.log_message("Stop button pressed.")
        self.serial_controller.stop_sequence()
        # Buttons will be re-enabled by check_sequence_thread when it finishes

    def check_sequence_thread(self):
        """Checks if the sequence thread has finished and updates GUI."""
        if self.sequence_thread and self.sequence_thread.is_alive():
            # Still running, check again later
            self.root.after(100, self.check_sequence_thread)
        else:
            # Finished or wasn't running
            if self.serial_controller.is_connected() and self.sr400_controller.is_connected(): # Only enable if still connected
                self.start_button.config(state=tk.NORMAL)
                self.sr400_connect_button.config(state=tk.DISABLED)  # Re-enable the SR400 connect button
                self.sr400_disconnect_button.config(state=tk.NORMAL)
                self.set_param_entries_state(tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)

            self.stop_button.config(state=tk.DISABLED)
            # Log if it finished unexpectedly (e.g., error) vs normal stop?
            # Controller's is_running flag should be False now.

    def set_param_entries_state(self, state):
        """Enable/disable parameter entry fields."""
        self.hz_entry.config(state=state)
        self.wavefront_entry.config(state=state)
        # self.start_offset_w17_entry.config(state=state)
        # self.start_offset_w18_entry.config(state=state)
        self.num_cycles_entry.config(state=state)
        self.inner_sleep_entry.config(state=state)
        self.sr400_tset_multiplier_entry.config(state=state)
        self.DWELL_entry.config(state=state)
        self.scan_lvl_entry.config(state=state)
        self.scan_step_entry.config(state=state)


    def on_closing(self):
        """Handles window closing event."""
        self.log_message("Closing application...")
        if self.serial_controller.is_running:
            self.stop_sequence()
            # It might be better to wait for the thread to join here
            # but daemon=True helps prevent hangs if it gets stuck.
            if self.sequence_thread:
                self.sequence_thread.join(timeout=1.0) # Wait up to 1 sec

        self.disconnect_serial() # Ensure serial disconnection
        self.disconnect_sr400()   # Ensure SR400 disconnection
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialControlApp(root)
    root.mainloop()