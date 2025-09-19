# Chronomind

<img width="1134" height="213" alt="chronomind-logoHD-withMiniLogo" src="https://github.com/user-attachments/assets/44a855e4-fe80-4a8f-bc49-4cdcde6443a8" />

Simulador gráfico de algoritmos de planificación de procesos, orientado a enseñanza, auditoría técnica y validación reproducible de métricas en sistemas operativos.

## Características

- Interfaz gráfica con `customtkinter`
- Algoritmos disponibles:
  - FIFO
  - SJF
  - SRTF (preemptivo)
  - Round Robin (quantum configurable)
- Ingreso flexible de patrones: `3,(2),4` representa CPU 3 → BLOQUEO 2 → CPU 4
- Visualización dinámica del diagrama de Gantt
- Cálculo automático de métricas por proceso:
  - Tiempo de Espera (TE)
  - Tiempo de Retorno (TR)
  - Promedios globales

- Acciones rápidas:
  - Nombrado alfabético
  - Randomización de tiempos y patrones
- Tema visual personalizable (`sistema_theme.json`)
  
## Requisitos

- Python 3.10+
- Paquetes:
  - `customtkinter`
  - `tkinter` (incluido en la mayoría de distribuciones)
  - `random`, `math`, `datetime` (estándar)

## Ejecución

```bash
python main.py
