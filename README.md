---

# Two Versions of GUI App for Reading via Prologix USB GPIB `SR400` Two-Channel Gated Photon Counter and Handling Data

Tho, mind you that this app is only for `<= 2000` number of periods. See the [manual](https://www.thinksrs.com/downloads/pdfs/manuals/SR400m.pdf). You can resolve this buffer problem by attaching an Arduino or any chip of your liking

# GUI App

## First Steps

Open `prologix.exe` in `app via lib`. Which is not my app and definitely works for easy communication setup

## Via Lib

* **Libs and Software to Download**  
  Before lib installation, you need to visit [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html#558610) for:

  ```powershell
  pip install pyvisa
  ```

  Actually, I don’t think there are so many (some of them are dependencies), but yk...

  ```powershell
  pip install numpy tkinter matplotlib datetime csv threading time queue
  ```

* ### **How to Use**

  ```python
  # You need to know your PORT address (mine is 5)
  rm.open_resource('ASRL5')
  # Also, you need to know your GPIB address (mine is 23)
  # I used prologix.exe one time, which is really helpful for first steps,
  # but it should also work.
  inst = rm.open_resource('GPIB0::23::INSTR')
  ```

![open](first%20steps/open.png)

`main8.py` will open this GUI app. Let's go through it a little bit.

```python
# Tset(s): 0.001. If you wanna change it, don't forget to use enter (you can check yourself in the terminal).
sr400.write(f"CP2, {self.tset * 10 ** 7 + 1}\n")  # CP - set counter time interval for 1 period (N) from 10**(-9) to 100 seconds.
```

```python
# N periods: 2000. Don't forget to press enter, same with terminal check.
self.sr400.write(f"NP {self.num_periods}\n")  # (1 - 2000)
```

M = 1, `M` is the number of experiments/loops by `N periods` in cycle (start/stop) (no terminal output about this parameter).

`Avg` - average value from 1 M (on the plot, you see green avg dots).

> [!CAUTION]
> **Don't press the `start on record button` 'cause it's logic is broken.**

```python
# A - last digit in A channel buffer (when the cycle was stopped).
# QA - periodic query with some time.sleep() 
# from 1519reader.py
data_source.query("QB").strip('\r\n')  # in main8 it's sr4
# Same with B, QB.
```

![start](first%20steps/start.png)

As you can see here, the `start` button is pressed, and `stop` and `record` are available to press. You should press `record` by yourself, sorry tho.

You can see how the terminal output corresponds to the GUI (plot, values) output.

> Recorded Data
> 
> ![recorded_data](first%20steps/recorded_data.png)
> 
> How to handle this output you can see in `voltage set`.

## App via QT1

Used Qt Designer.

```powershell
pip install pyside6
```

Quite similar tho, it's one .py file.

![qT](first%20steps/qT.png)

## How to Make .exe

**Install PyInstaller**: You can use PyInstaller to convert your Python script into an executable. First, install it using pip:

```bash
pip install pyinstaller
```

Navigate to the directory containing your Python script and run:

```bash
pyinstaller --onefile your_script.py
```

This will create a `dist` folder containing the `.exe` file.

## Voltage Set (Example of Output Data Usage)

![voltage](/voltage%20set/pigraph.png)

For calibration system (via dark counts and GUI app, get this graph).

Idk what is happening here (175-220mV), but after this, I decided to set the SR400 at `DISC lvl=+250 mV` (where the limit is `-300 -- +300`).
