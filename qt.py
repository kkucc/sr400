import sys
import numpy as np

import re

from PySide6 import QtWidgets, QtCore, QtUiTools
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MainWindow(QtWidgets.QMainWindow):
    file_write = False
    N_count = 1
    t_set = 10e-5
    dwel_time = 10e-5

    def __init__(self):
        super().__init__()

        # Загрузка интерфейса из файла main.ui с помощью QUiLoader
        loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile("main.ui")
        if not ui_file.open(QtCore.QFile.ReadOnly):
            print("Не удалось открыть файл main.ui")
            sys.exit(-1)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Если загруженный объект имеет атрибут centralwidget, используем его;
        # иначе – используем сам загруженный объект.
        if hasattr(self.ui, "centralwidget"):
            self.setCentralWidget(self.ui)
        else:
            self.setCentralWidget(self.ui)

        # Поиск виджета для вывода графика (objectName должен быть "plotWidget")
        self.plot_widget = self.findChild(QtWidgets.QWidget, "plotWidget")
        if self.plot_widget is None:
            print("В интерфейсе отсутствует виджет с objectName 'plotWidget'")
            sys.exit(-1)

        # Создание объекта Figure и его интеграция в plot_widget через FigureCanvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Создаем layout для plot_widget и добавляем в него canvas
        layout = QtWidgets.QVBoxLayout(self.plot_widget)
        layout.addWidget(self.canvas)

        # Создаём ось для рисования графика и начальную линию
        self.ax = self.figure.add_subplot(111)
        self.line, = self.ax.plot([], [], 'r-')  # красная линия

        # Инициализируем данные для графика
        self.xdata = []
        self.ydata = []
        self.counter = 0

        # Настраиваем таймер для обновления графика каждые 1000 мс (1 секунда)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # Поиск кнопки в интерфейсе (objectName кнопки должен быть "StartButton")
        self.StartButton = self.ui.findChild(QtWidgets.QPushButton, "Start_button")
        self.StopButton = self.ui.findChild(QtWidgets.QPushButton, "Stop_button")

        self.file_check = self.ui.findChild(QtWidgets.QCheckBox, "File")
        self.live_check = self.ui.findChild(QtWidgets.QCheckBox, "live_preview")

        self.n_counts_box = self.ui.findChild(QtWidgets.QSpinBox, "N_counts")

        self.accumulate_time_line = self.ui.findChild(QtWidgets.QLineEdit, "accumulation")
        self.dwel_time_line = self.ui.findChild(QtWidgets.QLineEdit, "dwel")

        self.text_chanel_A = self.ui.findChild(QtWidgets.QLabel, "Chanel_text_A")
        self.text_chanel_B = self.ui.findChild(QtWidgets.QLabel, "Chanel_text_B")

        # Подключаем сигналы

        self.StartButton.clicked.connect(self.start_clicked)
        self.StartButton.clicked.connect(self.stop_clicked)

        self.file_check.stateChanged.connect(self.filewrite)
        self.live_check.stateChanged.connect(self.live)

        self.n_counts_box.valueChanged.connect(self.nCounts)

        self.accumulate_time_line.editingFinished.connect(self.accumulate_time_set)
        self.dwel_time_line.editingFinished.connect(self.dwel_time_set)

    def accumulate_time_set(self):
        self.t_set = self.extract_number(self.accumulate_time_line.text())
        print("Редактирование завершено. Текущий текст:", self.t_set)

    def dwel_time_set(self):
        self.dwel_time = self.extract_number(self.dwel_time_line.text())
        print("Редактирование завершено. Текущий текст:", self.dwel_time)

    def filewrite(self, state):
        self.file_write = (state == 2)
        # state может быть Qt.Unchecked (0) или Qt.Checked (2)
        if state == 2:
            print("Checkbox отмечен")
        else:
            print("Checkbox не отмечен")

    def live(self, state):
        self.file_write = (state == 2)
        # state может быть Qt.Unchecked (0) или Qt.Checked (2)
        if state == 2:
            print("Checkbox отмечен")
        else:
            print("Checkbox не отмечен")

    def nCounts(self, value):
        self.N_count = value
        print("Новое значение spinbox:", value)

    def start_clicked(self):
        print("start")

    def stop_clicked(self):
        pass

    def extract_number(self, text: str) -> float:
        # Регулярное выражение:
        # ^\s*              - начало строки, возможные пробелы
        # (?:(?P<mul>\d+(?:\.\d+)?)\s*\*\s*)? - опционально: группа "mul" для множителя (целое или дробное число) и символ '*'
        # (?P<num>\d+(?:\.\d+)?(?:e[-+]?\d+)?|\.\d+(?:e[-+]?\d+)?) - группа "num" для основания числа:
        #       либо число с целой частью и опциональной дробной частью, с возможной экспонентой,
        #       либо число начинающееся с точки (например, .5)
        # \s*$              - возможные пробелы в конце строки и конец строки.
        pattern = r'^\s*(?:(?P<mul>\d+(?:\.\d+)?)\s*\*\s*)?(?P<num>\d+(?:\.\d+)?(?:e[-+]?\d+)?|\.\d+(?:e[-+]?\d+)?)\s*$'

        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if not match:
            raise ValueError("Строка не соответствует ожидаемому формату числа.")

        num_str = match.group("num")
        base_value = float(num_str)  # преобразуем основание числа в float

        mul_str = match.group("mul")
        if mul_str:
            # если имеется множитель, перемножаем его на основание
            value = float(mul_str) * base_value
        else:
            value = base_value

        return value

    def update_plot(self):
        """Метод обновления графика."""
        # Добавляем новую точку (например, значение синуса)
        self.xdata.append(self.counter)
        self.ydata.append(np.sin(self.counter / 10.0))

        # Обновляем данные линии
        self.line.set_data(self.xdata, self.ydata)

        # Подгоняем границы осей под новые данные
        self.ax.relim()
        self.ax.autoscale_view()

        # Перерисовываем холст
        self.canvas.draw()

        self.counter += 1


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
