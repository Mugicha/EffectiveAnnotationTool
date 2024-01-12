import sys
from collections import defaultdict

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QFileDialog, QMessageBox
from PySide6.QtGui import QPainter, QMouseEvent, QImage, QPen, QColor
from PySide6.QtCore import Qt, QPoint, QRect
from shapely import LineString
from shapely.geometry import Point
from typing import Union, Tuple

from DrawingObject import DrawingObject


# CONSTANT VALUE
MARGIN = 5


class DrawingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # タイトルの設定
        self.setWindowTitle("Drawing Application")

        # windowを特定の位置に配置する処理（100,100）を左上にして、
        # 800x600のサイズのウィンドウを作成する.
        self.setGeometry(100, 100, 800, 600)

        # Drawing settings
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.shape = 'Line'  # default shape

        # 現在編集中であるオブジェクトを格納する中間変数
        self.editingDrawingObject = None
        self.modifyingDrawingObject = None  # 修正対象のオブジェクトを一時的に格納する変数.
        self.currentMousePosition = None  # 現在のマウスの位置を格納する変数.

        # 直線を引くために必要な初期化処理
        self.linesDict = defaultdict(DrawingObject)
        self.lineID = 0
        self.drawingLine = False

        # Polylineを引く為に必要な変数定義と初期化処理.
        self.polyLinesDict = defaultdict(DrawingObject)  # 複数のpolylineを格納する辞書型変数.
        self.polyLineID = 0

        # Rectangleを描画する為に必要な変数定義と初期化処理.
        self.rectAngleDict = defaultdict(DrawingObject)  # 複数の矩形を格納する辞書型変数.
        self.rectAngleID = 0
        self.currentEditingRectID = None  # 現在描画中のRectangleのID（rectAngleDictのkey）を格納する変数.
        self.firstRectClickPoint = None  # 矩形左上座標を格納する変数
        self.lastRectClickPoint = None  # 矩形右下座標を格納する座標
        self.drawingRect = False

        # 描画用のプルダウンに関する設定
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
        """
        プルダウンを使って、描画するタイプが変更された時の処理.
        :param index:
        :return:
        """
        self.shape = self.shapeComboBox.itemText(index)
        # todo: self.editingDrawingObject or self.modifyingDrawingObject がNoneでなければリセットする処理を入れたい.

    def setDrawLayer(self,
                     _obj: DrawingObject,
                     ):
        """
        格納された座標情報をもとに、新たなレイヤーを作成し描画し、
        レイヤー情報を格納したDrawingObjectクラスの変数を返す関数.

        :param _obj: DrawingObjectクラスの変数.
        :return:
        """
        # 背景透明のレイヤーを用意する.
        layer = QImage(self.size(), QImage.Format.Format_ARGB32)
        layer.fill(Qt.transparent)

        # レイヤーに描画する.
        pen = QPen(_obj.color, _obj.line_thickness)
        painter = QPainter(layer)
        painter.setPen(pen)
        if _obj.object_type == "Line":
            painter.drawLine(_obj.coordinates[0], _obj.coordinates[1])
        elif _obj.object_type == "Rectangle":
            rect = QRect(_obj.coordinates[0],
                         _obj.coordinates[1],
                         )
            painter.drawRect(rect)
        elif _obj.object_type == "PolyLine":
            for i in range(1, len(_obj.coordinates)):
                painter.drawLine(_obj.coordinates[i-1],
                                 _obj.coordinates[i],
                                 )
        # 後処理
        painter.end()
        self.update()

        # レイヤーをセット
        _obj.set_layer(layer)
        return _obj

    def importImage(self):
        """
        画像をインポートする処理.
        :return:
        """
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
        """
        描画結果をエクスポートする処理.
        :return:
        """
        filePath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt)")
        if filePath:
            with open(filePath, 'w') as file:
                file.write(f"{self.rectAngleDict}¥n")  # Add more details as needed
                file.write(f"{self.polyLinesDict}¥n")

    def mousePressEvent(self, event):
        """
        マウスクリック（押下）を検知した場合に呼び出される関数.

        :param event:
        :return:
        """

        # 左クリック（描画）の場合　
        if event.button() == Qt.LeftButton:

            # 線描画時の処理.
            if self.shape == "Line":

                # 修正中の場合
                if self.modifyingDrawingObject is not None:

                    # マウスの位置を取得
                    currentMousePosition = event.position().toPoint()

                    # まだマウストラッキングを行っていない場合,
                    if self.currentMousePosition is None:

                        # 編集中のオブジェクトの座標全てと比較し、最も近い点を取得する.
                        nearest_point, nearest_point_index = self.findClosestPointAndIndex(_point=currentMousePosition,
                                                                                           _obj=self.modifyingDrawingObject,
                                                                                           )
                        # 修正点を格納する
                        self.modifyingDrawingObject.modifying_coordinate_index = nearest_point_index

                        # トラッキングを開始
                        self.setMouseTracking(True)

                    else:

                        # クリックしたマウス座標で置き換える.
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = currentMousePosition
                        self.currentMousePosition = None
                        self.modifyingDrawingObject.modifying_coordinate_index = None

                        # レイヤーを新しい座標で再描画し、辞書型変数に戻す.
                        self.linesDict[self.modifyingDrawingObject.id] = self.setDrawLayer(self.modifyingDrawingObject)
                        # self.modifyingDrawingObject = None
                        self.update()

                        # マウストラッキングを停止.
                        self.setMouseTracking(False)

                # 修正中ではない場合,
                else:

                    # 描画中の線がない場合.
                    if self.editingDrawingObject is None:

                        self.editingDrawingObject = DrawingObject(id=self.lineID, object_type="Line")
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())

                        self.lineID += 1
                        self.setMouseTracking(True)  # 点線の描画の為に、マウストラッキングを開始する

                    # 描画中の線がある場合. 直線なのでlen()==1という条件にする.
                    elif len(self.editingDrawingObject.coordinates) == 1:

                        self.setMouseTracking(False)  # 始点終点がセットされたのでマウストラッキングを終了する

                        # 座標の取得・格納
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())

                        # self.image に直線を描画
                        self.drawingLine = True

                        # 中間変数から、lineDictへ格上げ
                        self.linesDict[self.editingDrawingObject.id] = self.setDrawLayer(self.editingDrawingObject)
                        self.editingDrawingObject = None  # reset object.

                        # クリックポイントをリセット
                        self.currentMousePosition = None
                        self.drawingLine = False

            # 矩形の編集時の処理.
            elif self.shape == "Rectangle":

                # 修正中の場合,
                if self.modifyingDrawingObject is not None:

                    # マウスの位置を取得
                    currentMousePosition = event.position().toPoint()

                    # まだマウストラッキングを行っていない場合,
                    if self.currentMousePosition is None:

                        # 編集中のオブジェクトの座標全てと比較し、最も近い点を取得する.
                        nearest_point, nearest_point_index = self.findClosestPointAndIndex(_point=currentMousePosition,
                                                                                           _obj=self.modifyingDrawingObject,
                                                                                           )
                        # 修正点を格納する
                        self.modifyingDrawingObject.modifying_coordinate_index = nearest_point_index

                        # トラッキングを開始
                        self.setMouseTracking(True)

                    # マウストラッキングを行っている場合.
                    else:

                        # クリックしたマウス座標で置き換える.
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = currentMousePosition
                        self.currentMousePosition = None
                        self.modifyingDrawingObject.modifying_coordinate_index = None

                        # レイヤーを新しい座標で再描画し、辞書型変数に戻す.
                        self.linesDict[self.modifyingDrawingObject.id] = self.setDrawLayer(self.modifyingDrawingObject)
                        self.update()

                        # マウストラッキングを停止.
                        self.setMouseTracking(False)

                # 修正中ではない場合,
                else:

                    # 現在編集中の矩形が無い場合.
                    if self.editingDrawingObject is None:

                        # 新規作成
                        self.editingDrawingObject = DrawingObject(id=self.rectAngleID, object_type="Rectangle")
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())

                        self.rectAngleID += 1
                        self.setMouseTracking(True)

                    # 現在編集中の矩形がある場合.
                    elif len(self.editingDrawingObject.coordinates) == 1:
                        # 座標の取得・格納
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())
                        self.setMouseTracking(False)

                        # 中間変数から、rectAngleDictへ格上げ
                        self.rectAngleDict[self.editingDrawingObject.id] = self.setDrawLayer(self.editingDrawingObject)
                        self.editingDrawingObject = None  # reset object

                        # クリックポイントをリセット
                        self.currentMousePosition = None
                        self.drawingRect = False

            # ポリラインの編集時の処理
            elif self.shape == "PolyLine":

                # ポリラインを修正中の場合,
                if self.modifyingDrawingObject is not None:

                    # マウスの位置を取得
                    currentMousePosition = event.position().toPoint()

                    # まだマウストラッキングを行っていない場合,
                    if self.currentMousePosition is None:

                        # 編集中のオブジェクトの座標全てと比較し、最も近い点を取得する.
                        nearest_point, nearest_point_index = self.findClosestPointAndIndex(_point=currentMousePosition,
                                                                                           _obj=self.modifyingDrawingObject,
                                                                                           )
                        # 修正点を格納する
                        self.modifyingDrawingObject.modifying_coordinate_index = nearest_point_index

                        # トラッキングを開始
                        self.setMouseTracking(True)

                    # マウストラッキングを行っている場合.
                    else:

                        # クリックしたマウス座標で置き換える.
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = currentMousePosition
                        self.currentMousePosition = None
                        self.modifyingDrawingObject.modifying_coordinate_index = None

                        # レイヤーを新しい座標で再描画し、辞書型変数に戻す.
                        self.linesDict[self.modifyingDrawingObject.id] = self.setDrawLayer(self.modifyingDrawingObject)
                        self.update()

                        # マウストラッキングを停止.
                        self.setMouseTracking(False)

                # ポリラインを修正中ではない場合,
                else:

                    # 現在編集中のpolylineがない場合,
                    if self.editingDrawingObject is None:

                        # 新しいオブジェクトを作成
                        self.editingDrawingObject = DrawingObject(id=self.polyLineID, object_type="PolyLine")
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())

                        # IDをインクリメントする.
                        self.polyLineID += 1

                        # 点線の描画のため、マウストラッキングを開始.
                        self.setMouseTracking(True)

                    # 現在編集中のpolylineがある場合,
                    elif len(self.editingDrawingObject.coordinates) >= 1:
                        # 編集中のpolylineのIDを持つ配列に、現在の座標を追加する.
                        # appendすることでlen()>=2になるので後続処理でout of indexにはならない.
                        self.editingDrawingObject.coordinates.append(event.position().toPoint())
                        # レイヤーを取得.
                        self.editingDrawingObject = self.setDrawLayer(self.editingDrawingObject)

        # 右クリック（オブジェクトの修正）の場合,
        elif event.button() == Qt.RightButton:

            # 修正中のオブジェクトが存在する中で右クリックした場合,
            if self.modifyingDrawingObject is not None:

                # 修正を終了し、
                self.modifyingDrawingObject.stop_modifying()
                self.setDrawLayer(_obj=self.modifyingDrawingObject)

                # 修正した結果を辞書型変数に戻す.
                if self.modifyingDrawingObject.object_type == "Line":
                    self.linesDict[self.modifyingDrawingObject.id] = self.modifyingDrawingObject
                elif self.modifyingDrawingObject.object_type == "PolyLine":
                    self.polyLinesDict[self.modifyingDrawingObject.id] = self.modifyingDrawingObject
                elif self.modifyingDrawingObject.object_type == "Rectangle":
                    self.rectAngleDict[self.modifyingDrawingObject.id] = self.modifyingDrawingObject

                # 修正対象のオブジェクトを格納する変数を初期化する.
                self.modifyingDrawingObject = None
                self.update()
                return

            # 修正中のオブジェクトが存在しない中で右クリックした場合,
            else:

                # マウスポインタの座標を取得
                mouseCoord = event.position().toPoint()  # type: QPoint
                mouseCoordPoint = Point(mouseCoord.x(), mouseCoord.y())  # type: Point

                # クリックした近くのオブジェクトの特定.
                for d in [self.linesDict, self.rectAngleDict, self.polyLinesDict]:

                    # マウスポインタの座標が既に描画された線や矩形の近くである場合
                    for k, v in d.items():
                        # key  : object's id
                        # value: DrawingObject class instance.

                        # ShapelyのLineStringに変換
                        each_linestring = self.point2linestring(_obj=v)

                        # marginを追加
                        each_linestring_margin = each_linestring.buffer(MARGIN)

                        # 右クリックした時のマウス座標が、marginの中で,
                        if each_linestring_margin.contains(Point(mouseCoordPoint.x, mouseCoordPoint.y)):

                            # 修正フラグが立っていなければ,
                            if not d[k].is_being_modified:

                                # 修正フラグを立て,
                                d[k].start_modifying()

                                # 修正対象のオブジェクトを格納する変数に入れる.
                                self.modifyingDrawingObject = d[k]

                                # 変えた色で再描画する
                                self.setDrawLayer(_obj=self.modifyingDrawingObject)

                                # test
                                print(f"Start Modifying: {d}, {k}")

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.shape == "PolyLine":
            self.setMouseTracking(False)  # マウストラッキングを終了

            # 直前まで編集していたPolylineを格納する.
            self.polyLinesDict[self.editingDrawingObject.id] = self.editingDrawingObject

            # 初期化する
            self.editingDrawingObject = None
            self.currentMousePosition = None

    def mouseMoveEvent(self, event: QMouseEvent):

        # 描画中の場合
        if self.editingDrawingObject is not None:

            # 線を描画するモード.
            if self.shape == "Line" and len(self.editingDrawingObject.coordinates) == 1:
                self.currentMousePosition = event.position().toPoint()
                self.update()

            # 矩形を描画するモード.
            elif self.shape == "Rectangle":
                self.currentMousePosition = event.position().toPoint()
                self.update()

            # PolyLineを描画するモード.
            elif self.shape == "PolyLine":
                self.currentMousePosition = event.position().toPoint()
                self.update()

        # 修正中の場合,
        if self.modifyingDrawingObject is not None:

            # 線なら
            if self.modifyingDrawingObject.object_type == "Line":
                self.currentMousePosition = event.position().toPoint()
                self.update()  # 描画

            # 矩形なら
            elif self.modifyingDrawingObject.object_type == "Rectangle":
                self.currentMousePosition = event.position().toPoint()
                self.update()  # 描画

            elif self.modifyingDrawingObject.object_type == "PolyLine":
                self.currentMousePosition = event.position().toPoint()
                self.update()  # 描画


    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:

            # 線を描画中の場合.
            if self.drawingLine:
                # ライン描画後にポイントをリセット
                self.drawingLine = False

            # 矩形を描画中の場合.
            elif self.drawingRect:
                # 矩形描画後にポイントをリセット
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

        # 各レイヤーを重ねる処理
        for d in [self.linesDict, self.rectAngleDict, self.polyLinesDict]:
            for _obj in d.values():
                canvasPainter.drawImage(self.rect(),
                                        _obj.layerImage,
                                        _obj.layerImage.rect(),
                                        )
        if self.editingDrawingObject is not None:
            if self.editingDrawingObject.layerImage is not None:
                canvasPainter.drawImage(self.rect(),
                                        self.editingDrawingObject.layerImage,
                                        self.editingDrawingObject.layerImage.rect(),
                                        )

        # 編集・修正中でない場合は、ここでreturnする.
        # if self.editingDrawingObject is None or self.modifyingDrawingObject is None:
        #     return

        # もし線を描画中の場合、
        if self.editingDrawingObject is not None:

            # マウスの動きに合わせて線を描画する処理
            if (self.shape == "Line" and self.currentMousePosition is not None and
                    self.editingDrawingObject.object_type == "Line" and
                    len(self.editingDrawingObject.coordinates) == 1):
                # 点線のスタイルを設定
                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawLine(self.editingDrawingObject.coordinates[0], self.currentMousePosition)
                canvasPainter.end()
                return

            # 矩形を描画中の場合、マウスの動きに合わせて矩形を描画する処理
            if (self.shape == "Rectangle" and
                self.currentMousePosition is not None and  # マウストラッキング中のマウスポジションが格納されており,
                    len(self.editingDrawingObject.coordinates) == 1):  # 矩形の右下が選択されていない場合,

                # 点線のスタイルを設定して矩形を描画する
                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawRect(QRect(self.editingDrawingObject.coordinates[0],
                                             self.currentMousePosition,
                                             ))
                canvasPainter.end()
                return

            if (self.shape == "PolyLine" and
                    self.editingDrawingObject.object_type == "PolyLine" and
                    self.editingDrawingObject is not None and
                    self.currentMousePosition is not None):
                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawLine(self.editingDrawingObject.coordinates[-1], self.currentMousePosition)
                canvasPainter.end()
                return

        # もし、オブジェクトを修正中の場合,
        elif self.modifyingDrawingObject is not None:

            # 線の場合,
            # (備忘：２つめの条件は、オブジェクトを右クリックした直後のself.updateでこの条件分岐に入らないようにするための対策)
            if (self.modifyingDrawingObject.object_type == "Line" and
                    self.modifyingDrawingObject.modifying_coordinate_index is not None):

                # 固定点を設定
                fixed_point_index = 0 if self.modifyingDrawingObject.modifying_coordinate_index == 1 else 1

                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawLine(self.modifyingDrawingObject.coordinates[fixed_point_index],
                                       self.currentMousePosition,
                                       )
                # canvasPainter.end()

            # 矩形の場合
            elif (self.modifyingDrawingObject.object_type == "Rectangle" and
                    self.modifyingDrawingObject.modifying_coordinate_index is not None):

                fixed_point_index = 0 if self.modifyingDrawingObject.modifying_coordinate_index == 1 else 1

                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawRect(QRect(self.modifyingDrawingObject.coordinates[fixed_point_index],
                                             self.currentMousePosition,
                                             )
                                       )
                canvasPainter.end()

            # ポリラインの場合
            elif (self.modifyingDrawingObject.object_type == "PolyLine" and
                  self.modifyingDrawingObject.modifying_coordinate_index is not None):

                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)

                # 線を１本だけ引く場合
                if self.modifyingDrawingObject.modifying_coordinate_index > 0:
                    canvasPainter.drawLine(self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index-1],
                                           self.currentMousePosition,
                                           )
                # 線を２本だけ引く場合
                if self.modifyingDrawingObject.modifying_coordinate_index < len(self.modifyingDrawingObject.coordinates)-1:
                    canvasPainter.drawLine(self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index+1],
                                           self.currentMousePosition,
                                           )
                canvasPainter.end()

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

    def findClosestPointAndIndex(self,
                                 _point: QPoint,
                                 _obj: DrawingObject,
                                 ) -> (QPoint, int):
        """
        マウスクリックの座標と最も近い点をDrawingObjectクラスのcoordinatesから抽出し、
        その点とインデックスを返す関数.

        :param _point: マウスクリックされた座標点 (QPoint オブジェクト).
        :param _obj: DrawingObjectクラスのインスタンス.
        :return: (coordinatesリストの中で最もmousePointに近い点, その点のインデックス) (QPoint オブジェクト, int).
        """
        if not _obj.coordinates:
            return None, -1  # coordinatesリストが空の場合、Noneと-1を返す.

        closestPoint = None
        closestIndex = -1
        minDistance = float('inf')

        # 矩形の場合
        if _obj.object_type == "Rectangle":

            p1 = _obj.coordinates[0]
            p2 = _obj.coordinates[1]

            # x座標とy座標の最小値と最大値を計算
            min_x = min(p1.x(), p2.x())
            max_x = max(p1.x(), p2.x())
            min_y = min(p1.y(), p2.y())
            max_y = max(p1.y(), p2.y())

            # 矩形の四隅の座標を計算
            bottom_left = QPoint(min_x, min_y)  # type: QPoint
            bottom_right = QPoint(max_x, min_y)
            top_left = QPoint(min_x, max_y)
            top_right = QPoint(max_x, max_y)

            _coordinates = [bottom_left, bottom_right, top_right, top_left]

        else:
            _coordinates = _obj.coordinates

        for index, point in enumerate(_coordinates):
            distance = (_point.x() - point.x()) ** 2 + (_point.y() - point.y()) ** 2
            if distance < minDistance:
                minDistance = distance
                closestPoint = point
                closestIndex = index

        if _obj.object_type == "Rectangle":

            if closestIndex == 0:  # bottom_left
                modified_coordinate = [bottom_left, top_right]
            elif closestIndex == 1:  # bottom_right
                modified_coordinate = [bottom_right, top_left]
            elif closestIndex == 2:  # top_right
                modified_coordinate = [top_right, bottom_left]
            elif closestIndex == 3:  # top_left
                modified_coordinate = [top_left, bottom_right]
            else:
                modified_coordinate = None

            self.modifyingDrawingObject.coordinates = modified_coordinate
            return modified_coordinate[0], 0

        return closestPoint, closestIndex

    @staticmethod
    def point2linestring(_obj: DrawingObject):
        """
        QPoint型のPoint情報を使って、LineString型変数を返す関数.
        :param _obj: DrawingObjectクラス変数
        :return:
        """

        # 矩形の場合
        if _obj.object_type == "Rectangle":

            p1 = _obj.coordinates[0]
            p2 = _obj.coordinates[1]

            # x座標とy座標の最小値と最大値を計算
            min_x = min(p1.x(), p2.x())
            max_x = max(p1.x(), p2.x())
            min_y = min(p1.y(), p2.y())
            max_y = max(p1.y(), p2.y())

            # 矩形の四隅の座標を計算
            bottom_left = (min_x, min_y)
            bottom_right = (max_x, min_y)
            top_left = (min_x, max_y)
            top_right = (max_x, max_y)

            # LineString用の座標が格納された配列.
            linestring_ary = [bottom_left, bottom_right, top_right, top_left, bottom_left]

        elif _obj.object_type == "Line":
            linestring_ary = [(x.x(), x.y()) for x in _obj.coordinates]

        elif _obj.object_type == "PolyLine":
            linestring_ary = [(x.x(), x.y()) for x in _obj.coordinates]

        else:
            assert f"invalid object_type: {_obj.object_type}"
            return

        # Polygon オブジェクトを作成して矩形を定義
        return LineString(linestring_ary)  # type: LineString


def main():
    app = QApplication(sys.argv)
    mainWin = DrawingApp()
    mainWin.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

