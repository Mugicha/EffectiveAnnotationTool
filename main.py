import sys
from collections import defaultdict

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox
from PySide6.QtGui import QPainter, QMouseEvent, QImage, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QPoint, QRect


class DrawingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # タイトルの設定
        self.setWindowTitle("Drawing Application")

        # windowを特定の位置に配置する処理（100,100）を左上にして、
        # 800x600のサイズのウィンドウを作成する.
        self.setGeometry(100, 100, 800, 600)

        # Drawing settings
        self.drawing = False
        self.lastPoint = QPoint()
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.shape = 'Line'  # default shape

        # 直線を引くために必要な初期化処理
        self.firstLineClickPoint = None
        self.lastLineClickPoint = None
        self.currentMousePosition = None  # 現在のマウスの位置を格納する変数.
        self.drawingLine = False

        # Polylineを引く為に必要な変数定義と初期化処理.
        self.polyLinesDict = defaultdict(list)  # 複数のpolylineを格納する辞書型変数.
        self.polyLineID = 0
        self.currentEditingPolyID = None  # 現在描画中のPolylineのID（polyLineDictのkey）を格納する変数.

        # Rectangleを描画する為に必要な変数定義と初期化処理.
        self.rectAngleDict = defaultdict(list)  # 複数の矩形を格納する辞書型変数.
        self.rectAngleID = 0
        self.currentEditingRectID = None  # 現在描画中のRectangleのID（rectAngleDictのkey）を格納する変数.
        self.firstRectClickPoint = None  # 矩形を描画するための、左上座標を格納する変数
        self.lastRectClickPoint = None  # 矩形を描画するための、右下座標を格納する座標
        self.drawingRect = False

        # Dropdown for shape selection
        self.shapeComboBox = QComboBox(self)
        self.shapeComboBox.addItem("Line")
        self.shapeComboBox.addItem("Rectangle")
        self.shapeComboBox.addItem("PolyLine")
        self.shapeComboBox.move(10, 10)
        self.shapeComboBox.activated[int].connect(self.shapeChanged)

        # Button to import image
        self.importButton = QPushButton("Import Image", self)
        self.importButton.setStyleSheet(
            "QPushButton {"
            "border: 2px solid black;"
            "background-color: gray;"
            "color: white;"
            "}"
        )
        self.importButton.move(150, 10)
        self.importButton.clicked.connect(self.importImage)

        # Button to export drawing
        self.exportButton = QPushButton("Export Drawing", self)
        self.exportButton.setStyleSheet(
            "QPushButton {"
            "border: 2px solid black;"
            "background-color: gray;"
            "color: white;"
            "}"
        )
        self.exportButton.move(280, 10)
        self.exportButton.clicked.connect(self.exportDrawing)

    def shapeChanged(self, index):
        self.shape = self.shapeComboBox.itemText(index)

    def importImage(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Images (*.png *.xpm *.jpg)")
        if fileName:
            self.image = QImage(fileName)
            if self.image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
                return

            # キャンバスとウィンドウのサイズを画像のサイズに合わせる
            self.resize(self.image.size())
            self.update()

    def exportDrawing(self):
        filePath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt)")
        if filePath:
            with open(filePath, 'w') as file:
                file.write("Shape: " + self.shape + "\n")  # Add more details as needed
                file.write("Last Point: " + str(self.lastPoint.x()) + ", " + str(self.lastPoint.y()) + "\n")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:

            # 線描画時の処理.
            if self.shape == "Line":

                # 描画中の線がない場合.
                if self.firstLineClickPoint is None:
                    self.firstLineClickPoint = event.position().toPoint()
                    self.setMouseTracking(True)  # 点線の描画の為に、マウストラッキングを開始する

                # 描画中の線がある場合.
                elif self.lastLineClickPoint is None:
                    self.lastLineClickPoint = event.position().toPoint()
                    self.setMouseTracking(False)  # 始点終点がセットされたのでマウストラッキングを終了する
                    self.drawingLine = True
                    # self.image に直線を描画
                    pen = QPen(QColor(227, 23, 138, 127), 4)
                    painter = QPainter(self.image)
                    painter.setPen(pen)
                    painter.drawLine(self.firstLineClickPoint, self.lastLineClickPoint)
                    painter.end()
                    self.update()
                    # クリックポイントをリセット
                    self.firstLineClickPoint = None
                    self.lastLineClickPoint = None
                    self.currentMousePosition = None
                    self.drawingLine = False

            # 矩形の編集時の処理.
            elif self.shape == "Rectangle":

                # 現在編集中の矩形が無い場合.
                if self.firstRectClickPoint is None:
                    self.firstRectClickPoint = event.position().toPoint()
                    self.rectAngleDict[self.rectAngleID].append(self.firstRectClickPoint)
                    self.currentEditingRectID = self.rectAngleID
                    self.rectAngleID += 1
                    self.setMouseTracking(True)

                # 現在編集中の矩形がある場合.
                elif self.lastRectClickPoint is None:
                    self.lastRectClickPoint = event.position().toPoint()
                    self.rectAngleDict[self.currentEditingRectID].append(self.lastRectClickPoint)
                    self.setMouseTracking(False)
                    # self.imageに矩形を描画
                    pen = QPen(QColor(227, 149, 23), 4)
                    painter = QPainter(self.image)
                    painter.setPen(pen)
                    rect = QRect(self.firstRectClickPoint, self.lastRectClickPoint)
                    painter.drawRect(rect)
                    painter.end()
                    self.update()
                    # クリックポイントをリセット
                    self.firstRectClickPoint = None
                    self.lastRectClickPoint = None
                    self.drawingRect = False

            # ポリラインの編集時の処理
            elif self.shape == "PolyLine":

                # 現在編集中のpolylineがない場合,
                if self.currentEditingPolyID is None:
                    # 新しいIDを持つpolylineを作成し、現在の座標を格納する.
                    self.polyLinesDict[self.polyLineID].append(event.position().toPoint())
                    self.currentEditingPolyID = self.polyLineID
                    self.polyLineID += 1
                    self.setMouseTracking(True)  # 点線の描画のため、マウストラッキングを開始.

                # 現在編集中のpolylineがある場合,
                elif len(self.polyLinesDict[self.currentEditingPolyID]) >= 1:
                    # 編集中のpolylineのIDを持つ配列に、現在の座標を追加する.
                    # appendすることでlen()>=2になるので後続処理でout of indexにはならない.
                    self.polyLinesDict[self.currentEditingPolyID].append(event.position().toPoint())
                    # self.imageにPolyLineを描画
                    pen = QPen(QColor(181, 107, 201, 127), 4)
                    polypainter = QPainter(self.image)
                    polypainter.setPen(pen)
                    polypainter.drawLine(self.polyLinesDict[self.currentEditingPolyID][-2], self.polyLinesDict[self.currentEditingPolyID][-1])
                    polypainter.end()
                    self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.shape == "PolyLine":
            self.setMouseTracking(False)  # マウストラッキングを終了
            self.currentEditingPolyID = None

    def mouseMoveEvent(self, event: QMouseEvent):
        # 線を描画するモード.
        if self.shape == "Line" and self.firstLineClickPoint is not None and self.lastLineClickPoint is None:
            self.currentMousePosition = event.position().toPoint()
            self.update()
        # 矩形を描画するモード.
        elif self.shape == "Rectangle":
            self.currentMousePosition = event.position().toPoint()
            self.update()
        # PolyLineを描画するモード.
        elif self.shape == "PolyLine" and self.currentEditingPolyID is not None:
            self.currentMousePosition = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drawing = False

            # 線を描画中の場合.
            if self.drawingLine:
                # ライン描画後にポイントをリセット
                self.firstLineClickPoint = None
                self.lastLineClickPoint = None
                self.drawingLine = False

            # 矩形を描画中の場合.
            elif self.drawingRect:
                # 矩形描画後にポイントをリセット
                self.firstRectClickPoint = None
                self.lastRectClickPoint = None
                self.drawingRect = False

    def paintEvent(self, event):
        """
        以下のタイミングでcallされる処理.
        -------
        ウィンドウが初めて表示される時
        ウィンドウサイズが変更された時
        ウィンドウが他のウィンドウによって隠されて、再度表示された時
        明示的な処理要求があった時（update(), repaint()など）
        :param event:
        :return:
        """
        canvasPainter = QPainter(self)

        # 以下で実施していること
        # drawImage の呼び出しは self.image の全体を DrawingApp ウィンドウの全体に描画することを意味する。
        # 引数：self.rect() -> 描画先の領域を示す
        # 引数：self.image -> 描画する画像自体
        # 引数：self.image.rect() -> 描画する画像の中で、どの部分を描画するかを指定する
        canvasPainter.drawImage(self.rect(), self.image, self.image.rect())

        # もし線を描画中の場合、マウスの動きに合わせて線を描画する処理
        if (self.currentMousePosition is not None and
                self.firstLineClickPoint is not None and
                self.lastLineClickPoint is None):
            # 点線のスタイルを設定
            pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
            canvasPainter.setPen(pen)
            canvasPainter.drawLine(self.firstLineClickPoint, self.currentMousePosition)
            return

        # 矩形を描画中の場合、マウスの動きに合わせて矩形を描画する処理
        if (self.shape == "Rectangle" and
                self.currentMousePosition is not None and  # マウストラッキング中のマウスポジションが格納されており,
                self.firstRectClickPoint is not None and  # 矩形の左上が選択済であり,
                self.lastRectClickPoint is None):  # 矩形の右下が選択されていない場合,
            # 点線のスタイルを設定して矩形を描画する
            pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
            canvasPainter.setPen(pen)
            canvasPainter.drawRect(QRect(self.firstRectClickPoint, self.currentMousePosition))
            return

        if self.shape == "PolyLine" and self.currentEditingPolyID is not None and self.currentMousePosition is not None:
            pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
            canvasPainter.setPen(pen)
            canvasPainter.drawLine(self.polyLinesDict[self.currentEditingPolyID][-1], self.currentMousePosition)
            return

    def resizeEvent(self, event):
        """
        画面がリサイズされた時に呼ばれるイベント.
        :param event:
        :return:
        """
        # 新しいサイズを取得
        newSize = self.size()

        # 新しいサイズで新しいイメージを作成し、元のイメージの内容をコピーする.
        newImage = QImage(newSize, QImage.Format_RGB32)
        newImage.fill(Qt.white)
        painter = QPainter(newImage)
        painter.drawImage(QPoint(0, 0), self.image)
        painter.end()

        # イメージを更新
        self.image = newImage

        super().resizeEvent(event)


# Additional methods to handle editing of shapes and other functionalities
# can be added here. For example, handling clicks on existing shapes to
# modify their properties, etc.


def main():
    app = QApplication(sys.argv)
    mainWin = DrawingApp()
    mainWin.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

