import sys
import numpy as np

from PySide6 import QtWidgets, QtCore, QtUiTools
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MainWindow(QtWidgets.QMainWindow):
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

        # Поиск кнопки в интерфейсе (objectName кнопки должен быть "myButton")
        self.myButton = self.ui.findChild(QtWidgets.QPushButton, "Start_button")
        self.myButton.clicked.connect(self.start_clicked)

    def start_clicked(self):
        pass

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
