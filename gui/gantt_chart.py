import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseButton
from typing import List, Dict, Tuple
from ..core.models import ExecSlice, Process

class GanttChart(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self._processes: List[Process] = []
        self._timeline: List[ExecSlice] = []
        self._color_by_name: Dict[str, str] = {}

        # Zoom/pan
        self._zoom_factor = 1.2
        self._dragging = False
        self._press_event = None
        self._orig_xlim: Tuple[float, float] = (0.0, 1.0)
        self._orig_ylim: Tuple[float, float] = (0.0, 1.0)

        # Límites “full” que reflejan TODO el timeline y filas
        self._full_xlim: Tuple[float, float] = (0.0, 1.0)
        self._full_ylim: Tuple[float, float] = (0.0, 1.0)

        # Canvas / figura
        self.figure = Figure(figsize=(10, 4.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Eventos de ratón
        cid = self.canvas.mpl_connect
        cid('button_press_event',   self._on_press)
        cid('button_release_event', self._on_release)
        cid('motion_notify_event',  self._on_motion)
        cid('scroll_event',         self._on_scroll)

    def set_colors(self, color_map: Dict[str, str]):
        self._color_by_name = color_map.copy()

    def clear(self):
        self._processes = []
        self._timeline = []
        self._first_draw = True
        self.ax.clear()
        self.canvas.draw_idle()

    def _merge_timeline(self, timeline: List[ExecSlice]) -> List[ExecSlice]:
        if not timeline:
            return []
        merged = [timeline[0]]
        for sl in timeline[1:]:
            last = merged[-1]
            if sl.process == last.process and sl.start == last.end:
                merged[-1] = type(sl)(sl.process, last.start, sl.end)
            else:
                merged.append(sl)
        return merged

    def draw(self, processes: List[Process], timeline: List[ExecSlice]):
        self._processes = processes
        self._timeline = self._merge_timeline(timeline or [])
        self._redraw()

    def _compute_full_bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        max_t = max((sl.end for sl in self._timeline), default=1.0)
        proc_n = len(self._processes)
        return (0.0, float(max_t)), (-0.5, float(proc_n) - 0.5)

    def _redraw(self):
        self.ax.clear()
        procs = self._processes
        name_to_row = {p.name: i for i, p in enumerate(procs)}
        yticks = list(range(len(procs)))
        ylabels = [p.name for p in procs]
        self.ax.set_yticks(yticks)
        self.ax.set_yticklabels(ylabels)

        for p in procs:
            r = name_to_row[p.name]
            if p.arrival > 0:
                self.ax.barh(r, p.arrival, left=0, height=0.6,
                             color="black", alpha=0.15, zorder=0)

        for sl in self._timeline:
            is_block = sl.process.endswith("_BLOCK")
            base = sl.process.replace("_BLOCK", "").strip()
            r = name_to_row.get(base)
            if r is None:
                continue
            start, end = sl.start, sl.end
            dur = max(0.0, end - start)
            if dur == 0.0:
                continue

            color = self._color_by_name.get(base, "#1f1f1f")
            alpha = 0.45 if is_block else 1.0
            self.ax.barh(r, dur, left=start, height=0.6,
                         color=color, alpha=alpha,
                         edgecolor="#333333", linewidth=1.0)
            label = "IO" if is_block else base
            self.ax.text(start + dur/2, r, label,
                         ha="center", va="center",
                         color="white", fontsize=9)

        self.ax.set_xlabel("Tiempo")
        self._full_xlim, self._full_ylim = self._compute_full_bounds()

        cur_x0, cur_x1 = self.ax.get_xlim()
        fx0, fx1 = self._full_xlim
        if abs(cur_x1 - cur_x0) < 1e-6 or (cur_x0 < fx0 or cur_x1 > fx1):
            self.ax.set_xlim(*self._full_xlim)
        fy0, fy1 = self._full_ylim
        self.ax.set_ylim(fy0, fy1)

        self.ax.xaxis.set_major_locator(MultipleLocator(1))
        self.ax.xaxis.set_major_formatter(FormatStrFormatter('%d'))
        for y in yticks:
            self.ax.axhline(y=y + 0.5,
                            color="#cccccc",
                            linestyle="--",
                            linewidth=0.5,
                            zorder=0)
        self.ax.grid(True, axis="x", linestyle="--", alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    # — Mouse handlers —

    def _on_press(self, event):
        if event.inaxes != self.ax or event.button != MouseButton.LEFT:
            return
        self._dragging = True
        self._press_event = (event.x, event.y)  # usar píxeles
        self._orig_xlim = self.ax.get_xlim()
        self._orig_ylim = self.ax.get_ylim()

    def _on_motion(self, event):
        if not self._dragging or event.inaxes != self.ax:
            return
        if event.x is None or event.y is None:
            return

        dx_pix = event.x - self._press_event[0]
        dy_pix = event.y - self._press_event[1]

        dx_data = dx_pix * (self._orig_xlim[1] - self._orig_xlim[0]) / self.ax.bbox.width
        dy_data = dy_pix * (self._orig_ylim[1] - self._orig_ylim[0]) / self.ax.bbox.height

        new_l = self._orig_xlim[0] - dx_data
        new_r = self._orig_xlim[1] - dx_data
        new_b = self._orig_ylim[0] - dy_data
        new_t = self._orig_ylim[1] - dy_data

        new_l, new_r = self._clamp_snap(self._full_xlim, new_l, new_r)
        new_b, new_t = self._clamp_snap(self._full_ylim, new_b, new_t)

        self.ax.set_xlim(new_l, new_r)
        self.ax.set_ylim(new_b, new_t)
        self.canvas.draw_idle()

    def _on_release(self, event):
        if event.button == MouseButton.LEFT:
            self._dragging = False
            self._press_event = None

    def _on_scroll(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        factor = (1 / self._zoom_factor) if event.button == 'up' else self._zoom_factor
        self._zoom_at(event.xdata, event.ydata, factor)

    def _zoom_at(self, x: float, y: float, factor: float):
        l0, r0 = self.ax.get_xlim()
        b0, t0 = self.ax.get_ylim()
        width = (r0 - l0) * factor
        height = (t0 - b0) * factor

        new_l = x - (x - l0) * factor
        new_b = y - (y - b0) * factor
        new_r = new_l + width
        new_t = new_b + height

        new_l, new_r = self._clamp_snap(self._full_xlim, new_l, new_r)
        new_b, new_t = self._clamp_snap(self._full_ylim, new_b, new_t)

        self.ax.set_xlim(new_l, new_r)
        self.ax.set_ylim(new_b, new_t)
        self.canvas.draw_idle()

    def _clamp_snap(self, full: Tuple[float, float], low: float, high: float) -> Tuple[float, float]:
        full_low, full_high = full
        span = high - low
        eps = 1e-3
        if span >= (full_high - full_low) - eps:
            return full_low, full_high
        if abs(low - full_low) < eps:
            low, high = full_low, full_low + span
        elif abs(high - full_high) < eps:
            high, low = full_high, full_high - span
        else:
            if low < full_low:
                low, high = full_low, full_low + span
            elif high > full_high:
                high, low = full_high, full_high - span
        return low, high
