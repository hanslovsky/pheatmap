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

class RGBDialog(QtGui.QDialog):
    def __init__(self, title, reverse, isLight, parent=None):
        super(RGBDialog, self).__init__(parent)
        self.setWindowTitle( title )

        self.title  = title
        self.grid   = QtGui.QGridLayout()
        self.R      = QtGui.QLineEdit()
        self.G      = QtGui.QLineEdit()
        self.B      = QtGui.QLineEdit()
        self.N      = QtGui.QLineEdit()
        self.ok     = QtGui.QPushButton('Ok')
        self.cancel = QtGui.QPushButton('Cancel')
        self.R.setPlaceholderText( '0 <= red <= 255' )
        self.G.setPlaceholderText( '0 <= green <= 255' )
        self.B.setPlaceholderText( '0 <= blue <= 255' )
        self.N.setPlaceholderText( '0 < number of colors in palette' )

        self.grid.addWidget( self.R, 0, 0, 1, 2 )
        self.grid.addWidget( self.G, 0, 2, 1 ,2 )
        self.grid.addWidget( self.B, 0, 4, 1, 2 )
        self.grid.addWidget( self.N, 0, 6, 1, 2 )

        self.grid.addWidget( self.ok, 1, 0, 1, 2 )
        self.grid.addWidget( self.cancel, 1, 6, 1, 2 )
        
        self.setLayout( self.grid )

        self.reverse = reverse

        self.cmap_func = sns.light_palette if isLight else sns.dark_palette

        self.cancel.clicked.connect( self.reject )
        self.ok.clicked.connect( self._create_cmap )

    def _create_cmap( self ):
        r = int( str( self.R.text() ) )
        g = int( str( self.G.text() ) )
        b = int( str( self.B.text() ) )
        n = int( str( self.N.text() ) )
        rgb = ( r, g, b )
        self.cmap = self.cmap_func( tuple( c / 255.0 for c in rgb ), n_colors = n, as_cmap = True, reverse = self.reverse  )
        self.title = '%s - %d,%d,%d - %d colors' % ( ( self.title, ) + rgb + ( n, ) )
        self.accept()
        


class CmapDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(CmapDialog, self).__init__(parent)

        self.setWindowTitle( 'Colormap Chooser' )

        self.selectionRadioButtons = QtGui.QButtonGroup(self)
        self.choices               = [ 'Standard', 'Light Palette', 'Dark Palette' ]
        self.buttons               = [ QtGui.QRadioButton( l ) for l in self.choices ]
        self.buttonLayout          = QtGui.QHBoxLayout()
        self.layout                = QtGui.QVBoxLayout()
        self.yesNoLayout           = QtGui.QHBoxLayout()
        self.reverseCheck          = QtGui.QCheckBox( 'Reverse color map?' )
        self.cmap_name             = ''
        self.cmap                  = None
        
        for b in self.buttons:
            self.selectionRadioButtons.addButton( b )
            self.buttonLayout.addWidget( b )
        self.buttons[0].setChecked( True )
        self.buttonLayout.addWidget( self.reverseCheck )
            
        self.chooseButton = QtGui.QPushButton( 'Choose colormap', self )
        self.okButton     = QtGui.QPushButton( 'Ok', self )
        self.cancelButton = QtGui.QPushButton( 'Cancel', self )
        self.chooseButton.clicked.connect( self._choose_cmap )
        self.okButton.clicked.connect( self.accept )
        self.cancelButton.clicked.connect( self.reject )
        self.yesNoLayout.addWidget( self.chooseButton )
        self.yesNoLayout.addWidget( self.okButton )
        self.yesNoLayout.addWidget( self.cancelButton )
        self.layout.addLayout( self.buttonLayout )
        self.layout.addLayout( self.yesNoLayout )
        self.setLayout( self.layout )

    def _choose_cmap( self ):
        if self.buttons[0].isChecked():
            dialog = QtGui.QErrorMessage( self )
            dialog.showMessage( "Not implemented yet." )
        else:
            isLight = self.buttons[1].isChecked()
            dialog = RGBDialog( self.choices[1] if isLight else self.choices[2], # title
                                self.reverseCheck.isChecked(), # reverse
                                isLight,
                                self )
            result = dialog.exec_()
            if not result == QtGui.QDialog.reject:
                self.cmap  = dialog.cmap
                self.title = dialog.title



class MplPlot(QtGui.QDialog):
    def __init__(self, parent=None):
        super(MplPlot, self).__init__(parent)

        self.hm = None

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

        # Save button - toolbar has save button already
        # self.saveButton = QtGui.QPushButton('Save')
        # self.saveButton.clicked.connect( self._save )

        # color map button
        self.cmapButton = QtGui.QPushButton('Color Map')
        self.cmapButton.clicked.connect(self._cmap)

        self.grid = QtGui.QGridLayout()

        # File stuff
        self.browseButton  = QtGui.QPushButton('Browse')
        self.browseButton.clicked.connect(self._get_filename)
        self.fileNameField = QtGui.QLineEdit()
        self.fileNameField.setPlaceholderText( 'Path to file containing data (csv or image)' )

        self.grid.addWidget(self.button, 0, 0, 1, 1)
        self.grid.addWidget(self.cmapButton, 0, 1, 1, 1)
        self.grid.addWidget(self.browseButton, 1, 0)
        self.grid.addWidget(self.fileNameField, 1, 1, 1, 3)

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
        if self.cmap is None:
            self.hm = sns.heatmap( data, ax=ax, linewidths=0, square=True, xticklabels = xticklabels, yticklabels = yticklabels )
        else:
            self.hm = sns.heatmap( data, ax=ax, linewidths=0, square=True, xticklabels = xticklabels, yticklabels = yticklabels, cmap=self.cmap )

        # refresh canvas
        self.canvas.draw()

    def _cmap(self):
        dialog = CmapDialog( self )
        result = dialog.exec_()
        if not result == QtGui.QDialog.reject:
            self.cmap       = dialog.cmap
            self.cmap_title = dialog.title
        # dialog = CmapDialog( )

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
