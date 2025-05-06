import sys
import time
import csv
import datetime

import numpy as np
from Control_sr400 import Sr400

import re

from PySide6 import QtWidgets, QtCore, QtUiTools
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class WorkerLive(QtCore.QObject):
    finished = QtCore.Signal(object)
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
        # self.control_sr400.start_count()

        # Вместо одного большого time.sleep() делим время на короткие интервалы
        self.control_sr400.tset(self.t_set)
        time.sleep(0.01)
        self.control_sr400.write_com("NP 1")
        time.sleep(self.t_set + 0.1)
        print("start")
        while self._is_running:
            try:
                self.control_sr400.write_com("CR")
                Fa = self.control_sr400.sr4.query("FA")
                time.sleep(self.t_set + 0.001)
                Fa = list(map(int, Fa.rstrip().split(',')))

                self.control_sr400.write_com("CR")
                Fb = self.control_sr400.sr4.query("FB")
                time.sleep(self.t_set + self.dwell_time + 0.001)
                Fb = list(map(int, Fb.rstrip().split(',')))
                
                self.progress.emit((Fa, Fb))
            except Exception as e:
                print(e)
                break
        self.finished.emit(None)

    def stop(self):
        self._is_running = False
        # Дополнительно можно отправить команду на прерывание в устройстве:
        self.control_sr400.write_com("CR")


# Пример рабочего класса, который выполняет длительную операцию QThread: Destroyed while thread is still running
class Worker(QtCore.QObject):
    finished = QtCore.Signal(object)
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
        total_sleep = self.t_set * self.N_count + self.dwell_time * self.N_count + 0.1  # + self.dwell_time * self.N_count
        interval = 1e-1  # интервал проверки флага остановки
        elapsed = 0.0
        while self._is_running and elapsed < total_sleep:
            time.sleep(min(interval, total_sleep - elapsed))
            elapsed += interval
            # Здесь можно посылать сигналы с прогрессом, если требуется
        print("чтение")
        # Если операция не была остановлена извне, читаем данные
        if self._is_running:
            try:
                Fa = self.control_sr400.single_read('A')
                Fb = self.control_sr400.single_read('B')
                # self.progress.emit(Fa)  # отправляем результат через сигнал
                self.progress.emit(Fa)
                self.finished.emit((Fa, Fb))
            except:
                self.finished.emit(None)
        else:
            self.finished.emit(None)

    def stop(self):
        self._is_running = False
        # Дополнительно можно отправить команду на прерывание в устройстве:
        self.control_sr400.write_com("CR")


