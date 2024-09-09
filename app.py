import sys
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QTableWidget, \
    QTableWidgetItem, QSplitter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import pandas as pd


def find_first_nan(array: np.array, reverse: bool = False):
    first_nan_index = None
    if reverse:
        for i, val in enumerate(array[::-1]):
            if np.isnan(val):
                first_nan_index = len(array) - i  # Correct index for reversed array
                break
        return array[first_nan_index:] if first_nan_index is not None else np.array([])
    else:
        for i, val in enumerate(array):
            if np.isnan(val):
                first_nan_index = i - 1
                break
        return array[:first_nan_index] if first_nan_index is not None else np.array([])


class DraggableLine:
    def __init__(self, ax, x, x_idx, y_range, line_number, canvas, update_callback):
        self.ax = ax
        self.canvas = canvas
        self.update_callback = update_callback
        self.line = Line2D([x, x], y_range, color='gray', linestyle='--', marker='', picker=5)
        self.ax.add_line(self.line)
        self.text = self.ax.text(x, max(y_range), str(line_number), ha='center', va='bottom', color='black',
                                 fontsize=10)
        self.press = None
        self.x = x
        self.x_idx = x_idx
        self.connect()

    def move(self, x_step):
        self.x += x_step
        self.line.set_xdata([self.x, self.x])
        self.canvas.draw()
        self.update_callback(self, self.x)

    def connect(self):
        """ Connect to all the events we need. """
        self.cidpress = self.line.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.line.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.line.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_press(self, event):
        """ On button press we will see if the mouse is over us and store some data. """
        if event.inaxes != self.line.axes: return
        contains, attrd = self.line.contains(event)
        if not contains: return
        x0, y0 = self.line.get_xdata(), self.line.get_ydata()
        self.press = x0, event.xdata

    def on_motion(self, event):
        """ On motion we will move the line if the mouse is over us. """
        if self.press is None: return
        if event.inaxes != self.line.axes: return
        x0, xpress = self.press
        dx = event.xdata - xpress
        self.line.set_xdata(x0 + dx)
        self.text.set_position((x0 + dx, self.text.get_position()[1]))
        self.canvas.draw()

    def on_release(self, event):
        """ On release we will reset the press data. """
        self.press = None
        self.canvas.draw()

    def disconnect(self):
        """ Disconnect all the stored connection ids. """
        self.line.figure.canvas.mpl_disconnect(self.cidpress)
        self.line.figure.canvas.mpl_disconnect(self.cidrelease)
        self.line.figure.canvas.mpl_disconnect(self.cidmotion)


