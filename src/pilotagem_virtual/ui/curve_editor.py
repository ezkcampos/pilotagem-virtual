from __future__ import annotations

import uuid

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from pilotagem_virtual.domain.exercise import Exercise


DEFAULT_VALUES = (0, 100, 100, 90, 75, 60, 45, 30, 18, 8, 0)


class CurveEditorWidget(QWidget):
    changed = Signal(object)

    def __init__(self, values=DEFAULT_VALUES):
        super().__init__()
        self.values=[max(0,min(100,int(round(value)))) for value in values]
        if len(self.values) != 11:
            raise ValueError('O editor exige onze pontos')
        self.selected=0
        self.setMinimumSize(720,390)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Editor da curva personalizada com onze pontos')

    def plot_rect(self):
        return QRectF(55,35,max(1,self.width()-80),max(1,self.height()-85))

    def position(self,index):
        rect=self.plot_rect()
        return QPointF(rect.left()+rect.width()*index/10,rect.bottom()-rect.height()*self.values[index]/100)

    def set_value(self,index,value):
        self.selected=max(0,min(10,index))
        value=max(0,min(100,int(round(value))))
        if self.values[self.selected] != value:
            self.values[self.selected]=value
            self.changed.emit(tuple(self.values))
        self.update()

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor('#101716')); rect=self.plot_rect()
        for n in range(6):
            y=rect.bottom()-rect.height()*n/5
            p.setPen(QColor('#34403e')); p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            p.setPen(QColor('#aab3b0')); p.drawText(15,int(y)+4,str(n*20))
        for index in range(11):
            x=rect.left()+rect.width()*index/10
            p.setPen(QColor('#2a3331')); p.drawLine(QPointF(x,rect.top()),QPointF(x,rect.bottom()))
            p.setPen(QColor('#aab3b0')); p.drawText(int(x)-10,int(rect.bottom())+22,f'{index*10}%')
        path=QPainterPath(self.position(0))
        for index in range(1,11): path.lineTo(self.position(index))
        p.setPen(QPen(QColor('#e3b55c'),3)); p.drawPath(path)
        for index,value in enumerate(self.values):
            point=self.position(index)
            p.setBrush(QColor('#27c4df') if index==self.selected else QColor('#eee8dc'))
            p.setPen(QPen(QColor('#101716'),2)); p.drawEllipse(point,8 if index==self.selected else 6,8 if index==self.selected else 6)
            if index==self.selected:
                p.setPen(QColor('#eee8dc')); p.drawText(QPointF(point.x()+10,max(18,point.y()-10)),f'{index*10}% do tempo · {value}% de freio')
        p.setPen(QColor('#aab3b0')); p.drawText(55,self.height()-8,'Arraste os pontos verticalmente · ←/→ seleciona · ↑/↓ ajusta 1% · Shift ajusta 5%')
        p.end()

    def mousePressEvent(self,event: QMouseEvent):
        self.setFocus()
        nearest=min(range(11),key=lambda i:abs(self.position(i).x()-event.position().x()))
        self.selected=nearest; self._apply_mouse(event.position().y())

    def mouseMoveEvent(self,event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton: self._apply_mouse(event.position().y())

    def _apply_mouse(self,y):
        rect=self.plot_rect(); self.set_value(self.selected,(rect.bottom()-y)/rect.height()*100)

    def keyPressEvent(self,event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right):
            self.selected=max(0,min(10,self.selected+(-1 if event.key()==Qt.Key.Key_Left else 1))); self.update(); return
        if event.key() in (Qt.Key.Key_Up,Qt.Key.Key_Down):
            step=5 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            self.set_value(self.selected,self.values[self.selected]+(step if event.key()==Qt.Key.Key_Up else -step)); return
        super().keyPressEvent(event)


class CurveEditorDialog(QDialog):
    def __init__(self, exercise=None, parent=None):
        super().__init__(parent)
        self.original=exercise
        self.result_exercise=None
        self.setWindowTitle('Criar curva personalizada')
        self.resize(920,650)
        root=QVBoxLayout(self)
        intro=QLabel('Defina a entrada esperada em cada 10% da duração. Os pontos ficam fixos no tempo e podem ser movidos de 0% a 100% do freio.')
        intro.setWordWrap(True); root.addWidget(intro)
        form=QFormLayout()
        self.name=QLineEdit(exercise.name if exercise else 'Minha curva de frenagem')
        self.duration=QDoubleSpinBox(); self.duration.setRange(5,10); self.duration.setDecimals(1); self.duration.setSuffix(' s'); self.duration.setValue(exercise.duration if exercise else 8)
        self.tolerance=QSpinBox(); self.tolerance.setRange(1,20); self.tolerance.setSuffix(' pp'); self.tolerance.setValue(round(exercise.tolerance*100) if exercise else 8)
        form.addRow('Nome',self.name); form.addRow('Duração',self.duration); form.addRow('Tolerância',self.tolerance); root.addLayout(form)
        values=[value*100 for _,value in exercise.target] if exercise else DEFAULT_VALUES
        self.editor=CurveEditorWidget(values); root.addWidget(self.editor,1)
        self.selected=QLabel(); self.editor.changed.connect(self._update_label); self._update_label(tuple(self.editor.values)); root.addWidget(self.selected)
        buttons=QHBoxLayout(); reset=QPushButton('Restaurar exemplo'); reset.clicked.connect(self._reset); save=QPushButton('Salvar curva'); save.clicked.connect(self._save); cancel=QPushButton('Cancelar'); cancel.clicked.connect(self.reject)
        buttons.addWidget(reset); buttons.addStretch(); buttons.addWidget(save); buttons.addWidget(cancel); root.addLayout(buttons)

    def _update_label(self,values):
        self.selected.setText('Pontos: '+ ' · '.join(f'{i*10}%:{value}%' for i,value in enumerate(values)))

    def _reset(self):
        for index,value in enumerate(DEFAULT_VALUES): self.editor.set_value(index,value)
        self.editor.selected=0; self.editor.update()

    def _save(self):
        name=self.name.text().strip()
        if not name:
            self.name.setFocus(); return
        duration=self.duration.value()
        target=tuple((duration*index/10,value/100) for index,value in enumerate(self.editor.values))
        payload={'id':self.original.id if self.original else f'custom-{uuid.uuid4().hex}', 'level':0,
                 'name':name,'objective':'Acompanhe a curva personalizada criada por você.','family':'custom',
                 'duration':duration,'target':target,'windows':((0,duration),),'tolerance':self.tolerance.value()/100,
                 'steering':((0,0),(duration,0)),'accelerator':((0,0),(duration,0)),
                 'version':(self.original.version+1 if self.original else 1),'formula':'brake-v1','custom':True}
        self.result_exercise=Exercise.from_dict(payload); self.accept()
