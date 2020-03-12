import sys
import os

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout, QSizePolicy, QMessageBox, QWidget, QPushButton, QGridLayout, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class App(QMainWindow):

    def __init__(self):
        super(App, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.init_ui()


    def init_ui(self):
        # Initialize data structurs
        self.plot_data = DataStructure()
        '''
        adds in default values
        connects widgets to functions
        '''
        ### Action connections ###
        # Connect load button to dialog box
        self.ui.pushButton_load_data.clicked.connect(self.load_button_handler)

        # Initialize the top graph and make a layout inside the frame
        self.ui.mpl_top = MatplotlibWidget(parent=self.ui.frame_top, axtype='freq_sweep')
        self.ui.frame_top.setLayout(self.set_vlayout(self.ui.mpl_top))
    
        # Initialize the bottom graph and make a layout inside the frame
        self.ui.mpl_bottom = MatplotlibWidget(parent=self.ui.frame_bottom, axtype='freq_sweep')
        self.ui.frame_bottom.setLayout(self.set_vlayout(self.ui.mpl_bottom))

    ### Action Functions ###

    def load_button_handler(self):
        self.open_dialog_box()
    
    def open_dialog_box(self):
        # TODO if the user closes the dialog box and doesn't pick a file
        filename = QFileDialog.getOpenFileName()
        filename[0]
        path = filename[0]
        file_type = self.check_file_type(path)
        self.load_plots(path, file_type)


    def load_plots(self, path, file_type):
        #TODO check if there is missing data
        # TODO check type of file
        # TODO if file is un parsed and raw from the rheometer in single

        # Read the data in
        if file_type == "csv": 
            csv_data = pd.read_csv(path)
        elif file_type == "xlsx":
            csv_data = self.split_covert_xlsx(path)
        else:
            print("Cannot parse file type")

        # Figure out what type of mechanical test it is
        plot_type = self.parse_input_type(csv_data)
        self.clear_all_mpl()
        if plot_type == 'freq_sweep':
            self.plot_freq_sweep(csv_data)
        elif plot_type == 'amplitude_sweep':
            self.plot_amplitude_sweep(csv_data)
        else:
            print("Cannot parse input data")
        
        #TODO make this adjust for different types of data
        #TODO come back and make this regular experession
        
        # TODO add error handling

    def check_file_type(self, path):
        '''
        Check what type of file it is
        '''
        name, ext = os.path.splitext(path)
        if ext == '.csv':
            return "csv"
        elif ext == '.xlsx':
            return "xlsx"
    
    def check_raw_data(self,csv):
        '''
        Check if the data is raw and needs to be cleaned up
        '''
        # TODO fix this
        if 'Point No.' in list(csv.columns) == False:
            # Clean the data up and pass back a new dataframe
            return self.clean_raw_data(csv)

    def split_covert_xlsx(self, path):
        # TODO return multiple dataframes
        '''
        In takes a xslx file and splits the multiple tests into single 
        dataframes- currently set up for a single dataframe
        '''
        temp_data = pd.read_excel(path)
        test_indexes = temp_data.index[temp_data.iloc[:,0]== 'Test:'].tolist()

        for i in range(len(test_indexes)):
            #test_index = int(i)
            # Test if were not the last one
            if test_indexes[i] != test_indexes[-1]:
                # Get the next index
                next_data_index = int(test_indexes[i+1]) - 1
                temp_df = temp_data.iloc[test_indexes[i]:next_data_index,:]
                # Parse just the data
                return self.clean_single_datatable(temp_df)
            # If it's the last number in the list
            else:
                temp_df = temp_data.iloc[i:,:]
                return self.clean_single_datatable(temp_df)

    def clean_single_datatable(self,temp_df):
        '''
        Cleans the raw data from the rheometer into something that can be parsed
        '''
        # Find the index where 'Point No.' occurs so it can be used to 
        # reshape the dataframe
        start_row_index = 0
        # Find where the data starts
        start_row_index = temp_df.index[temp_df.iloc[:,0]== 'Interval data:'].tolist()[0]
        # Find the test name - to be used later when program is extended to multiple tests
        test_name = temp_df.index[temp_df.iloc[:,0]== 'Test:'].tolist()[0]

        # Reshape the dataframe with just the data
        reshape_data = temp_df.iloc[start_row_index:, 1:]

        unit_columns = []
        # Add the unit to the first line and then make it the column names
        for i in range(0, len(reshape_data.iloc[0,:])):
            unit = str(reshape_data.iloc[2,i])
            header = str(reshape_data.iloc[0,i])
            # If the third row doesn't have units
            if unit != 'nan':
                unit_header = header + " " + unit
                unit_columns.append(unit_header)
            else:
                unit_columns.append(header)

        # Set the Columns to the first row and remove the first row
        reshape_data.columns = unit_columns
        reshape_data = reshape_data.iloc[3:,:].reset_index(drop=True)

        # Pass back the cleaned up dataframe
        return reshape_data

    def parse_input_type(self, csv):
        '''
        Look at the columns of the inputed data and determine
        what type of plots to plot 
        '''
        # Get the columns
        cols = csv.columns
        # TODO make this a regular expression
        # List of variables that uniquely identify what type of data it is  
        freq_sweel_list = ['Angular Frequency [rad/s]', 'Storage Modulus [Pa]', 'Loss Modulus [Pa]']
        amplitude_sweep = ['Shear Strain [1]', 'Storage Modulus [Pa]', 'Loss Modulus [Pa]']

        # Check if its a frequency sweep
        if all(elem in cols for elem in freq_sweel_list):
            return 'freq_sweep'
        # Check if its an amplitude sweep
        elif all(elem in cols for elem in amplitude_sweep):
            return "amplitude_sweep"

    ### Plotting Functions ###  
    def plot_freq_sweep(self,csv):
        '''
        Plot the data if the file is a frequency sweep
        '''
        
        self.plot_data.angular_freq = csv['Angular Frequency [rad/s]']
        self.plot_data.gprime = csv['Storage Modulus [Pa]']
        self.plot_data.gprimeprime = csv['Loss Modulus [Pa]']

        self.plot_data.g_star = self.plot_data.calc_g_star()

        # Check the label axis
        plot_labels = self.check_label_text_boxes("freq_sweep")

        # Set it up to plot for frequency sweep
        self.ui.mpl_top.make_mpl_plot(x_data=self.plot_data.angular_freq, y_data=self.plot_data.g_star, title=plot_labels[0],
         xlabel=plot_labels[1], ylabel=plot_labels[2], marker="o")

        self.ui.mpl_bottom.make_mpl_plot(x_data=self.plot_data.angular_freq, y_data=self.plot_data.gprime, marker='^')
        self.ui.mpl_bottom.make_mpl_plot(x_data=self.plot_data.angular_freq, y_data=self.plot_data.gprimeprime, title=plot_labels[3], 
        xlabel=plot_labels[4], ylabel=plot_labels[5], marker="v")

    def plot_amplitude_sweep(self,csv):
        '''
        Plot the data if the file is a amplitude sweep
        '''
        self.plot_data.shear_strain = csv['Shear Strain [1]']
        self.plot_data.gprime = csv['Storage Modulus [Pa]']
        self.plot_data.gprimeprime = csv["Loss Modulus [Pa]"]

        plot_labels = self.check_label_text_boxes("amplitude_sweep")

        # Set it up to plot for amplitude sweep
        self.ui.mpl_top.make_mpl_plot(x_data=self.plot_data.shear_strain, y_data=self.plot_data.gprime, marker="^")
        self.ui.mpl_top.make_mpl_plot(x_data=self.plot_data.shear_strain, y_data=self.plot_data.gprimeprime, title=plot_labels[0],
        xlabel=plot_labels[1], ylabel=plot_labels[2], marker="v")
    
    def create_temp_axis_labels(self):
        '''
        Get the current text within the user input for labels
        '''
        temp_label_list = [self.ui.top_box_title_text.toPlainText(), self.ui.top_box_x_label_text.toPlainText(),
         self.ui.top_box_y_label_text.toPlainText(), self.ui.bottom_box_title_text.toPlainText(), 
         self.ui.bottom_box_x_label_text.toPlainText(), self.ui.bottom_box_y_label_text.toPlainText()]

        return temp_label_list

    def check_label_text_boxes(self, plot_type):
        # Get the current labels
        default_labels = self.default_labels(plot_type)
        current_labels = self.create_temp_axis_labels()
        plot_labels = []
        for i in range(len(current_labels)):
            if current_labels[i] == '':
                plot_labels.append(default_labels[i])
            else:
                plot_labels.append(current_labels[i])
        
        return plot_labels

    def default_labels(self,plot_type):

        freq_sweep_defaults = ['', 'Frequency', 'G Star', '',  'Frequency', "G', G''"]
        amplitude_sweep_defaults = ['', "G', G''",'Strain (%)', '','','']
        if plot_type == 'freq_sweep':
            return freq_sweep_defaults
        elif plot_type == 'amplitude_sweep':
            return amplitude_sweep_defaults


    def title_axis_labels(self):

        if self.ui.top_box_title_text.toPlainText() == "":
            print('blank')

    def clear_all_mpl(self):
        '''
        clear lines in all mpls
        '''
        # find all mpl objects
        mpl_list = self.findChildren(MatplotlibWidget)
        # clear mpl_sp
        for mpl in mpl_list:
            mpl.clr_lines()
               
    ### Setting up Layouts ###
    def set_vlayout(self, widget):
        '''set a dense layout for frame with a single widget'''
        vbox = QGridLayout()
        vbox.setContentsMargins(0, 0, 0, 0) # set layout margins (left, top, right, bottom)
        vbox.addWidget(widget)
        return vbox



# Define a class to define the data 
class DataStructure():
    def __init__(self):

        #TODO set this up to receive multipe data types
        self.angular_freq =[]
        self.gprime =[]
        self.gprimeprime = []
        self.g_star = []
        
        self.shear_strain = []

    def calc_g_star(self):
        return ((np.array(self.gprime)**2) + (np.array(self.gprimeprime)**2))**0.5

class MatplotlibWidget(QWidget):
    '''
    Overlays matplotlib figure onto different parts of the gui
    '''
    def __init__(self, parent=None, axtype='', title='', xlabel='', ylabel='', xlim=None, ylim=None, xscale='linear', yscale='linear', showtoolbar=True, dpi=100, **kwargs):
        super(MatplotlibWidget, self).__init__(parent)
        self.axtype = axtype
        #self.axtype = axtype
        self.leg = ''

        # Make the Figure
        self.fig = Figure(tight_layout={'pad': 0.05}, dpi=dpi)

        # Make the Canvas
        self.canvas = FigureCanvas(self.fig)
        # Have it resize to the Gui
        self.canvas.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.canvas.setFocus()

        self.vbox = QVBoxLayout()
        self.vbox.setContentsMargins(0, 0, 0, 0) # set layout margins
        self.vbox.addWidget(self.canvas)
        self.setLayout(self.vbox)

        # TODO maybe- add tool bar

        # Set the inital axes
        self.ax = self.fig.add_subplot(111, facecolor='none')

        # Draw the canvas
        self.canvas_draw()

    def make_mpl_plot(self, title='', xlabel='', ylabel='', xlim=None, ylim=None, xscale='log', yscale='log', x_data=None, y_data=None, marker='.', *args, **kwargs):
        
        
        self.ax.plot(x_data, y_data, marker=marker)

        self.ax.set_xscale(xscale)
        self.ax.set_yscale(yscale)

        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        self.ax.set_title(title)

        # Redraw the new scale
        self.canvas_draw()

    def clr_lines(self):
        # TODO look into clearing the whole plot before 
        '''
        Clear all lines in all mpls
        '''
        line_list = self.ax.get_lines()
        # Clear each line in the figure
        for line in line_list:
            self.ax.lines.remove(line)
        
        #self.reset_ax_lim(ax)
        self.canvas_draw()

    def canvas_draw(self):
        '''
        redraw canvas after data changed
        '''
        self.canvas.draw()
        self.canvas.flush_events() # flush the GUI events 
    def reset_ax_lim(self, ax):
        '''
        reset the lim of ax
        this change the display and where home button goes back to
        '''
        ax.relim(visible_only=True)
        ax.autoscale_view(True,True,True)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1087, 745)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.frame_top = QtWidgets.QFrame(self.centralwidget)
        self.frame_top.setGeometry(QtCore.QRect(520, 20, 481, 311))
        self.frame_top.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_top.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_top.setObjectName("frame_top")
        self.frame_bottom = QtWidgets.QFrame(self.centralwidget)
        self.frame_bottom.setGeometry(QtCore.QRect(520, 360, 481, 311))
        self.frame_bottom.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_bottom.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_bottom.setObjectName("frame_bottom")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(120, 50, 301, 41))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.load_data_bar = QtWidgets.QLineEdit(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.load_data_bar.sizePolicy().hasHeightForWidth())
        self.load_data_bar.setSizePolicy(sizePolicy)
        self.load_data_bar.setText("")
        self.load_data_bar.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.load_data_bar.setReadOnly(True)
        self.load_data_bar.setObjectName("load_data_bar")
        self.verticalLayout.addWidget(self.load_data_bar)
        self.pushButton_load_data = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_load_data.setGeometry(QtCore.QRect(230, 100, 81, 31))
        self.pushButton_load_data.setObjectName("pushButton_load_data")
        self.replot_data_button = QtWidgets.QPushButton(self.centralwidget)
        self.replot_data_button.setGeometry(QtCore.QRect(210, 590, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.replot_data_button.setFont(font)
        self.replot_data_button.setObjectName("replot_data_button")
        self.frame = QtWidgets.QFrame(self.centralwidget)
        self.frame.setGeometry(QtCore.QRect(120, 150, 311, 431))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.top_box_title_text = QtWidgets.QPlainTextEdit(self.frame)
        self.top_box_title_text.setGeometry(QtCore.QRect(53, 0, 201, 31))
        self.top_box_title_text.setObjectName("top_box_title_text")
        self.top_box_x_label_text = QtWidgets.QPlainTextEdit(self.frame)
        self.top_box_x_label_text.setGeometry(QtCore.QRect(53, 60, 201, 31))
        self.top_box_x_label_text.setObjectName("top_box_x_label_text")
        self.top_box_y_label_text = QtWidgets.QPlainTextEdit(self.frame)
        self.top_box_y_label_text.setGeometry(QtCore.QRect(53, 120, 201, 31))
        self.top_box_y_label_text.setObjectName("top_box_y_label_text")
        self.bottom_box_title_text = QtWidgets.QPlainTextEdit(self.frame)
        self.bottom_box_title_text.setGeometry(QtCore.QRect(53, 200, 201, 31))
        self.bottom_box_title_text.setObjectName("bottom_box_title_text")
        self.bottom_box_y_label_text = QtWidgets.QPlainTextEdit(self.frame)
        self.bottom_box_y_label_text.setGeometry(QtCore.QRect(53, 320, 201, 31))
        self.bottom_box_y_label_text.setObjectName("bottom_box_y_label_text")
        self.bottom_box_x_label_text = QtWidgets.QPlainTextEdit(self.frame)
        self.bottom_box_x_label_text.setGeometry(QtCore.QRect(53, 260, 201, 31))
        self.bottom_box_x_label_text.setObjectName("bottom_box_x_label_text")
        self.top_plot_title = QtWidgets.QLabel(self.frame)
        self.top_plot_title.setGeometry(QtCore.QRect(120, 30, 61, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.top_plot_title.setFont(font)
        self.top_plot_title.setObjectName("top_plot_title")
        self.top_plot_xlabel = QtWidgets.QLabel(self.frame)
        self.top_plot_xlabel.setGeometry(QtCore.QRect(120, 90, 131, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.top_plot_xlabel.setFont(font)
        self.top_plot_xlabel.setObjectName("top_plot_xlabel")
        self.top_plot_ylabel = QtWidgets.QLabel(self.frame)
        self.top_plot_ylabel.setGeometry(QtCore.QRect(120, 150, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.top_plot_ylabel.setFont(font)
        self.top_plot_ylabel.setObjectName("top_plot_ylabel")
        self.bottom_plot_title = QtWidgets.QLabel(self.frame)
        self.bottom_plot_title.setGeometry(QtCore.QRect(120, 230, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.bottom_plot_title.setFont(font)
        self.bottom_plot_title.setObjectName("bottom_plot_title")
        self.bottom_plot_xlabel = QtWidgets.QLabel(self.frame)
        self.bottom_plot_xlabel.setGeometry(QtCore.QRect(110, 290, 141, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.bottom_plot_xlabel.setFont(font)
        self.bottom_plot_xlabel.setObjectName("bottom_plot_xlabel")
        self.bottom_plot_xlabel_2 = QtWidgets.QLabel(self.frame)
        self.bottom_plot_xlabel_2.setGeometry(QtCore.QRect(110, 350, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.bottom_plot_xlabel_2.setFont(font)
        self.bottom_plot_xlabel_2.setObjectName("bottom_plot_xlabel_2")
        self.export_top_plot_button = QtWidgets.QPushButton(self.centralwidget)
        self.export_top_plot_button.setGeometry(QtCore.QRect(110, 640, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.export_top_plot_button.setFont(font)
        self.export_top_plot_button.setObjectName("export_top_plot_button")
        self.export_bottom_plot_button = QtWidgets.QPushButton(self.centralwidget)
        self.export_bottom_plot_button.setGeometry(QtCore.QRect(310, 640, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.export_bottom_plot_button.setFont(font)
        self.export_bottom_plot_button.setObjectName("export_bottom_plot_button")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1087, 18))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.load_data_bar.setPlaceholderText(_translate("MainWindow", "<output filename>"))
        self.pushButton_load_data.setText(_translate("MainWindow", "Load Data"))
        self.replot_data_button.setText(_translate("MainWindow", "Replot Data"))
        self.top_plot_title.setText(_translate("MainWindow", "Top Plot Title"))
        self.top_plot_xlabel.setText(_translate("MainWindow", "Top Plot X Label"))
        self.top_plot_ylabel.setText(_translate("MainWindow", "Top Plot Y Label"))
        self.bottom_plot_title.setText(_translate("MainWindow", "Bottom Plot Title"))
        self.bottom_plot_xlabel.setText(_translate("MainWindow", "Bottom Plot X Label"))
        self.bottom_plot_xlabel_2.setText(_translate("MainWindow", "Bottom Plot X Label"))
        self.export_top_plot_button.setText(_translate("MainWindow", "Export Top Plot"))
        self.export_bottom_plot_button.setText(_translate("MainWindow", "Export Bottom Plot"))


        
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    rheo_app = App()
    rheo_app.show()
    sys.exit(app.exec_())
