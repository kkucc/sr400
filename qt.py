import sys
import time

import numpy as np
from Control_sr400 import Sr400

import re

from PySide6 import QtWidgets, QtCore, QtUiTools
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# Пример рабочего класса, который выполняет длительную операцию
class Worker(QtCore.QObject):
    finished = QtCore.Signal()
    progress = QtCore.Signal(object)  # можно отправлять данные, если нужно

    def __init__(self, control_sr400, t_set, N_count, dwel_time):
        super().__init__()
        self.control_sr400 = control_sr400
        self.t_set = t_set
        self.N_count = N_count
        self._is_running = True  # Флаг для остановки
        self.dwell_time = dwel_time

    def run(self):
        # Запуск счетчика
        self.control_sr400.start_count()

        # Вместо одного большого time.sleep() делим время на короткие интервалы
        total_sleep = self.t_set * self.N_count + 0.1
        interval = 0.1  # интервал проверки флага остановки
        elapsed = 0.0
        while self._is_running and elapsed < total_sleep:
            time.sleep(min(interval, total_sleep - elapsed))
            elapsed += interval
            # Здесь можно посылать сигналы с прогрессом, если требуется
            self.progress.emit(elapsed)

        # Если операция не была остановлена извне, читаем данные
        if self._is_running:
            Fa = self.control_sr400.single_read('A')
            self.progress.emit(Fa)  # отправляем результат через сигнал

        self.finished.emit()

    def stop(self):
        self._is_running = False
        # Дополнительно можно отправить команду на прерывание в устройстве:
        self.control_sr400.write_com("CR")


class MainWindow(QtWidgets.QMainWindow):
    file_write = False
    N_count = 1
    t_set = 10e-3
    dwel_time = 8e-3

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

        # Это для работы многопоточности с workerом, см. функцию кнопки start

        self.worker_thread = None
        self.worker = None

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

        self.control_sr400 = Sr400(n_counts=self.N_count, t_set=self.t_set, dwel_time=self.dwel_time)

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
        self.control_sr400.numperiod(value)
        print("Новое значение spinbox:", value)

    def start_clicked(self):
        # Запрещаем повторный запуск, если поток уже работает
        if self.worker_thread is not None and self.worker_thread.isRunning():
            print("Задача уже запущена!")
            return
        # Создаем рабочий объект и поток
        self.worker = Worker(self.control_sr400, self.t_set, self.N_count, self.dwel_time)
        self.worker_thread = QtCore.QThread()

        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.progress.connect(self.handle_progress)

        self.worker_thread.start()

    def handle_progress(self, data):
        # Этот метод вызывается из рабочего потока через сигнал.
        # Здесь можно обрабатывать данные, например, обновлять интерфейс.
        self.ydata.append(data)
        print("Прогресс/результат:", data)

    def stop_clicked(self):
        # Если рабочий объект существует, отправляем сигнал остановки
        if self.worker:
            self.worker.stop()
            print("Запрошена остановка процесса.")

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
        # array = list(range(1, n + 1))
        self.xdata = list(range(1, len(self.ydata) + 1))
        # self.ydata

        # Обновляем данные линии
        self.line.set_data(self.xdata, self.ydata)

        # Подгоняем границы осей под новые данные
        self.ax.relim()
        self.ax.autoscale_view()

        # Перерисовываем холст
        self.canvas.draw()

        self.counter += 1

    def closeEvent(self, event):
        """
        Переопределённый метод closeEvent, который вызывается при попытке закрыть окно.
        Здесь мы выводим диалоговое окно с запросом подтверждения.
        """
        reply = QMessageBox.question(
            self,
            "Выход из приложения",
            "Вы действительно хотите выйти?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Здесь можно добавить дополнительную логику перед закрытием
            self.control_sr400.close()
            event.accept()  # Разрешаем закрытие окна
        else:
            event.ignore()  # Отменяем закрытие окна


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
