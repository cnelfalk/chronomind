import re
import customtkinter as ctk
from ..utils import DualScrollFrame
import tkinter.colorchooser

class ProcessTable(ctk.CTkFrame):
    def __init__(self, master, initial_rows=6):
        super().__init__(master)
        self.rows = []
        self._color_by_index = {}  # índice → color hex

        self.scroll = DualScrollFrame(self, height=270)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_frame = ctk.CTkFrame(self.scroll.inner_frame)
        self.content_frame.pack(fill="x", expand=True, pady=5)

        palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
            "#3182bd", "#31a354", "#756bb1", "#636363", "#e6550d"
        ]
        self._palette = palette

        self.grid_columnconfigure(0, weight=1)

        container = self.content_frame
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_columnconfigure(2, weight=1)

        headers = ["Proceso", "Tiempo de llegada", "Tiempo de ejecución"]
        for i, text in enumerate(headers):
            ctk.CTkLabel(container, text=text, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=i, padx=(10 if i == 0 else 20), pady=(5, 0), sticky="ew"
            )

        self.set_rows(initial_rows)

    def set_rows(self, count: int):
        current_data = []
        for row in self.rows:
            name_entry, arrival_frame, pattern_entry, *_ = row
            current_data.append({
                "name": name_entry.get(),
                "arrival": arrival_frame.entry.get(),
                "pattern_raw": pattern_entry.get()
            })

        for i in range(len(self.rows)):
            if i >= count:
                for w in self.rows[i]:
                    w.destroy()

        self.rows = self.rows[:count]

        for i in range(len(self.rows), count):
            container = self.content_frame
            container.grid_columnconfigure(3, weight=0)

            name = ctk.CTkEntry(container, width=160)
            arr = self._create_spinbox_field(container, i+1, 1, default_val=0, min_val=0)
            pattern_entry = ctk.CTkEntry(container, width=220, placeholder_text="Ej: 3,(2),4")

            name.grid(row=i+1, column=0, padx=(12, 12), pady=4, sticky="nsew")
            arr.grid(row=i+1, column=1, padx=(8, 12), pady=4, sticky="nsew")
            pattern_entry.grid(row=i+1, column=2, padx=(8, 12), pady=4, sticky="nsew")

            def choose_color(index, btn):
                color = tkinter.colorchooser.askcolor(title=f"Color para proceso {index+1}")[1]
                if color:
                    self._color_by_index[index] = color
                    btn.configure(fg_color=color)

            color_btn = ctk.CTkButton(container, text="🎨", width=36)
            color_btn.configure(command=lambda idx=i, btn=color_btn: choose_color(idx, btn))
            color_btn.grid(row=i+1, column=3, padx=(4, 12), pady=4)

            default_color = self._palette[i % len(self._palette)]
            self._color_by_index[i] = default_color
            color_btn.configure(fg_color=default_color)

            self.rows.append((name, arr, pattern_entry, color_btn))

        for i, row in enumerate(self.rows):
            name, arr, pattern_entry, _ = row
            if i < len(current_data):
                name.delete(0, "end"); name.insert(0, current_data[i]["name"])
                arr.entry.delete(0, "end"); arr.entry.insert(0, current_data[i]["arrival"])
                pattern_entry.delete(0, "end"); pattern_entry.insert(0, current_data[i]["pattern_raw"])
            else:
                name.delete(0, "end"); name.insert(0, f"P{i+1}")
                arr.entry.delete(0, "end"); arr.entry.insert(0, "0")
                pattern_entry.delete(0, "end"); pattern_entry.insert(0, "")

    def _create_spinbox_field(self, container, row, col, default_val, min_val=0, max_val=999):
        outer_frame = ctk.CTkFrame(container)
        outer_frame.grid(row=row, column=col, padx=10, pady=4, sticky="nsew")
        outer_frame.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(outer_frame)
        inner_frame.pack(anchor="center")

        def adjust(entry, delta):
            try:
                val = int(entry.get())
                new_val = max(min_val, min(max_val, val + delta))
                entry.delete(0, "end")
                entry.insert(0, str(new_val))
            except ValueError:
                entry.delete(0, "end")
                entry.insert(0, str(default_val))

        minus_btn = ctk.CTkButton(inner_frame, text="–", width=28, height=28, command=lambda: adjust(entry, -1))
        minus_btn.grid(row=0, column=0, padx=(0, 4))

        entry = ctk.CTkEntry(inner_frame)
        inner_frame.grid_columnconfigure(1, weight=1)
        entry.grid(row=0, column=1, sticky="ew")
        entry.insert(0, str(default_val))

        plus_btn = ctk.CTkButton(inner_frame, text="+", width=28, height=28, command=lambda: adjust(entry, 1))
        plus_btn.grid(row=0, column=2, padx=(4, 0))

        outer_frame.entry = entry
        return outer_frame

    @staticmethod
    def _parse_pattern(raw: str):
        if not raw:
            return None
        tokens = re.findall(r'\(?\d+\)?', raw)
        if not tokens:
            return None
        pattern = []
        try:
            for tok in tokens:
                if tok.startswith('(') and tok.endswith(')'):
                    pattern.append(("BLOCK", int(tok[1:-1])))
                else:
                    tok_clean = tok.strip("()")
                    pattern.append(("CPU", int(tok_clean)))
        except ValueError:
            return None
        return pattern

    def get_data(self):
        data = []
        for i, (name, arr, pattern_entry, _) in enumerate(self.rows):
            name_val = name.get().strip() or ""
            arrival_val = arr.entry.get().strip()
            pattern_raw = pattern_entry.get().strip()

            pattern = self._parse_pattern(pattern_raw)
            if pattern is None and pattern_raw.isdigit():
                pattern = [("CPU", int(pattern_raw))]

            burst = sum(d for k, d in (pattern or []) if k == "CPU")
            color = self._color_by_index.get(i, "#1f1f1f")

            data.append({
                "name": name_val,
                "arrival": arrival_val,
                "burst": str(burst),
                "color": color,
                "pattern": pattern,
                "pattern_raw": pattern_raw
            })

        return data

    def reset(self):
        for i, (name, arr, pattern_entry, _) in enumerate(self.rows):
            name.delete(0, "end"); name.insert(0, f"P{i+1}")
            arr.entry.delete(0, "end"); arr.entry.insert(0, "0")
            pattern_entry.delete(0, "end"); pattern_entry.insert(0, "")
