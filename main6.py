import tkinter as tk
import pyvisa
import time
import numpy as np
import modified_1527reader as reader 

class SR400Device:
    def __init__(self, resource_name):
        self.rm = pyvisa.ResourceManager()
        self.sr400 = self.rm.open_resource(resource_name)
        self.tset = 0.001
        self.num_periods = 2000

    def acquire_data(self):
        """Acquires data from the SR400."""
        try:
            self.sr400.write(f"CP2, {self.tset * 10 ** 7 + 1}\n")  # Set preset
            print(f"установлен tset: {self.tset}")
            self.sr400.write(f"NP {self.num_periods}\n")  # Set number of periods
            time.sleep(1)
            self.sr400.write("CR\n")
            self.sr400.write("CS\n")
            time.sleep()

            fa = []
            self.sr400.write("EA\n")
            for _ in range(self.num_periods):
                response = self.sr400.read().rstrip()
                if response:
                    fa.append(list(map(int, response.split(','))))
                else:
                    print("Empty response received")
            self.sr400.write("CR\n")
            return fa
        except Exception as e:
            print(f"Error acquiring data: {e}")
            return None

    def stop_acquisition(self):
        """Stops the SR400 acquisition gracefully."""
        self.sr400.write("CR\n")

    def close(self):
        """Closes the connection to the SR400."""
        self.sr400.close()
        self.rm.close()

    def query(self, command):
        """Sends a query to the SR400 and returns the response."""
        try:
            response = self.sr400.query(command)
            return response
        except Exception as e:
            print(f"Error sending query: {e}")
            return None

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SR400 Control and Data Acquisition")
        self.sr400_device = self.connect_to_sr400()

        if self.sr400_device:
            self.reader_app = reader.App(self.root, data_source=self.sr400_device)
            self.create_tset_control()
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        else:
            print("Failed to connect to SR400. Exiting.")
            self.root.destroy()

    def connect_to_sr400(self):
        """Connects to the SR400 instrument."""
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            sr400_resource = None
            for resource in resources:
                if 'ASRL5' in resource:
                    try:
                        temp_inst = rm.open_resource(resource, timeout=5000)
                        temp_inst.close()
                        sr400_resource = resource
                        break
                    except Exception:
                        continue

            if sr400_resource:
                device = SR400Device(sr400_resource)
                print(f"Connected to SR400 on {sr400_resource}")
                return device
            else:
                print("SR400 not found.")
                return None
        except Exception as e:
            print(f"Error connecting to SR400: {e}")
            return None

    def create_tset_control(self):
        """Creates a control for changing the Tset value."""
        tset_frame = tk.Frame(self.reader_app.row3_frame, bg=self.reader_app.VALUE_BG, bd=2, relief=tk.GROOVE)
        tset_frame.grid(row=0, column=4, padx=5, pady=2, sticky="nsew")

        tset_label = tk.Label(tset_frame, text="Tset (s):", font=self.reader_app.FONT_STYLE,
                               fg=self.reader_app.VALUE_FG, bg=self.reader_app.VALUE_BG,
                               width=self.reader_app.LABEL_WIDTH + 2)
        tset_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.tset_entry = tk.Entry(tset_frame, font=self.reader_app.FONT_STYLE,
                                   bg=self.reader_app.ENTRY_BG, fg=self.reader_app.ENTRY_FG,
                                   width=self.reader_app.ENTRY_WIDTH)
        self.tset_entry.insert(0, str(self.sr400_device.tset))
        self.tset_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.tset_entry.bind("<Return>", self.update_tset)

        num_periods_frame = tk.Frame(self.reader_app.row3_frame, bg=self.reader_app.VALUE_BG, bd=2,
                                     relief=tk.GROOVE)
        num_periods_frame.grid(row=1, column=4, padx=5, pady=2, sticky="nsew")

        num_periods_label = tk.Label(num_periods_frame, text="N Periods:", font=self.reader_app.FONT_STYLE,
                                     fg=self.reader_app.VALUE_FG, bg=self.reader_app.VALUE_BG,
                                     width=self.reader_app.LABEL_WIDTH + 2)
        num_periods_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.num_periods_entry = tk.Entry(num_periods_frame, font=self.reader_app.FONT_STYLE,
                                          bg=self.reader_app.ENTRY_BG, fg=self.reader_app.ENTRY_FG,
                                          width=self.reader_app.ENTRY_WIDTH)
        self.num_periods_entry.insert(0, str(self.sr400_device.num_periods))
        self.num_periods_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.num_periods_entry.bind("<Return>", self.update_num_periods)

    def update_tset(self, event):
        """Updates the Tset value in the SR400Device object."""
        try:
            new_tset = float(self.tset_entry.get())
            if 0.000001 <= new_tset <= 1:
                self.sr400_device.tset = new_tset
                print(f"Tset updated to: {new_tset}")
            else:
                print("Invalid Tset value. Enter a value between 1e-6 and 1.")
        except ValueError:
            print("Invalid Tset value. Please enter a number.")

    def update_num_periods(self, event):
        """Updates the num_periods value in the SR400Device object."""
        try:
            new_num_periods = int(self.num_periods_entry.get())
            if 1 <= new_num_periods <= 2000:
                self.sr400_device.num_periods = new_num_periods
                print(f"Num_periods updated to: {new_num_periods}")
            else:
                print("Invalid num_periods value. Enter a value between 1 and 2000.")
        except ValueError:
            print("Invalid num_periods value. Please enter an integer.")

    def on_closing(self):
        """Handles the closing of the application."""
        self.reader_app.on_closing()
        if self.sr400_device:
            self.sr400_device.stop_acquisition()
            self.sr400_device.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()