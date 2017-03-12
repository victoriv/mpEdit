# editor.py

import sys
import glob
import subprocess
import serial
from PyQt5 import QtCore, QtWidgets, QtGui
import syntax

class LineNumberArea(QtWidgets.QWidget):

    def __init__(self, editor):
        super().__init__(editor)
        self.myeditor = editor

    def sizeHint(self):
        return Qsize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.myeditor.lineNumberAreaPaintEvent(event)

class Main(QtWidgets.QMainWindow):

    def __init__(self, parent = None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.filename = ""
        self.port = ""

        self.initUI()

    def getPorts(self):

        if sys.platform.startswith('win'):
            ports = ['COM{}'.format(i + 1) for i in range(256)]
        elif sys.platform.startswith('linux'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError("Unsupported Platform")

        activePorts = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                activePorts.append(port)
            except(OSError, serial.SerialException):
                pass
        
        return activePorts

    def initToolbar(self):

        self.saveAction = QtWidgets.QAction(QtGui.QIcon("icons/save.png"), "Save", self)
        self.saveAction.setStatusTip("Save Program")
        self.saveAction.triggered.connect(self.save)

        self.runAction = QtWidgets.QAction(QtGui.QIcon("icons/run.png"), "Run", self)
        self.runAction.setStatusTip("Run program")
        self.runAction.triggered.connect(self.run)


        portsList = self.getPorts()
        self.portSelect = QtWidgets.QComboBox()
        self.portSelect.addItems(portsList)
        self.portSelect.currentIndexChanged.connect(self.setPort)


        self.toolbar = self.addToolBar("Options")

        self.toolbar.setMovable(False)

        self.toolbar.addAction(self.saveAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.runAction)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.portSelect)

        self.addToolBarBreak()

    def initUI(self):

        self.editor = QtWidgets.QPlainTextEdit(self)
        self.setCentralWidget(self.editor)
        self.highlight = syntax.PythonHighlighter(self.editor.document())


        self.lineNumberArea = LineNumberArea(self)
        self.editor.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.editor.updateRequest.connect(self.updateLineNumberArea)
        self.editor.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.initToolbar()

        self.updateLineNumberAreaWidth(0) 
        infile = open('blinky.py', 'r')
        self.editor.setPlainText(infile.read())


        # self.statusbar = self.statusbar()

        self.setGeometry(100, 100, 800, 600)

        self.setWindowTitle("mpEdit")

    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.editor.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.editor.fontMetrics().width('9') * digits
        return space
            
    def updateLineNumberAreaWidth(self, _):
        self.editor.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.editor.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        QtWidgets.QPlainTextEdit.resizeEvent(self.editor, event)

        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        mypainter = QtGui.QPainter(self.lineNumberArea)

        mypainter.fillRect(event.rect(), QtCore.Qt.lightGray)

        block = self.editor.firstVisibleBlock()
        # block = block.next()
        # block = block.next()
        blockNumber = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        height = self.fontMetrics().height() + self.toolbar.iconSize().height()
        print(self.toolbar.iconSize().height())
        while block.isValid() and (top <= event.rect().bottom()):
            print("top: {}, bottom: {}".format(top, bottom))
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                mypainter.setPen(QtCore.Qt.black)
                mypainter.drawText(0, top, self.lineNumberArea.width(), height, QtCore.Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.editor.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()

            lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.editor.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)

        self.editor.setExtraSelections(extraSelections)





    def save(self):
        if not self.filename:
            self.filename = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Program')[0]

        if not self.filename.endswith(".py"):
            self.filename += ".py"

        with open(self.filename, "wt") as f:
            f.write(self.editor.toPlainText())

    def run(self):
        # Save program
        self.save()

        # Call AMPY
        proc = subprocess.Popen("ampy -p {} run {}".format(self.port, self.filename), shell=True, stdout=subprocess.PIPE)
        try:
            output, errors = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, errors = proc.communicate()
            print("ERROR {}".format(errors))

        proc.kill()

        if output != "":
            print(output)

        # status = subprocess.Popen("ampy -p {} run {}".format(self.port, self.filename), shell=True, stdout=subprocess.PIPE).stdout.read()
        # print(status)

    def setPort(self):
        self.port = self.portSelect.currentText()


def main():
    app = QtWidgets.QApplication([])

    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

# editor = QtWidgets.QPlainTextEdit()
# highlight = syntax.PythonHighlighter(editor.document())
# editor.show()

# # Load syntax.py into the editor for demo purposes
# infile = open('blinky.py', 'r')
# editor.setPlainText(infile.read())

# app.exec_()
