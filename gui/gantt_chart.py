import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import List, Dict
from ..core.models import ExecSlice, Process

class GanttChart(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self._processes: List[Process] = []
        self._timeline: List[ExecSlice] = []
        self._color_by_name: Dict[str, str] = {}

        self.figure = Figure(figsize=(10, 4.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def set_colors(self, color_map: Dict[str, str]):
        self._color_by_name = color_map.copy()

    def clear(self):
        self._processes = []
        self._timeline = []
        self.ax.clear()
        self.canvas.draw()
    
    def _merge_timeline(self, timeline):
        if not timeline:
            return []

        merged = [timeline[0]]
        for sl in timeline[1:]:
            last = merged[-1]
            # Unir solo si es el mismo proceso (incluyendo bloques) y son contiguos
            if sl.process == last.process and sl.start == last.end:
                merged[-1] = type(sl)(sl.process, last.start, sl.end)
            else:
                merged.append(sl)
        return merged

    def draw(self, processes: List[Process], timeline: List[ExecSlice]):
        self._processes = processes
        self._timeline = self._merge_timeline(timeline or [])
        self._redraw()

    def _redraw(self):
        self.ax.clear()

        # Mantener orden original
        procs_sorted = self._processes
        name_to_row = {p.name: i for i, p in enumerate(procs_sorted)}

        # Eje Y
        yticks = list(range(len(procs_sorted)))
        ylabels = [p.name for p in procs_sorted]
        self.ax.set_yticks(yticks)
        self.ax.set_yticklabels(ylabels)

        # Sombra hasta arrival
        for p in procs_sorted:
            row = name_to_row[p.name]
            if p.arrival > 0:
                self.ax.barh(row, p.arrival, left=0, height=0.6, color="black", alpha=0.15, zorder=0)

        # Timeline
        for sl in self._timeline:
            is_block = "_BLOCK" in sl.process
            raw_base = sl.process.replace("_BLOCK", "")
            base_name = raw_base.strip()

            # Mapeo robusto a fila
            row = name_to_row.get(base_name)
            if row is None:
                base_lc = base_name.lower()
                for k, r in name_to_row.items():
                    if k.strip().lower() == base_lc:
                        row = r
                        base_name = k
                        break
                if row is None:
                    continue

            start, end = sl.start, sl.end
            dur = max(0, end - start)
            if dur == 0:
                continue

            color = self._color_by_name.get(base_name, "#1f1f1f")
            alpha = 0.45 if is_block else 1.0
            label = "BLOCK" if is_block else base_name

            self.ax.barh(
                row, dur, left=start, height=0.6,
                color=color, alpha=alpha,
                edgecolor="#333333", linewidth=1.0
            )
            self.ax.text(start + dur / 2, row, label, ha="center", va="center", color="white", fontsize=9)

        self.ax.set_xlabel("Tiempo")

        # Extender X hasta el fin real del timeline
        max_time = max((sl.end for sl in self._timeline), default=1)
        self.ax.set_xlim(0, max_time)
        self.ax.xaxis.set_major_locator(MultipleLocator(1))
        self.ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))

        # Guías
        for y in yticks:
            self.ax.axhline(y=y + 0.5, color="#cccccc", linestyle="--", linewidth=0.5, zorder=0)

        self.ax.grid(True, axis="x", linestyle="--", alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()
