from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from pilotagem_virtual.domain.scenario import Scenario, ScenarioMarker


MARKER_COLORS = {
    "start": QColor("#717C78"),
    "braking": QColor("#C85D36"),
    "turn_in": QColor("#EEE8DC"),
    "trail_braking": QColor("#E3A23B"),
    "apex": QColor("#08A6C7"),
    "acceleration": QColor("#55B878"),
}


class TrackMapWidget(QWidget):
    def __init__(self, scenario: Scenario, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scenario = scenario
        self.progress = 0.0
        self.active_marker: ScenarioMarker = scenario.markers[0]
        self.setMinimumSize(620, 430)

    def set_progress(self, progress: float) -> None:
        self.progress = max(0.0, min(1.0, float(progress)))
        self.active_marker = self.scenario.active_marker(self.progress)
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101716"))

        points = self._screen_points()
        path = self._smooth_path(points)

        painter.setPen(QPen(QColor("#717C78"), 76, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.setPen(QPen(QColor("#242C2B"), 66, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        center_pen = QPen(QColor("#EEE8DC"), 2, Qt.PenStyle.DashLine)
        center_pen.setDashPattern([8, 9])
        painter.setPen(center_pen)
        painter.drawPath(path)

        for marker in self.scenario.markers:
            self._draw_marker(painter, points, marker)

        vehicle = self._point_at_progress(points, self.progress)
        painter.setBrush(QColor("#08A6C7"))
        painter.setPen(QPen(QColor("#EEE8DC"), 3))
        painter.drawEllipse(vehicle, 11, 11)

        painter.setPen(QColor("#EEE8DC"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(22, 18, self.width() - 44, 30),
            Qt.AlignmentFlag.AlignLeft,
            f"FASE: {self.active_marker.label}",
        )

    def _screen_points(self) -> list[QPointF]:
        margin_x = max(70.0, self.width() * 0.08)
        margin_y = max(65.0, self.height() * 0.09)
        width = max(1.0, self.width() - 2 * margin_x)
        height = max(1.0, self.height() - 2 * margin_y)
        return [
            QPointF(margin_x + x * width, margin_y + y * height)
            for x, y in self.scenario.geometry
        ]

    @staticmethod
    def _smooth_path(points: list[QPointF]) -> QPainterPath:
        path = QPainterPath(points[0])
        for index in range(1, len(points) - 1):
            midpoint = QPointF(
                (points[index].x() + points[index + 1].x()) / 2,
                (points[index].y() + points[index + 1].y()) / 2,
            )
            path.quadTo(points[index], midpoint)
        path.lineTo(points[-1])
        return path

    def _draw_marker(
        self,
        painter: QPainter,
        points: list[QPointF],
        marker: ScenarioMarker,
    ) -> None:
        position = self._point_at_progress(points, marker.progress)
        color = MARKER_COLORS.get(marker.key, QColor("#EEE8DC"))
        active = marker.key == self.active_marker.key
        radius = 9 if active else 6

        painter.setBrush(color)
        painter.setPen(QPen(QColor("#101716"), 2))
        painter.drawEllipse(position, radius, radius)
        painter.setPen(color)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold if active else QFont.Weight.Medium))
        label_rect = QRectF(position.x() + 13, position.y() - 20, 120, 24)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, marker.label)

    @staticmethod
    def _point_at_progress(points: list[QPointF], progress: float) -> QPointF:
        if progress <= 0.0:
            return points[0]
        if progress >= 1.0:
            return points[-1]

        lengths: list[float] = []
        total = 0.0
        for start, end in zip(points, points[1:], strict=False):
            length = math.hypot(end.x() - start.x(), end.y() - start.y())
            lengths.append(length)
            total += length

        target = progress * total
        traversed = 0.0
        for index, length in enumerate(lengths):
            if traversed + length >= target:
                local = (target - traversed) / max(length, 1e-9)
                start, end = points[index], points[index + 1]
                return QPointF(
                    start.x() + (end.x() - start.x()) * local,
                    start.y() + (end.y() - start.y()) * local,
                )
            traversed += length
        return points[-1]