class MainWindow(QtWidgets.QMainWindow):
    file_write = False
    live_prev = False
    N_count = 1
    t_set = 10e-3
    dwel_time = 8e-3

    N_Files = 1

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
        # Линия для канала A (например, красная)
        self.line, = self.ax.plot([], [], 'r-', label="Канал A")
        # Линия для канала B (например, синяя)
        self.line2, = self.ax.plot([], [], 'b-', label="Канал B")
        # Добавляем легенду
        self.ax.legend()

        # Инициализируем данные для графика
        self.xdata = []
        self.ydata = []
        self.ydata2 = []  # для канала B
        self.counter = 0

        # Настраиваем таймер для обновления графика каждые 500 мс (0.5 секунд)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # Поиск кнопки в интерфейсе (objectName кнопки должен быть "StartButton")
        self.StartButton = self.ui.findChild(QtWidgets.QPushButton, "Start_button")
        self.StopButton = self.ui.findChild(QtWidgets.QPushButton, "Stop_button")

        self.file_check = self.ui.findChild(QtWidgets.QCheckBox, "File")
        self.live_check = self.ui.findChild(QtWidgets.QCheckBox, "live_preview")

        self.n_counts_box = self.ui.findChild(QtWidgets.QSpinBox, "N_counts")

        self.files_n = self.ui.findChild(QtWidgets.QSpinBox, "Files")

        self.accumulate_time_line = self.ui.findChild(QtWidgets.QLineEdit, "accumulation")
        self.dwel_time_line = self.ui.findChild(QtWidgets.QLineEdit, "dwel")

        self.text_chanel_A = self.ui.findChild(QtWidgets.QLabel, "Chanel_text_A")
        self.text_chanel_B = self.ui.findChild(QtWidgets.QLabel, "Chanel_text_b")

        # Подключаем сигналы

        self.StartButton.clicked.connect(self.start_clicked)
        self.StopButton.clicked.connect(self.stop_clicked)

        self.file_check.stateChanged.connect(self.filewrite)
        self.live_check.stateChanged.connect(self.live)

        self.n_counts_box.valueChanged.connect(self.nCounts)
        self.files_n.valueChanged.connect(self.Files_n)

        self.accumulate_time_line.editingFinished.connect(self.accumulate_time_set)
        self.dwel_time_line.editingFinished.connect(self.dwel_time_set)

        self.control_sr400 = Sr400(n_counts=self.N_count, t_set=self.t_set, dwel_time=self.dwel_time)


    def accumulate_time_set(self):
        self.t_set = self.extract_number(self.accumulate_time_line.text())
        self.control_sr400.tset(self.t_set)
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
        self.live_prev = (state == 2)
        # state может быть Qt.Unchecked (0) или Qt.Checked (2)
        if state == 2:
            print("Checkbox отмечен")
        else:
            print("Checkbox не отмечен")

    def nCounts(self, value):

        self.N_count = value
        self.control_sr400.numperiod(value)
        print("Новое значение spinbox:", value)

    def Files_n(self, value):        
        self.N_Files = value
        print("Новое значение spinbox:", value)


    def start_clicked(self):

        if self.live_prev is False:
            if self.worker_thread is not None:
                if self.worker_thread.isRunning():
                    print("Задача уже запущена!")
                    return
                else:
                    self.worker_thread.deleteLater()  # Удаляем старый поток, если он завершен

            self.worker = Worker(self.control_sr400, self.t_set, self.N_count, self.dwel_time)
            self.worker_thread = QtCore.QThread()

            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.progress.connect(self.handle_progress)
            self.worker.finished.connect(self.handle_result)

            self.worker_thread.start()

            self.ydata = []
            self.ydata2 = []
        else:
            self.ydata = []
            self.ydata2 = []
            if self.worker_thread is not None:
                if self.worker_thread.isRunning():
                    print("Задача уже запущена!")
                    return
                else:
                    self.worker_thread.deleteLater()  # Удаляем старый поток, если он завершен

            self.worker = WorkerLive(self.control_sr400, self.t_set, self.N_count, self.dwel_time)
            self.worker_thread = QtCore.QThread()

            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.progress.connect(self.handle_progress_live)
            self.worker.finished.connect(self.handle_result_live)

            self.worker_thread.start()

            self.ydata = []
            self.ydata2 = []

    def handle_progress_live(self, data):
        # Этот метод вызывается из рабочего потока через сигнал.
        # Здесь можно обрабатывать данные, например, обновлять интерфейс.
        if data is not None:
            dataA, dataB = data
            self.ydata.append(dataA[0])
            self.ydata2.append(dataB[0])
            # print("Прогресс/результат:", self.ydata, len(self.ydata))
        else:
            print("Работа остановлена до завершения измерения.")
        # Обнуляем ссылки, чтобы поток и объект worker могли быть удалены сборщиком мусора

    def handle_result_live(self, data):
        self.worker = None
        self.worker_thread = None

    def handle_result(self, data):
        # Этот метод вызывается из рабочего потока через сигнал.
        # Здесь можно обрабатывать данные, например, обновлять интерфейс.
        if data is not None:
            dataA, dataB = data

            dataA = [item[0] for item in dataA]
            dataB = [item[0] for item in dataB]

            avrA = sum(dataA) / self.N_count
            avrB = sum(dataB) / self.N_count

            self.text_chanel_A.setText(f"Chanel A: {avrA}")
            self.text_chanel_B.setText(f"Chanel B: {avrB}")

            self.ydata.extend(dataA)
            self.ydata2.extend(dataB)
            self.xdata = list(range(1, len(self.ydata) + 1))
            # print("Прогресс/результат:", self.ydata, len(self.ydata))
            if self.file_write:
                # Получаем текущее время
                current_time = datetime.datetime.now()
                # Форматируем строку с датой и временем
                filename = current_time.strftime(f"log\\%Y-%m-%d_%H-%M-%S_{self.N_Files}.csv")
                with open(filename, "w", newline='', encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    # Записываем заголовок (опционально)
                    writer.writerow(["N", "Counts"])
                    # Записываем данные
                    for xi, yi in zip(self.xdata, self.ydata):
                        writer.writerow([xi, yi])
        else:
            print("Работа остановлена до завершения измерения.")
        # Обнуляем ссылки, чтобы поток и объект worker могли быть удалены сборщиком мусора
        self.worker = None
        self.worker_thread = None

    def handle_progress(self, data):
        print("Прогресс/результат:", data)
        # Этот метод вызывается из рабочего потока через сигнал.
        # Здесь можно обрабатывать данные, например, обновлять интерфейс.
        # self.ydata.append(data)
        # print("Прогресс/результат:", data)

    def stop_clicked(self):
        # Если рабочий объект существует, отправляем сигнал остановки
        if self.worker:
            self.worker.stop()
            print("Запрошена остановка процесса.")
        else:
            self.worker = None
            self.worker_thread = None
            print("Нет активного процесса для остановки.")

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
        self.line2.set_data(self.xdata, self.ydata2)

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
