# Two version of gui app for reading `sr400` two channel gated photon counter and handling data

tho mind warn you that this apps only for `<=2000` number of periods see [manual](https://www.thinksrs.com/downloads/pdfs/manuals/SR400m.pdf), you can resolve this buffer problem by attaching ardiono or any chip for your liking

# gui app

## first steps

open `prologix.exe` in `app via lib`. Wich is not my app and defenetly works for eazy comunication setup

## Via lib

* Libs and soft to downoad
  before lib installation you need to visit [ni-visa](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html#558610) for:

  ```powershell
  pip install pyvisa
  ```

  actually i dont think there are so many(some of them are dependencies) but yk..

  ```powershell
   pip install numpy, tkinter,matplotlib, datetime, csv,threading, time, Queue
  ```
* ### **How to use**


  ```python
  pp#you need to know your PORT addr (mine is 5)`
  rm.open_resource('ASRL5')
  #also you need to know your gpib addr( mine is 23)
  # i used 1 time prologix.exe wich is reaaly helpful for first steps, 
  #but also should works
  inst = rm.open_resource('GPIB0::23::INSTR')
  ```

  ![1738852502800](images/readme/1738852502800.png)
  `main8.py` will open this gui app lets go trough it a little bit

  ```python
  #Tset(s): 0.001, if you wanna change it dont forget to use enter( you can check your self in terminal)
  sr400.write(f"CP2, {self.tset * 10 ** 7 + 1}\n")  # CP - set counter i time interval for 1 period(N) from 10**(-9) to 100 seconds
  ```

  ```python
  # N periods: 2000, dont forget to press enter,same with terminal check
  self.sr400.write(f"NP {self.num_periods}\n") (1 - 2000)
  ```

M = 1,`M` number of experiments /loops by `N periods ` in cycle(start/stop)(no terminal output about this parameter)

`Avg` - average value from 1 M( on plot you see green avg dots)

> [ !CAUTION]
> **Dont press `start on record botton` cuz' its logic broken**

```python
#A - last didgit in A channal buffer(when cycle was stoped)
#QA - periodic query from with some time.sleep() 
#from 1519reader.py
data_source.query("QB").strip('\r\n') # in main8 it's sr4
same with B, QB
```

![1738852519093](images/readme/1738852519093.png)

As you can see here botton `start` pressed and `stop` , `record` are avialiable to press. You should press `record  ` by yourself, sorry tho

You can see how terminal output copespond to gui(plot,values) output

> recorded_data
> ![1738852527161](images/readme/1738852527161.png)
> how to handle this output you can see in `volatge set` ///ссылку на ридми параграф или на сам файл?

## app via QT1

used Qt Designer

```powershell
pip install pyside6
```

quite similar tho its one .py file

![1738867295191](images/readme/1738867295191.png)

## how to make .exe

**Install PyInstaller**: You can use PyInstaller to convert your Python script into an executable. First, install it using pip:

```bash
pip install pyinstaller
```

Navigate to the directory containing your Python script and run:

```bash
pyinstaller --onefile your_script.py
```

This will create a `dist` folder containing the `.exe` file.

## voltage set(example of output data usage)

![voltage](images/readme/1738850634567.png)
For colibration system( via dark counts and gui app get this graph)

idk what is happening here(175-220mV), but after this decided to set sr400 at `DISC lvl=+250 mV` (where limit is `-300 -- + 300`)
