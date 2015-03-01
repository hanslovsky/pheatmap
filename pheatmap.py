import sys
from PyQt4 import QtGui

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib
import matplotlib.pyplot as plt

import numpy as np

import os

import pandas
import pandas.io as io

import seaborn as sns

import random

import vigra

matplotlib.rc('text', usetex=False) # no tex escape so far!

class MplPlot(QtGui.QDialog):
    def __init__(self, parent=None):
        super(MplPlot, self).__init__(parent)

        self.hm = None

        # initial plot parameters
        self.xticklabelOptions = 'none'
        self.yticklabelOptions = 'none'
        self.labelStep         = 10

        # a figure instance to plot on
        self.figure = plt.figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar( self.canvas, self )

        # Plot button
        self.button = QtGui.QPushButton('Plot')
        self.button.clicked.connect(self.plot)

        # Save button
        self.saveButton = QtGui.QPushButton('Save')
        self.saveButton.clicked.connect( self._save )

        self.grid = QtGui.QGridLayout()

        # File stuff
        self.browseButton  = QtGui.QPushButton('Browse')
        self.browseButton.clicked.connect(self._get_filename)
        self.fileNameField = QtGui.QLineEdit()
        self.fileNameField.setPlaceholderText( 'Path to file containing data (csv or image)' )

        self.grid.addWidget(self.button, 0, 0)
        self.grid.addWidget(self.saveButton, 0, 1)
        self.grid.addWidget(self.browseButton, 1, 0)
        self.grid.addWidget(self.fileNameField, 1, 1)

        # axis tags
        self.xaxistagsGroup        = QtGui.QButtonGroup(self)
        self.yaxistagsGroup        = QtGui.QButtonGroup(self)
        axisLabelTypes             = 'None', 'From file', 'Numbers'
        self.xaxistagsRadioButtons = [ QtGui.QRadioButton( l ) for l in axisLabelTypes ]
        self.xaxistagsLayout       = QtGui.QGridLayout()
        self.yaxistagsRadioButtons = [ QtGui.QRadioButton( l ) for l in axisLabelTypes ]
        self.yaxistagsLayout       = QtGui.QGridLayout()
        self.xaxistagsStepField    = QtGui.QLineEdit()
        self.yaxistagsStepField    = QtGui.QLineEdit()
        self.xaxistagsLabel        = QtGui.QLineEdit()
        self.yaxistagsLabel        = QtGui.QLineEdit()

        self.xaxistagsLabel.setReadOnly( True )
        self.yaxistagsLabel.setReadOnly( True )
        self.xaxistagsLabel.setText( "Label type for x-axis ticks" )
        self.yaxistagsLabel.setText( "Label type for y-axis ticks" )
        
        self.xaxistagsStepField.setPlaceholderText( 'Step for axistags (default=1)' )
        self.yaxistagsStepField.setPlaceholderText( 'Step for axistags (default=1)' )

        self.xaxistagsStepField.setReadOnly( True )
        self.yaxistagsStepField.setReadOnly( True )
        
        
        
        indexX, indexY = 0, 0
        self.xaxistagsLayout.addWidget( self.xaxistagsLabel, 0, indexX )
        self.yaxistagsLayout.addWidget( self.yaxistagsLabel, 0, indexY )
        indexX += 1
        indexY += 1
        
        for rb in self.xaxistagsRadioButtons:
            self.xaxistagsLayout.addWidget( rb, 0, indexX )
            self.xaxistagsGroup.addButton( rb )
            indexX += 1
        for rb in self.yaxistagsRadioButtons:
            self.yaxistagsLayout.addWidget( rb, 0, indexY )
            self.yaxistagsGroup.addButton( rb )
            indexY += 1

        self.xaxistagsLayout.addWidget( self.xaxistagsStepField, 0, indexX )
        self.yaxistagsLayout.addWidget( self.yaxistagsStepField, 0, indexY )

        self.xaxistagsRadioButtons[0].setChecked( True )
        self.yaxistagsRadioButtons[0].setChecked( True )

        self.xaxistagsRadioButtons[2].toggled.connect( lambda isEnabled: self.xaxistagsStepField.setReadOnly( not isEnabled ) ) # why not isEnabled?
        self.yaxistagsRadioButtons[2].toggled.connect( lambda isEnabled: self.yaxistagsStepField.setReadOnly( not isEnabled ) ) # why not isEnabled?

        self.axestagsRadioButtons = ( self.xaxistagsRadioButtons, self.yaxistagsRadioButtons )

        # set the layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(self.grid)
        layout.addLayout(self.xaxistagsLayout)
        layout.addLayout(self.yaxistagsLayout)
        self.setLayout( layout )

    def plot(self):
        dataFrame = self._read_file()
        data      = dataFrame.as_matrix()

        # clear
        plt.clf()

        # create an axis
        ax = self.figure.add_subplot(111)

        # discards the old graph
        ax.hold(False)

        # plot data
        xticklabels, yticklabels = self._get_ticklabels( dataFrame )
        self.hm = sns.heatmap( data, ax=ax, linewidths=0, square=True, xticklabels = xticklabels, yticklabels = yticklabels )

        # refresh canvas
        self.canvas.draw()

    def _save(self):
        if self.hm is None:
            dialog = QtGui.QErrorMessage( self )
            dialog.showMessage( "No plotting done yet." )
        else:
            dialog = QtGui.QFileDialog(self)
            dialog.setWindowTitle('Save File')
            dialog.setFileMode(QtGui.QFileDialog.AnyFile)
            if dialog.exec_() == QtGui.QDialog.Accepted:
                filename = str( dialog.selectedFiles()[0] )
                if os.path.isfile( filename ):
                    doOverwrite = QtGui.QMessageBox.question( self,
                                                              "Overwrite?",
                                                              "File exists - overwrite?",
                                                              QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                                              QtGui.QMessageBox.No )
                    if doOverwrite == QtGui.QMessageBox.No:
                        return
                self.figure.savefig( filename, bbox_inches='tight' )
                statusMessage = QtGui.QMessageBox.question( self,
                                                            "Saved file",
                                                            "Saved file to %s" % filename )
                


    def _get_filename(self):
        dialog = QtGui.QFileDialog(self)
        dialog.setWindowTitle('Open File')
        dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            filename = dialog.selectedFiles()[0]
            self.fileNameField.setText( filename )

    def _get_ticklabels(self, dataFrame ):
        xtickLabelOption = 0
        ytickLabelOption = 0
        for o in self.xaxistagsRadioButtons:
            if o.isChecked():
                break
            xtickLabelOption += 1
        for o in self.yaxistagsRadioButtons:
            if o.isChecked():
                break
            ytickLabelOption += 1
        stepX, stepY = int( self.xaxistagsStepField.text() or '1' ), int( self.yaxistagsStepField.text() or '1' )
        xticklabels, yticklabels = ( self._get_ticklabel( dataFrame, 0, xtickLabelOption, stepX ),
                                     self._get_ticklabel( dataFrame, 1, ytickLabelOption, stepY ) )
        return xticklabels, yticklabels

    def _get_ticklabel( self, dataFrame, axis, option, step ):
        if option == 0:
            labels = [''] * dataFrame.shape[axis]
        elif option == 1:
            if axis == 1:
                labels = dataFrame.index
            elif axis == 0:
                labels = dataFrame.columns
        elif option == 2:
            labels = [''] * dataFrame.shape[axis]
            labels[ ::step ] = xrange( 0, dataFrame.shape[axis], step )
        return labels

    def _read_file( self ):
        filename = str( self.fileNameField.text() )
        if filename.endswith('.csv'):
            header    = 0 if self.axestagsRadioButtons[0][1].isChecked() else None
            index_col = 0 if self.axestagsRadioButtons[1][1].isChecked() else None
            dataFrame = io.parsers.read_csv( filename, index_col=index_col, header=None )#, header=header)
        else:
            data = vigra.impex.readImage( filename ).squeeze()
            cols = [''] * data.shape[1]
            rows = [''] * data.shape[0]
            dataFrame = pandas.dataFrame( data, columns = cols, rows = rows )
        return dataFrame

    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    main = MplPlot()
    main.show()

    sys.exit(app.exec_())
