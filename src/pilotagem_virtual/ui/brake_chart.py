from bisect import bisect_left
import time

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush
from PySide6.QtWidgets import QWidget
from pilotagem_virtual.domain.exercise import interpolate


class BrakeChart(QWidget):
    inspected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 300)
        self.exercise = None
        self.samples = ()
        self.reveal = True
        self.result = False
        self.progress = 0.
        self.simulation = None
        self.override_target = None
        self.frames = []
        self.recording = False
        self.setAccessibleName('Gráfico temporal da entrada do freio')

    def points(self):
        return self.override_target or (self.exercise.target if self.exercise else ((0.,0.),(8.,0.)))

    def plot_rect(self):
        return QRectF(58, 56, max(1,self.width()-84), max(1,self.height()-104))

    def paintEvent(self, event):
        started=time.perf_counter_ns()
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor('#101716'))
        p.setPen(QColor('#eee8dc'))
        p.drawText(16,24,'Entrada do freio (%)  ·  Tempo (s)')
        rect=self.plot_rect()
        duration=self.exercise.duration if self.exercise else 8.
        def point(t,v): return QPointF(rect.left()+t/duration*rect.width(),rect.bottom()-v*rect.height())
        for n in range(6):
            y=point(0,n/5).y()
            p.setPen(QColor('#34403e'))
            p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            p.setPen(QColor('#aab3b0'))
            p.drawText(18,int(y)+4,str(n*20))
        for n in range(int(duration)+1):
            p.drawText(int(point(n,0).x())-4,int(rect.bottom())+21,str(n))
        if self.reveal:
            target=self.points()
            tolerance=self.exercise.tolerance if self.exercise else .1
            band=QPainterPath()
            timeline=sorted({t for t,_ in target if t <= duration} | {duration})
            for i,t in enumerate(timeline):
                pt=point(t,min(1,interpolate(target,t)+tolerance))
                band.moveTo(pt) if i==0 else band.lineTo(pt)
            for t in reversed(timeline): band.lineTo(point(t,max(0,interpolate(target,t)-tolerance)))
            band.closeSubpath()
            p.fillPath(band,QBrush(QColor('#38403a'),Qt.BrushStyle.Dense6Pattern))
            path=QPainterPath()
            for i,t in enumerate(timeline):
                path.moveTo(point(t,interpolate(target,t))) if i==0 else path.lineTo(point(t,interpolate(target,t)))
            p.setPen(QPen(QColor('#e3b55c'),2,Qt.PenStyle.DashLine))
            p.drawPath(path)
            path=QPainterPath()
            previous=None
            p.setPen(QPen(QColor('#27c4df'),2))
            for sample in self.samples:
                t=sample.elapsed_ns/1e9
                pt=point(t,sample.controls.brake)
                if previous is None or t-previous > .05: path.moveTo(pt)
                else: path.lineTo(pt)
                previous=t
            p.drawPath(path)
            # Crosses identify out-of-band readings independently of color.
            p.setPen(QPen(QColor('#eee8dc'),1))
            last_mark=-1.
            for sample in self.samples:
                t=sample.elapsed_ns/1e9
                if t-last_mark >= .15 and abs(sample.controls.brake-interpolate(target,t)) > tolerance:
                    pt=point(t,sample.controls.brake)
                    p.drawLine(pt+QPointF(-3,-3),pt+QPointF(3,3))
                    p.drawLine(pt+QPointF(-3,3),pt+QPointF(3,-3))
                    last_mark=t
            if self.simulation:
                p.setPen(QPen(QColor('#aa96ff'),2,Qt.PenStyle.DotLine))
                effective=QPainterPath()
                for i,row in enumerate(self.simulation['rows']):
                    pt=point(row['time'],row['effective'])
                    effective.moveTo(pt) if i==0 else effective.lineTo(pt)
                p.drawPath(effective)
                for lock in self.simulation['locks']:
                    box=QRectF(point(lock['start'],1),point(lock['end'],0))
                    p.fillRect(box,QBrush(QColor('#be663f'),Qt.BrushStyle.BDiagPattern))
                    p.drawText(QPointF(box.left()+4,rect.top()+16),'TRAVADA')
            p.setPen(QColor('#aab3b0'))
            legend='— Execução   -- Alvo   ▒ Tolerância   × Fora da faixa'
            if self.simulation: legend+='   ··· Atuação virtual — Simulação didática'
            p.drawText(58,self.height()-9,legend)
        else:
            p.setPen(QColor('#aab3b0'))
            p.drawText(rect,Qt.AlignmentFlag.AlignCenter,'Comparação disponível ao terminar')
        if self.recording:
            p.setPen(QPen(QColor('#eee8dc'),1,Qt.PenStyle.DotLine))
            x=point(self.progress*duration,0).x()
            p.drawLine(QPointF(x,rect.top()),QPointF(x,rect.bottom()))
        p.end()
        if self.recording: self.frames.append(started)

    def mousePressEvent(self,event):
        if not self.result or not self.reveal or not self.samples:
            return
        duration=self.exercise.duration if self.exercise else 8.
        t=max(0,min(duration,(event.position().x()-self.plot_rect().left())/self.plot_rect().width()*duration))
        times=[s.elapsed_ns/1e9 for s in self.samples]
        i=min(len(times)-1,bisect_left(times,t))
        if i and abs(times[i-1]-t)<abs(times[i]-t): i-=1
        sample=self.samples[i]
        self.inspected.emit(f'Leitura real em {times[i]:.3f} s: freio {sample.controls.brake*100:.1f}% · alvo {interpolate(self.points(),times[i])*100:.1f}%')