class MainWindow(QMainWindow):
    def __init__(self, x_data, y_data):
        super().__init__()
        self.lines = []
        self.peaks_overlap_threshold = 0.65
        self.setWindowTitle('Interactive Peak Adjustment')

        self.x_data = x_data
        self.y_data = y_data

        self.canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.ax = self.canvas.figure.subplots()
        self.ax.plot(self.x_data, self.y_data, label='Data')
        # self.ax.legend()

        self.toolbar = NavigationToolbar(self.canvas, self)

        self.tableLayout = QVBoxLayout()
        self.table = QWidget()
        self.table.setLayout(self.tableLayout)
        self.tableWidget = QTableWidget(0, 3)
        self.tableWidget.setHorizontalHeaderLabels(["Line #", "2Theta", "Controls"])
        self.tableLayout.addWidget(self.tableWidget)
        self.tableWidget.setBaseSize(300, 600)

        self.detect_peaks()

        self.plotLayout = QVBoxLayout()
        self.plotWidget = QWidget()
        self.plotWidget.setLayout(self.plotLayout)
        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)


        self.mainWidget = QSplitter(Qt.Orientation.Horizontal)
        self.mainWidget.addWidget(self.plotWidget)
        self.mainWidget.addWidget(self.table)

        self.initButtons()

        self.setCentralWidget(self.mainWidget)
        self.resize(800, 600)

    def initButtons(self):
        self.toggle_btn = QPushButton("Change Peak Position", self)
        self.toggle_btn.clicked.connect(self.activate_peak_pos_change)
        self.tableLayout.addWidget(self.toggle_btn)

    def activate_peak_pos_change(self):
        return 0

    def add_line_to_table(self, line):
        row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_position)
        self.tableWidget.setItem(row_position, 0, QTableWidgetItem(str(row_position + 1)))
        self.tableWidget.setItem(row_position, 1, QTableWidgetItem(f"{line.x:.2f}"))

        for row in range(self.tableWidget.rowCount()):
            self.tableWidget.setRowHeight(row, 50)


        # Add line position change buttons
        btn_layout = QHBoxLayout()
        left_btn = QPushButton("<")
        left_btn.setFixedSize(20, 30)
        right_btn = QPushButton(">")
        right_btn.setFixedSize(20, 30)
        btn_layout.addWidget(left_btn)
        btn_layout.addWidget(right_btn)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        self.tableWidget.setCellWidget(row_position, 2, btn_widget)
        self.canvas.draw()

        left_btn.clicked.connect(lambda: self.move_line(row_position, -1))
        right_btn.clicked.connect(lambda: self.move_line(row_position, 1))

    def move_line(self, line_index, direction):
        line = self.lines[line_index]
        curr_x = line.x
        curr_x_idx = line.x_idx
        print(f"curr idx: {curr_x_idx}, curr_x: {curr_x}")
        if curr_x_idx is not None:
            x_step = x_data[curr_x_idx+1] - x_data[curr_x_idx]
            if direction < 0:
                line.move(-x_step)
            else:
                line.move(x_step)
        self.tableWidget.item(line_index, 1).setText(f"{line.x:.2f}")

    def update_line_position(self, line, new_x):
        index = self.lines.index(line)
        self.tableWidget.item(index, 1).setText(f"{new_x:.2f}")

    def detect_peaks(self):
        mean = np.mean(self.y_data)
        noise_threshold = 1
        peak_id_magnitude = 1.7
        self.hills = np.copy(self.y_data)
        self.hills[self.hills < noise_threshold * mean] = np.nan
        window_size = 7
        self.peaks = []
        peak_number = 1

        for i, y in enumerate(self.hills[:-window_size]):
            if not np.isnan(y) and y > peak_id_magnitude * mean:
                if y >= max(self.hills[i:i + window_size]):
                    peak_left = find_first_nan(self.hills[:i], True)
                    if len(peak_left) == 0:
                        # that means that this peak belongs to the previous one, which is not perfectly simmetrical
                        s = find_first_nan(self.hills[i:])
                        self.hills[i: i + len(s)] = np.nan
                        continue
                    peak_left_idx = i - len(peak_left)
                    x = int(1.0 * len(peak_left))
                    if (i + x) >= len(self.hills):
                        x = len(self.hills) - i - 1
                    if np.isnan(self.hills[i + x]):
                        # peak is isolated
                        peak_right = find_first_nan(self.hills[i:])
                        peak_end_idx = i + len(peak_right)
                    elif np.mean(self.hills[i: i + x]) / y > self.peaks_overlap_threshold:
                        # which means that this peak is more flat
                        peak_right = find_first_nan(self.hills[i:])
                        peak_end_idx = i + len(peak_right)
                    else:
                        # overlapping peaks
                        print(f"Overlapping peak")
                        peak_end = min(self.hills[i: i + x])
                        peak_end_idx = i + np.where(self.hills[i: i + x] == peak_end)[0][0]
                        peak_right = self.hills[i:peak_end_idx]

                    self.peaks.append((peak_left_idx, peak_end_idx))
                    self.hills[peak_left_idx:peak_end_idx] = np.nan
                    ymin, ymax = min(self.y_data), max(self.y_data)
                    peak_x = (self.x_data[peak_left_idx] + self.x_data[peak_end_idx]) / 2
                    vline = DraggableLine(self.ax, peak_x, i, [ymin, ymax], peak_number, self.canvas, self.update_line_position)
                    self.lines.append(vline)
                    self.add_line_to_table(vline)
                    peak_number += 1

    def update_peaks(self):
        # This function can be used to refresh the peak calculations after adjustments
        pass


if __name__ == "__main__":
    # Load data from the uploaded file
    read_filepath = fr"C:\Users\Młody\Desktop\[Srv] Doktorat\02. Etap 3 (wł. mech.)\XRD\H13_01.xy"
    save_filepath = read_filepath.replace('.xy', '.csv')
    data = np.loadtxt(read_filepath)  # Replace with the correct file path
    x_data = data[:, 0]
    y_data = data[:, 1]

    # df = pd.DataFrame(data, columns=['2theta', 'Intensity'], dtype=float)
    # df.to_csv(save_filepath, sep=';', index=False)


    app = QApplication(sys.argv)
    window = MainWindow(x_data, y_data)
    window.show()
    sys.exit(app.exec())
