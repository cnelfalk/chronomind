import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from .controls import ControlsFrame
from .process_table import ProcessTable
from .gantt_chart import GanttChart
from .results_table import ResultsTable
from ..core.models import Process
from ..core.scheduler_factory import SchedulerFactory
import os

class SchedulerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Planificación de procesos")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        self.icon_path = os.path.join(os.path.dirname(__file__), "media", "logo-sistemaplanificacion.ico")
        self.iconbitmap(self.icon_path)

        theme_path = os.path.join(os.path.dirname(__file__), "..", "sistema_theme.json")
        ctk.set_default_color_theme(theme_path)

        window_width = 1250
        window_height = 570
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        ctk.set_appearance_mode("System")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.controls = ControlsFrame(
            self,
            algorithms=SchedulerFactory.list_algorithms(),
            on_calculate=self.on_calculate,
            on_reset=self.on_reset,
            app=self
        )
        self.controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        tables_frame = ctk.CTkFrame(self)
        tables_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tables_frame.grid_columnconfigure(0, weight=1)
        tables_frame.grid_columnconfigure(1, weight=1)

        self.table = ProcessTable(tables_frame, initial_rows=6)
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

        self.results = ResultsTable(tables_frame)
        self.results.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)

        self.gantt = GanttChart(self)
        self.gantt.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))

    def show_fullscreen_gantt(self):
        if not self.gantt._timeline:
            CTkMessagebox(title="Aviso", message="Primero debes calcular el gráfico.", icon="info")
            return

        fullscreen_win = ctk.CTkToplevel(self)
        fullscreen_win.after(10, lambda: fullscreen_win.iconbitmap(self.icon_path))
        fullscreen_win.attributes("-fullscreen", True)
        fullscreen_win.configure(fg_color="white")
        fullscreen_win.bind("<Escape>", lambda e: fullscreen_win.destroy())

        gantt_container = ctk.CTkFrame(fullscreen_win)
        gantt_container.pack(fill="both", expand=True)

        gantt_full = GanttChart(gantt_container)
        gantt_full.pack(fill="both", expand=True)

        processes = []
        for row in self.table.get_data():
            try:
                processes.append(Process(
                    name=row["name"].strip(),
                    arrival=int(row["arrival"]),
                    burst=int(row["burst"]),
                    pattern=row["pattern"]
                ))
            except Exception:
                continue

        color_map = {row["name"]: row["color"] for row in self.table.get_data()}
        gantt_full.set_colors(color_map)
        gantt_full.draw(processes, self.gantt._timeline)

        close_btn = ctk.CTkButton(fullscreen_win, text="Cerrar", command=fullscreen_win.destroy)
        close_btn.place(relx=0.98, rely=0.02, anchor="ne")

        fullscreen_win.focus_force()
        fullscreen_win.lift()
        fullscreen_win.grab_set()

    def on_reset(self):
        self.table.reset()
        self.gantt.clear()
        self.results.clear()

    def on_calculate(self):
        data = self.table.get_data()
        processes = []

        for row in data:
            name = (row["name"] or "").strip()
            if not name:
                CTkMessagebox(title="Error", message="Hay procesos sin nombre.", icon="cancel")
                return
            try:
                arrival = int(row["arrival"])
            except ValueError:
                CTkMessagebox(title="Error", message=f"Llegada inválida en {name}.", icon="cancel")
                return

            pattern = row["pattern"]
            burst = int(row["burst"]) if row["burst"].isdigit() else 0

            if pattern is None or burst <= 0:
                CTkMessagebox(
                    title="Error",
                    message=f"Patrón inválido o vacío en {name}. Escribe algo como: 3,(2),4 o 5.",
                    icon="cancel"
                )
                return

            processes.append(Process(
                name=name,
                arrival=arrival,
                burst=burst,
                pattern=pattern
            ))

        color_map = {row["name"]: row["color"] for row in data}
        self.gantt.set_colors(color_map)

        algo = self.controls.get_algorithm()
        quantum = self.controls.get_quantum()
        if algo == "Round Robin" and (quantum is None or quantum <= 0):
            return

        strategy = SchedulerFactory.create(algo)
        try:
            result = strategy.schedule(processes, quantum=quantum)

            def orden_cpu(timeline):
                seq = []
                for sl in timeline:
                    if sl.process.endswith("_BLOCK"):
                        continue
                    if not seq or seq[-1] != sl.process:
                        seq.append(sl.process)
                return seq

            print("Orden de ejecución (sin bloques):", " > ".join(orden_cpu(result.timeline)))

        except Exception as ex:
            CTkMessagebox(title="Error", message=str(ex), icon="cancel")
            return

        self.gantt.draw(processes, result.timeline)
        self.results.update(processes, result.turnaround, result.waiting, result.avg_turnaround, result.avg_waiting)
