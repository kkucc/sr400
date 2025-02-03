# import modified_1522reader as reader  # Import the modified library
import tkinter as tk
import pyvisa
import time
import numpy as np
import modified_1522reader as reader

class SR400Device:
    def __init__(self, resource_name):
        self.rm = pyvisa.ResourceManager()
        self.sr400 = self.rm.open_resource(resource_name)
        self.tset = 0.01
        self.num_periods = 2000

    def acquire_data(self):
        """Acquires data from the SR400."""
        try:
            self.sr400.write(f"CP2,{self.tset*10**7}\n") # Set preset
            self.sr400.write(f"NP {self.num_periods}\n")  # Set number of periods
            time.sleep(0.1)
            self.sr400.write("CR\n")
            self.sr400.write("CS\n")
            time.sleep(self.tset * (self.num_periods + 1))

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
              if 'ASRL' in resource:
                try:
                    temp_inst = rm.open_resource(resource)
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
                                fg=self.reader_app.VALUE_FG, bg=self.reader_app.VALUE_BG, width=self.reader_app.LABEL_WIDTH+2)
        tset_label.grid(row=0, column=0, padx=2, pady=2, sticky="w")

        self.tset_entry = tk.Entry(tset_frame, font=self.reader_app.FONT_STYLE,
                                    bg=self.reader_app.ENTRY_BG, fg=self.reader_app.ENTRY_FG, width=self.reader_app.ENTRY_WIDTH)
        self.tset_entry.insert(0, str(self.sr400_device.tset))
        self.tset_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.tset_entry.bind("<Return>", self.update_tset)

    def update_tset(self, event):
        """Updates the Tset value in the SR400Device object."""
        try:
            new_tset = float(self.tset_entry.get())
            if 10**(-9) <= new_tset <= 10**2:
              self.sr400_device.tset = new_tset
              print(f"Tset updated to: {new_tset}")
            else:
               print("Invalid Tset value. Enter a value between 1e-9 and 1e2.")
        except ValueError:
            print("Invalid Tset value. Please enter a number.")

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