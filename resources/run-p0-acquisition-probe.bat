@echo off
start "Pilotagem Virtual - P0" "%~dp0PilotagemVirtual.exe" --acquisition-probe --source g29 --context worker --output-dir "%~dp0medicoes-p0"
