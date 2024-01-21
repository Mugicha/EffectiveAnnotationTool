from PySide6.QtCore import QSize, QPointF
from PySide6.QtGui import QColor
from PySide6.QtGui import QImage


class DrawingObject:

    # 描画可能なオブジェクトの定義をクラス変数に格納する.
    TYPES = ('Line', 'Rectangle', 'PolyLine')

    def __init__(self,
                 id: int,
                 object_type: str,
                 coordinates: list = None,
                 color: tuple = None,
                 line_thickness: int = 2,
                 ):

        if object_type not in self.TYPES:
            raise ValueError(f"Invalid object type. Allowed types are: {self.TYPES}")

        self.id = id
        self.object_name = f"{object_type}_{id}"
        self.object_type = object_type
        self.coordinates = [] if coordinates is None else coordinates  # List of coordinates.
        self.is_being_modified = False  # 修正中かどうか
        self.is_currently_drawing = False  # 編集中かどうか
        self.line_thickness = line_thickness  # 線の太さ（ピクセル値）
        self.color = None  # オブジェクトの色情報（QColor）
        self.custom_color = None  # オブジェクトの色情報（QColor）

        # 図形が描画されたQtImageを格納する変数.
        self.layerImage = None

        # 修正時、どの座標がマウスで調整可能かを示すindex情報
        self.modifying_coordinate_index = None

        # 色の設定
        # QColorオブジェクトが指定されている場合
        if color is not None and isinstance(color, QColor):

            # カスタムカラーとして保存しておく.
            self.custom_color = color

        # 色を設定する.
        self.set_color()

    def start_modifying(self):
        self.is_being_modified = True
        self.color = QColor(255, 0, 0, 127)

    def stop_modifying(self):
        self.is_being_modified = False
        self.set_color()

    def start_drawing(self):
        self.is_currently_drawing = True

    def stop_drawing(self):
        self.is_currently_drawing = False

    def set_color(self, _color=None):

        # 一時的に色を変えたい時.
        if _color is not None and isinstance(_color, QColor):
            self.color = _color

        if self.custom_color is not None:
            self.color = self.custom_color
        else:
            # オブジェクトのタイプによって色を変える
            if self.object_type == "Line":
                self.color = QColor(227, 23, 138, 127)
            elif self.object_type == "Rectangle":
                self.color = QColor(227, 149, 23, 127)
            elif self.object_type == "PolyLine":
                self.color = QColor(181, 107, 201, 127)
            else:
                self.color = QColor(0, 0, 0, 127)

    def set_layer(self, layer: QImage):
        self.layerImage = layer

    def set_relative_coordinates(self, window_size: QSize, coordinate: QPointF):
        """
        画像のサイズと、マウスクリックされた座標から、
        オブジェクトの相対位置を算出する関数.
        :param window_size: 座標が記録された時点のウィンドウサイズ. QSize型.
        :param coordinate: 記録したい座標. QPoint型.
        :return: 相対位置が格納されたQpoint.
        """
        relative_coordinates_width = coordinate.x() / window_size.width()
        relative_coordinates_height = coordinate.y() / window_size.height()
        return QPointF(relative_coordinates_width, relative_coordinates_height)

    def __repr__(self):
        return f"DrawingObject(type={self.object_type}, coordinates={self.coordinates}, color={self.color}, thickness={self.line_thickness})"
