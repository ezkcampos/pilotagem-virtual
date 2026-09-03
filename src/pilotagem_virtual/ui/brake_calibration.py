import time
from dataclasses import replace

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QSlider, QHBoxLayout
from pilotagem_virtual.domain.calibration import calibrate_brake


class BrakeCalibrationDialog(QDialog):
    def __init__(self, controller, save, parent=None):
        super().__init__(parent)
        self.controller, self.save = controller, save
        self.original=controller.profile
        self.candidate=None
        self.rest=[]
        self.applications=[]
        self.stage='rest'
        self.started=None
        self.last_stamp=None
        self.setWindowTitle('Calibrar entrada do freio')
        self.resize(600,370)
        layout=QVBoxLayout(self)
        self.message=QLabel('1. Deixe o freio solto. Vamos registrar 2 segundos de repouso.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.value=QLabel('—')
        self.value.setStyleSheet('font-size: 36px; font-weight: bold')
        layout.addWidget(self.value)
        self.slider=QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(20,100)
        self.slider.setValue(100)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._maximum_changed)
        self.maximum_label=QLabel('Máximo de treino: 100% do curso observado')
        layout.addWidget(self.maximum_label)
        layout.addWidget(self.slider)
        self.action=QPushButton('Registrar repouso')
        self.action.clicked.connect(self.advance)
        cancel=QPushButton('Cancelar')
        cancel.clicked.connect(self.reject)
        row=QHBoxLayout()
        row.addWidget(self.action)
        row.addWidget(cancel)
        layout.addLayout(row)
        self.timer=QTimer(self)
        self.timer.setInterval(17)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def _maximum_changed(self,value):
        self.maximum_label.setText(f'Máximo de treino: {value}% do curso observado')
        if self.candidate:
            self.candidate=replace(self.candidate,brake=replace(self.candidate.brake,comfortable_max=value/100))

    def advance(self):
        if self.stage == 'preview':
            try:
                self.save(self.candidate)
            except (OSError,ValueError,RuntimeError) as error:
                self.message.setText(f'Não foi possível salvar: {error}. Você pode tentar novamente.')
                return
            self.accept()
        else:
            self.started=time.perf_counter_ns()
            self.last_stamp=None
            self.action.setEnabled(False)
            self.message.setText('Mantenha o pedal solto por 2 segundos.' if self.stage=='rest' else 'Aplique e solte duas vezes até seu máximo confortável. Registro por 4 segundos.')

    def tick(self):
        raw=self.controller.last_raw
        if not self.controller.available or raw is None or not raw.ready:
            self.value.setText('Sem leitura')
            self.action.setEnabled(False)
            if self.started is not None:
                self.started=None
                (self.rest if self.stage=='rest' else self.applications).clear()
                self.message.setText('Leitura interrompida. Cancele, detecte o dispositivo e refaça a calibração.')
            return
        if self.started is None:
            self.action.setEnabled(True)
        value=raw.axes[self.original.brake.axis]
        if self.candidate:
            self.value.setText(f'Entrada do freio: {self.candidate.brake.normalize(value)*100:.0f}%')
        if self.started is None:
            return
        duration=2 if self.stage=='rest' else 4
        elapsed=(time.perf_counter_ns()-self.started)/1e9
        self.value.setText(f'{max(0,duration-elapsed):.1f} s')
        if raw.timestamp_ns != self.last_stamp:
            (self.rest if self.stage=='rest' else self.applications).append(value)
            self.last_stamp=raw.timestamp_ns
        if elapsed < duration:
            return
        self.started=None
        self.action.setEnabled(True)
        if self.stage=='rest':
            self.stage='applications'
            self.message.setText('2. Registre duas aplicações completas dentro do seu conforto, soltando entre elas.')
            self.action.setText('Registrar curso do pedal')
        else:
            try:
                self.candidate=calibrate_brake(self.original,self.rest,self.applications)
            except ValueError as error:
                self.message.setText(f'{error}. Reinicie a calibração.')
                self.stage='rest'
                self.rest.clear()
                self.applications.clear()
                self.action.setText('Registrar repouso')
                return
            self.stage='preview'
            self.slider.setEnabled(True)
            self.message.setText(f'3. Confira 0% solto e 100% no máximo de treino. Ajuste o máximo abaixo, se desejar. Deadzone calculada: {self.candidate.brake.deadzone*100:.1f}%.')
            self.action.setText('Salvar calibração')

    def done(self,result):
        self.timer.stop()
        super().done(result)
