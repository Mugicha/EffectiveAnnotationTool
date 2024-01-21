import sys
from collections import defaultdict

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QFileDialog, QMessageBox, \
    QCheckBox, QHBoxLayout, QVBoxLayout  # , QListWidget
from PySide6.QtGui import QPainter, QMouseEvent, QImage, QPen, QColor
from PySide6.QtCore import Qt, QRect, QSize, QPointF, QPoint
from shapely import LineString
from shapely.geometry import Point

from DrawingObject import DrawingObject


# CONSTANT VALUE
MARGIN = 5


class DrawingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # タイトルの設定
        self.setWindowTitle("Drawing Application")

        # main windowを特定の位置に配置する処理（100,100）を左上にして、
        # 800x600のサイズのウィンドウを作成する.
        self.setGeometry(100, 100, 800, 600)

        # # Listを配置する.
        # main windowの左上に対して, x=650, y=10 から幅140, 高さ580で配置する.
        # self.objectListWidget = QListWidget(self)
        # self.objectListWidget.setGeometry(650, 10, 140, 580)
        # # キーボードのフォーカスを確保する.
        # self.setFocusPolicy(Qt.StrongFocus)

        # Drawing settings
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.shape = 'Line'  # default shape

        # 現在編集中であるオブジェクトを格納する中間変数
        self.editingDrawingObject = None
        self.modifyingDrawingObject = None  # 修正対象のオブジェクトを一時的に格納する変数.
        self.currentMousePosition = None  # 現在のマウスの位置を格納する変数.

        # 複数選択した際、選択されたオブジェクトを一時的に格納する配列
        self.selected_object = []
        self.range_coordinates = []  # 範囲選択の座標を格納する配列.

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

        # 線, ポリライン, 矩形の辞書型配列をさらに統合する辞書型配列.
        self.objectDict = {"Line": self.linesDict,
                           "Rectangle": self.rectAngleDict,
                           "PolyLine": self.polyLinesDict,
                           }

        # 描画用のプルダウンに関する設定
        self.shapeComboBox = QComboBox(self)
        self.shapeComboBox.addItem("Line")
        self.shapeComboBox.addItem("Rectangle")
        self.shapeComboBox.addItem("PolyLine")
        self.shapeComboBox.move(10, 10)
        self.shapeComboBox.activated[int].connect(self.shapeChanged)

        # 範囲選択を行うチェックボックス
        self.checkbox = QCheckBox("範囲選択", self)
        self.checkbox.move(150, 10)
        self.checkbox.stateChanged.connect(self.switchRangeSelectionState)
        self.allow_range_selection = False  # 範囲選択ができる状態かどうかを保存する変数.

        # Button to import image
        self.importButton = QPushButton("Import Image", self)
        self.importButton.setStyleSheet(
            "QPushButton {"
            "border: 2px solid black;"
            "background-color: gray;"
            "color: white;"
            "}"
        )
        self.importButton.move(280, 10)
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
        self.exportButton.move(410, 10)
        self.exportButton.clicked.connect(self.exportDrawing)

        # # レイアウト
        # self.main_layout = QHBoxLayout()
        #
        # # サイドバー
        # self.sidebar_layout = QVBoxLayout()
        #
        # # サイドバーにボタンを追加
        # self.sidebar_layout.addWidget(self.importButton)
        # self.sidebar_layout.addWidget(self.shapeComboBox)
        # self.sidebar_layout.addWidget(self.checkbox)
        # self.sidebar_layout.addWidget(self.exportButton)
        #
        # # メインレイアウト
        # self.main_layout.addLayout(self.sidebar_layout)
        # self.main_layout.addWidget()
        #
        # self.setLayout(self.main_layout)

    def shapeChanged(self, index):
        """
        プルダウンを使って、描画するタイプが変更された時の処理.
        :param index:
        :return:
        """
        self.shape = self.shapeComboBox.itemText(index)
        # todo: self.editingDrawingObject or self.modifyingDrawingObject がNoneでなければリセットする処理を入れたい.

    def setDrawLayer(self, _obj: DrawingObject) -> DrawingObject:
        """
        格納された座標情報をもとに、新たなレイヤーを作成し描画し、
        レイヤー情報を格納したDrawingObjectクラスの変数を返す関数.

        :param _obj: DrawingObjectクラスの変数.
        :return:
        """

        window_size = self.size()

        # 背景透明のレイヤーを用意する.
        layer = QImage(window_size, QImage.Format.Format_ARGB32)
        layer.fill(Qt.transparent)

        # レイヤーに描画する.
        pen = QPen(_obj.color, _obj.line_thickness)
        painter = QPainter(layer)
        painter.setPen(pen)
        if _obj.object_type == "Line":
            painter.drawLine(self.get_actual_coordinate(_obj.coordinates[0], window_size),
                             self.get_actual_coordinate(_obj.coordinates[1], window_size),
                             )
        elif _obj.object_type == "Rectangle":
            rect = QRect(self.get_actual_coordinate(_obj.coordinates[0], window_size),
                         self.get_actual_coordinate(_obj.coordinates[1], window_size),
                         )
            painter.drawRect(rect)
        elif _obj.object_type == "PolyLine":
            for i in range(1, len(_obj.coordinates)):
                painter.drawLine(self.get_actual_coordinate(_obj.coordinates[i-1], window_size),
                                 self.get_actual_coordinate(_obj.coordinates[i], window_size),
                                 )

        # 各オブジェクトの名前を表示.
        painter.drawText(self.get_actual_coordinate(_obj.coordinates[0], window_size),
                         _obj.object_name,
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

        # Ctrl押しながらクリックしている場合,
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            print("Ctrl + Click detected.")

            # クリックした座標を取得し
            ctrl_point = event.position().toPoint()  # type: QPoint

            # 最も近い場所にあるオブジェクトを探し
            nearest_object = self.findClosestObject(ctrl_point)  # 絶対座標系を前提とする.

            # 選択中と分かるように、一時的に色を変える.
            nearest_object.color = QColor(0, 255, 0, 127)
            nearest_object = self.setDrawLayer(nearest_object)  # 戻り値は、色が変わってレイヤーが再描画されたDrawingObject.

            # 複数選択用の配列にappendする. 参照渡しのため、各種辞書変数のvalue側も変更されることに注意.
            self.selected_object.append(nearest_object)

            # 普通の左クリックが検知されないようにreturnし、この関数の処理を終了する.
            return

        # 普通の左クリック（描画）の場合　
        if event.button() == Qt.LeftButton:

            # 複数選択中の場合, 複数選択を解除する.
            if len(self.selected_object) > 0:

                # 選択中のオブジェクトの色を全てリセットする.
                # 参照渡しなので、Dictのほうも変更されるはず
                for _obj in self.selected_object:
                    _obj.set_color()
                    self.setDrawLayer(_obj=_obj)

                self.selected_object = []
                return

            # 範囲選択が可能な状態の場合.
            if self.allow_range_selection:

                # マウスの位置を取得
                clickedMousePosition = event.position().toPoint()  # type: QPoint

                # 矩形選択中じゃない場合. = 矩形の1点目がない場合.
                if len(self.range_coordinates) == 0:

                    # まだマウストラッキングを行っていない場合,
                    if self.currentMousePosition is None:

                        # 矩形選択範囲の座標を格納する（絶対座標系）
                        self.range_coordinates.append(clickedMousePosition)

                        # トラッキングを開始
                        self.setMouseTracking(True)

                # 矩形選択中の場合. = 矩形の2点目がない場合.
                elif len(self.range_coordinates) == 1:

                    # 矩形選択範囲の座標を格納する（絶対座標系）
                    self.range_coordinates.append(clickedMousePosition)

                    # トラッキングを停止
                    self.setMouseTracking(False)

                    # 描画した矩形の中にあるオブジェクトを特定し,
                    self.selected_object = self.isInsideOfRect(self.range_coordinates)  # DrawingObject型変数のリスト.

                    # 各種リセット
                    self.currentMousePosition = None
                    self.range_coordinates = []

                return

            # 線描画時の処理.
            if self.shape == "Line":

                # 修正中の場合
                if self.modifyingDrawingObject is not None:

                    # マウスの位置を取得
                    currentMousePosition = event.position().toPoint()  # type: QPoint

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

                        # クリックしたマウス座標を相対位置に変換のうえ置き換える.
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = self.get_relative_coordinate(currentMousePosition)
                        self.currentMousePosition = None
                        self.modifyingDrawingObject.modifying_coordinate_index = None

                        # レイヤーを新しい座標で再描画し、辞書型変数に戻す.
                        self.linesDict[self.modifyingDrawingObject.id] = self.setDrawLayer(self.modifyingDrawingObject)
                        self.update()

                        # マウストラッキングを停止.
                        self.setMouseTracking(False)

                # 修正中ではない場合,
                else:

                    # 描画中の線がない場合.
                    if self.editingDrawingObject is None:

                        self.editingDrawingObject = DrawingObject(id=self.lineID, object_type="Line")
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(abs_coord=event.position().toPoint()))

                        self.lineID += 1
                        self.setMouseTracking(True)  # 点線の描画の為に、マウストラッキングを開始する

                    # 描画中の線がある場合. 直線なのでlen()==1という条件にする.
                    elif len(self.editingDrawingObject.coordinates) == 1:

                        self.setMouseTracking(False)  # 始点終点がセットされたのでマウストラッキングを終了する

                        # 座標の取得・格納
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(abs_coord=event.position().toPoint()))

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
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = self.get_relative_coordinate(currentMousePosition)
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
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(event.position().toPoint()))

                        self.rectAngleID += 1
                        self.setMouseTracking(True)

                    # 現在編集中の矩形がある場合.
                    elif len(self.editingDrawingObject.coordinates) == 1:
                        # 座標の取得・格納
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(event.position().toPoint()))
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
                        self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index] = self.get_relative_coordinate(currentMousePosition)
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
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(event.position().toPoint()))

                        # IDをインクリメントする.
                        self.polyLineID += 1

                        # 点線の描画のため、マウストラッキングを開始.
                        self.setMouseTracking(True)

                    # 現在編集中のpolylineがある場合,
                    elif len(self.editingDrawingObject.coordinates) >= 1:
                        # 編集中のpolylineのIDを持つ配列に、現在の座標を追加する.
                        # appendすることでlen()>=2になるので後続処理でout of indexにはならない.
                        self.editingDrawingObject.coordinates.append(self.get_relative_coordinate(event.position().toPoint()))
                        # レイヤーを取得.
                        self.editingDrawingObject = self.setDrawLayer(self.editingDrawingObject)

        # 普通の右クリック（オブジェクトの修正）の場合,
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
            # この処理はmarginを持たせることから、相対座標ではなく絶対座標での計算をさせたい.
            else:

                # 画面サイズを取得.
                window_size = self.size()

                # マウスポインタの座標を取得し、ShapelyのPoint型（相対座標）に変換する.
                mouseCoord = event.position().toPoint()  # type: QPoint
                # mouseCoordPoint = Point(mouseCoord.x()/window_size.width(), mouseCoord.y()/window_size.height())  # type: Point
                mouseCoordPoint = Point(mouseCoord.x(), mouseCoord.y())  # type: Point

                # クリックした近くのオブジェクトの特定.
                for d in [self.linesDict, self.rectAngleDict, self.polyLinesDict]:

                    # マウスポインタの座標が既に描画された線や矩形の近くである場合
                    for k, v in d.items():
                        # key  : object's id
                        # value: DrawingObject class instance.

                        # ShapelyのLineStringに変換(絶対座標に変換もしている)
                        each_linestring = self.point2linestring(_obj=v, window_size=window_size)

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

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.shape == "PolyLine":
            self.setMouseTracking(False)  # マウストラッキングを終了

            # 直前まで編集していたPolylineを格納する.
            self.polyLinesDict[self.editingDrawingObject.id] = self.editingDrawingObject

            # 初期化する
            self.editingDrawingObject = None
            self.currentMousePosition = None

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        DrawingObjectを描画中や修正中の場合に、マウスの位置を取得する関数.
        計算量が膨大になることから、絶対座標で保持する.

        :param event:
        :return:
        """

        # 範囲選択中の場合,
        if self.allow_range_selection:
            self.currentMousePosition = event.position().toPoint()
            self.update()

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

    def keyPressEvent(self, event) -> None:
        """
        キーボードのキーが押された時のイベントハンドラ.
        ---
        d: 選択中のオブジェクトを消す.

        :param event:
        :return:
        """
        print("keypress is triggered.")
        # "d"キー
        if event.key() == Qt.Key_D:

            # 複数選択した状態であれば,
            if len(self.selected_object) > 0:

                # 複数選択しているオブジェクトごとに,
                for each_obj in self.selected_object:

                    # objectの辞書型から消す.
                    del self.objectDict[each_obj.object_type][each_obj.id]

                # 複数選択状態をリセット.
                self.selected_object = []

                # 再描画(削除したオブジェクトを消す)
                self.update()

            return

    def paintEvent(self, event) -> None:
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
        window_size = self.size()
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

        # もし範囲選択中の場合,
        if self.allow_range_selection and len(self.range_coordinates) == 1:

            if self.currentMousePosition is not None:

                # 描画する. range_coordinates, currentMousePositionともに絶対座標.
                pen = QPen(QColor(125, 125, 125, 127))
                canvasPainter.setPen(pen)
                canvasPainter.drawRect(QRect(self.range_coordinates[0],
                                             self.currentMousePosition,
                                             ))
                canvasPainter.end()
                return

        # もし描画中の場合、
        if self.editingDrawingObject is not None:

            # マウスの動きに合わせて線を描画する処理
            if (self.shape == "Line" and self.currentMousePosition is not None and
                    self.editingDrawingObject.object_type == "Line" and
                    len(self.editingDrawingObject.coordinates) == 1):
                # 点線のスタイルを設定
                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawLine(self.get_actual_coordinate(self.editingDrawingObject.coordinates[0]),
                                       self.currentMousePosition,
                                       )
                canvasPainter.end()
                return

            # 矩形を描画中の場合、マウスの動きに合わせて矩形を描画する処理
            if (self.shape == "Rectangle" and
                self.currentMousePosition is not None and  # マウストラッキング中のマウスポジションが格納されており,
                    len(self.editingDrawingObject.coordinates) == 1):  # 矩形の右下が選択されていない場合,

                # 点線のスタイルを設定して矩形を描画する
                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawRect(QRect(self.get_actual_coordinate(self.editingDrawingObject.coordinates[0],
                                                                        window_size,
                                                                        ),
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
                canvasPainter.drawLine(self.get_actual_coordinate(self.editingDrawingObject.coordinates[-1],
                                                                  window_size,
                                                                  ),
                                       self.currentMousePosition,
                                       )
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
                canvasPainter.drawLine(self.get_actual_coordinate(self.modifyingDrawingObject.coordinates[fixed_point_index],
                                                                  window_size,
                                                                  ),
                                       self.currentMousePosition,
                                       )
                # canvasPainter.end()

            # 矩形の場合
            elif (self.modifyingDrawingObject.object_type == "Rectangle" and
                    self.modifyingDrawingObject.modifying_coordinate_index is not None and
                    self.currentMousePosition is not None):

                fixed_point_index = 0 if self.modifyingDrawingObject.modifying_coordinate_index == 1 else 1

                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)
                canvasPainter.drawRect(QRect(self.get_actual_coordinate(self.modifyingDrawingObject.coordinates[fixed_point_index],
                                                                        window_size,
                                                                        ),
                                             self.currentMousePosition),
                                       )
                canvasPainter.end()

            # ポリラインの場合
            elif (self.modifyingDrawingObject.object_type == "PolyLine" and
                  self.modifyingDrawingObject.modifying_coordinate_index is not None):

                pen = QPen(QColor(255, 0, 0, 127), 2, Qt.DotLine)
                canvasPainter.setPen(pen)

                # 線を１本だけ引く場合
                if self.modifyingDrawingObject.modifying_coordinate_index > 0:
                    canvasPainter.drawLine(self.get_actual_coordinate(self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index-1],
                                                                      window_size,
                                                                      ),
                                           self.currentMousePosition,
                                           )
                # 線を２本だけ引く場合
                if self.modifyingDrawingObject.modifying_coordinate_index < len(self.modifyingDrawingObject.coordinates)-1:
                    canvasPainter.drawLine(self.get_actual_coordinate(self.modifyingDrawingObject.coordinates[self.modifyingDrawingObject.modifying_coordinate_index+1],
                                                                      window_size,
                                                                      ),
                                           self.currentMousePosition,
                                           )
                canvasPainter.end()

    def resizeEvent(self, event) -> None:
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
        painter.drawImage(QPointF(0, 0), self.image)
        painter.end()

        # イメージを更新
        self.image = newImage

        # # ListWidgetの位置を更新する.
        # self.updateListWidgetGeometry()

        # 親クラス側のメソッドも実行する.
        super().resizeEvent(event)

    def findClosestPointAndIndex(self,
                                 _point: QPointF,
                                 _obj: DrawingObject,
                                 ) -> (QPointF, int):
        """
        マウスクリックの座標と最も近い点をDrawingObjectクラスのcoordinatesから抽出し、その点とインデックスを返す関数.
        マウスクリックの座標は絶対座標なので、相対座標に変換して計算する.

        :param _point: マウスクリックされた座標点 (QPoint オブジェクト). 絶対座標系.
        :param _obj: DrawingObjectクラスのインスタンス.
        :return: (coordinatesリストの中で最もmousePointに近い点, その点のインデックス) (QPoint オブジェクト, int).
        """
        if not _obj.coordinates:
            return None, -1  # coordinatesリストが空の場合、Noneと-1を返す.

        closestPoint = None
        closestIndex = -1
        minDistance = float('inf')

        # マウスクリックの座標を相対座標に変換する.
        window_size = self.size()
        _point = QPointF(_point.x() / window_size.width(), _point.y() / window_size.height())

        # 矩形の場合
        if _obj.object_type == "Rectangle":

            # DrawingObjectの座標なのでここは相対座標.
            p1 = _obj.coordinates[0]
            p2 = _obj.coordinates[1]

            # x座標とy座標の最小値と最大値を計算
            min_x = min(p1.x(), p2.x())
            max_x = max(p1.x(), p2.x())
            min_y = min(p1.y(), p2.y())
            max_y = max(p1.y(), p2.y())

            # 矩形の四隅の座標を計算
            bottom_left = QPointF(min_x, min_y)  # type: QPointF
            bottom_right = QPointF(max_x, min_y)
            top_left = QPointF(min_x, max_y)
            top_right = QPointF(max_x, max_y)

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

    def findClosestObject(self, _point: QPointF) -> DrawingObject:
        """
        マウスポイントから最も近い位置にあるDrawingObjectクラスのインスタンスを返す.
        絶対座標を前提とする.

        :param _point: 絶対座標系のQPoint.
        :return: _pointに最も近いDrawingObjectクラスのインスタンス.
        """

        window_size = self.size()

        # 検索対象のオブジェクトの辞書型を指定できるようにしても良い.
        for d in [self.linesDict, self.rectAngleDict, self.polyLinesDict]:

            # マウスポインタの座標が既に描画された線や矩形の近くである場合
            for k, v in d.items():
                # key  : object's id
                # value: DrawingObject class instance.

                # ShapelyのLineStringに変換
                each_linestring = self.point2linestring(_obj=v, window_size=window_size)

                # marginを追加
                each_linestring_margin = each_linestring.buffer(MARGIN)

                # 右クリックした時のマウス座標が、marginの中なら,
                if each_linestring_margin.contains(Point(_point.x(), _point.y())):
                    return v

        # 見つからなければNoneを返す
        return None

    def isInsideOfRect(self, point_list: list) -> list:
        """
        QPoint型の2点から成る矩形の中に含まれるDrawingObject型変数を探す.

        :param point_list: 矩形を定義する2点のQPoint型変数. 絶対座標系.
        :return: 描画した矩形の領域内に含まれるDrawingObjectクラスを要素とした配列.
        """
        # 範囲選択した矩形をQRect型で定義.
        rect = QRect(point_list[0], point_list[1])

        # 矩形内に含まれるDrawingObject型変数を格納するリスト
        inside_list = []

        # 現在の画面のサイズ.
        window_size = self.size()

        # 線やポリラインの場合,
        for d in [self.linesDict, self.polyLinesDict]:

            # 各オブジェクトごとの,
            for each_object in d.values():

                isinsideflag = False

                # 各相対座標点ごとに,
                for relative_p in each_object.coordinates:

                    # QRect.contains()はintしかダメなので, QPointを使う.
                    abs_p = QPoint(int(relative_p.x()*window_size.width()),
                                   int(relative_p.y()*window_size.height()),
                                   )

                    # 点が矩形に含まれれば
                    if rect.contains(abs_p):

                        # フラグを立てる.
                        isinsideflag = True

                # 1つでも含まれている点があれば,
                if isinsideflag:

                    # リストに加える.
                    inside_list.append(each_object)

        # 矩形の場合,
        for each_object in self.rectAngleDict.values():

            # QRectを作り,
            target_rect = QRect(self.get_actual_coordinate(each_object.coordinates[0], window_size),
                                self.get_actual_coordinate(each_object.coordinates[1], window_size),
                                )

            # 範囲選択した領域に矩形の各頂点が含まれるか確認し,
            check_tr = rect.contains(target_rect.topRight())
            check_tl = rect.contains(target_rect.topLeft())
            check_br = rect.contains(target_rect.bottomRight())
            check_bl = rect.contains(target_rect.bottomLeft())

            # 四隅のどれかが含まれる場合,
            if check_tr or check_tl or check_br or check_bl:

                # リストに加える.
                inside_list.append(each_object)

        # 最後に一気に色を変える.
        for each_object in inside_list:
            each_object.color = QColor(0, 255, 0, 127)
        inside_list = [self.setDrawLayer(x) for x in inside_list]

        return inside_list

    def switchRangeSelectionState(self, state):
        """
        範囲選択が可能かどうかの状態を切り替える関数.
        「範囲選択」チェックボックスのイベントハンドラ.

        :param state:  チェックされたかどうかを示すint型. チェックされたら2.
        :return:
        """
        def resetColor():
            """
            現在選択されているオブジェクトの色をリセットする内部関数.
            :return:
            """
            for each_selected_object in self.selected_object:
                # 何かしら選択状態であるオブジェクトの色を元に戻す処理を入れる.
                each_selected_object.set_color()
                _ = self.setDrawLayer(each_selected_object)

        # チェックが入った時.
        # PySide6.QtCore.Qt.CheckState型に合わせ、両者を比較する.
        if Qt.CheckState(state) == Qt.Checked:

            # 既に選択済みのオブジェクトがあれば、一度リセットする
            # Todo: UXを検証すること. もしかしたらいらないかも.
            resetColor()
            self.selected_object = []
            self.allow_range_selection = True

        # チェックが解除された時.
        else:
            self.allow_range_selection = False
            resetColor()
            # 選択したオブジェクトを解除する.
            self.selected_object = []
            self.range_coordinates = []
            self.update()

    # def updateListWidgetGeometry(self) -> None:
    #     """
    #     QListWidgetの位置とサイズを更新する.
    #     :return:
    #     """
    #     width = 150  # QListWidgetの幅
    #     height = self.height()  # ウィンドウの高さに合わせる
    #     x = self.width() - width  # ウィンドウの右端に合わせる
    #     y = 0  # ウィンドウの上端から始める
    #     self.objectListWidget.setGeometry(x, y, width, height)

    def get_relative_coordinate(self, abs_coord: QPointF):
        """
        インポートした画面サイズに対する座標の相対座標を算出する関数.

        :param abs_coord:
        :return:
        """
        relative_coord_width = abs_coord.x() / self.size().width()
        relative_coord_height = abs_coord.y() / self.size().height()
        return QPointF(relative_coord_width, relative_coord_height)

    def get_actual_coordinate(self, relative_coord: QPointF,
                              window_size: QSize = None,
                              isReturnInt: bool = True
                              ) -> QPointF:
        """
        画面サイズに対する絶対座標を算出する関数.

        :param relative_coord: 絶対座標に変換したいQPoint座標.
        :param window_size: window size.
        :param isReturnInt: QPoint型で返すかどうか.
        :return:
        """
        window_size = self.size() if window_size is None else window_size
        actual_coord_width = relative_coord.x() * window_size.width()
        actual_coord_height = relative_coord.y() * window_size.height()
        print(f"width: {actual_coord_width}")
        print(f"height: {actual_coord_height}")
        if isReturnInt:
            return QPoint(int(actual_coord_width), int(actual_coord_height))
        else:
            return QPointF(actual_coord_width, actual_coord_height)

    def point2linestring(self, _obj: DrawingObject,
                         window_size: QSize = None) -> LineString:
        """
        QPoint型のPoint情報を使って、LineString型変数を返す関数.
        :param _obj: DrawingObjectクラス変数
        :param window_size: 絶対座標に戻すために必要なwindow_size.
        :return:
        """

        # 矩形の場合
        if _obj.object_type == "Rectangle":

            p1 = _obj.coordinates[0]
            p2 = _obj.coordinates[1]

            p1 = self.get_actual_coordinate(p1, window_size)
            p2 = self.get_actual_coordinate(p2, window_size)

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
            linestring_ary = []
            for x in _obj.coordinates:
                act_coordinate = self.get_actual_coordinate(x, window_size)
                linestring_ary.append((act_coordinate.x(), act_coordinate.y()))

        elif _obj.object_type == "PolyLine":
            linestring_ary = []
            for x in _obj.coordinates:
                act_coordinate = self.get_actual_coordinate(x, window_size)
                linestring_ary.append((act_coordinate.x(), act_coordinate.y()))

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

