# Chronomind

<img width="1134" height="213" alt="chronomind-logoHD-withMiniLogo" src="https://github.com/user-attachments/assets/44a855e4-fe80-4a8f-bc49-4cdcde6443a8" />

Simulador gráfico de algoritmos de planificación de procesos, orientado a enseñanza, auditoría técnica y validación reproducible de métricas en sistemas operativos.

## Características

- Interfaz gráfica basada en CustomTkinter  
- Cuatro estrategias de planificación  
  - FIFO (no preemptivo)  
  - SJF (no preemptivo, shortest job first)  
  - SRTF (preemptivo, shortest remaining time first)  
  - Round Robin con quantum configurable  
- Ingreso de patrones en formato flexible  
  Ejemplo: `3,(2),4` representa CPU 3 → BLOQUEO 2 → CPU 4  
- Diagrama de Gantt interactivo con zoom y pan  
- Cálculo automático de métricas por proceso  
  - Tiempo de Retorno (TR)  
  - Tiempo de Espera (TE)  
  - Promedios globales  
- Acciones rápidas desde la interfaz  
  - Renombrar procesos en orden alfabético  
  - Randomizar tiempos y patrones  
  - Exportar resultados a Excel  
- Tema visual personalizable mediante `sistema_theme.json`  
- **Instalador nativo solo para Windows**, crea acceso directo y registra el comando `chronomind`. Incluye un intérprete Python portable y todas las dependencias, por lo que el usuario NO necesita tener Python ni librerías instaladas.

---

## Requisitos

- Para la versión instalada en Windows: **no se requiere Python ni pip**.  
- Para ejecutar desde código o en Linux:  
  - Python 3.10 o superior  
  - Paquetes de Python:
    ```bash
    pip install customtkinter matplotlib openpyxl CTkMessagebox
    ```

---

## Instalación en Windows

1. Descarga el instalador `.exe` desde la última release.  
2. Ejecuta el instalador y sigue los pasos del asistente.  
3. Se creará un acceso directo en el Menú Inicio y se registrará el comando `chronomind` en la terminal.  

> Para desinstalar, usa el panel de “Agregar o quitar programas” de Windows.

---

## Uso

- Desde el Menú Inicio o en la terminal de Windows:
  ```bash
  chronomind
