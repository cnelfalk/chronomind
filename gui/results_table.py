import customtkinter as ctk
from typing import List, Dict
from ..core.models import Process

class ResultsTable(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.body = ctk.CTkScrollableFrame(self, height=270)
        self.body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._labels = []

        for col in range(6):
            self.body.grid_columnconfigure(col, weight=1)

    def clear(self):
        for w in self._labels:
            w.destroy()
        self._labels.clear()
        for w in self.body.winfo_children():
            w.destroy()

    def update(self, processes: List[Process], tr: Dict[str,int], te: Dict[str,int], avg_tr: float, avg_te: float):
        self.clear()

        headers = ["Proceso", "Llegada", "CPU", "Salida", "TR", "TE"]
        for j, h in enumerate(headers):
            cell = ctk.CTkFrame(self.body, fg_color="#200a0a", corner_radius=4)
            cell.grid(row=0, column=j, padx=1, pady=1, sticky="nsew")
            lbl = ctk.CTkLabel(cell, text=h, font=ctk.CTkFont(weight="bold"))
            lbl.pack(padx=6, pady=4)

        for i, p in enumerate(processes, start=1):
            # Clamp defensivo: evitar mostrar negativos si hubiera alguna inconsistencia upstream
            tr_val = max(0, tr.get(p.name, 0))
            te_val = max(0, te.get(p.name, 0))
            salida = p.arrival + tr_val
            fila = [p.name, p.arrival, p.burst, salida, tr_val, te_val]
            for j, val in enumerate(fila):
                cell = ctk.CTkFrame(self.body, fg_color="#2e2e2e", corner_radius=4)
                cell.grid(row=i, column=j, padx=1, pady=1, sticky="nsew")
                ctk.CTkLabel(cell, text=str(val)).pack(padx=6, pady=4)

        # Fila de promedios
        row = self.body.grid_size()[1]
        avg_tr_disp = max(0.0, avg_tr if avg_tr is not None else 0.0)
        avg_te_disp = max(0.0, avg_te if avg_te is not None else 0.0)
        promedio = ["Promedio", "—", "—", "—", f"{avg_tr_disp:.2f}", f"{avg_te_disp:.2f}"]
        for j, val in enumerate(promedio):
            cell = ctk.CTkFrame(self.body, fg_color="#af53ab", corner_radius=4)
            cell.grid(row=row, column=j, padx=1, pady=4, sticky="nsew")
            font = ctk.CTkFont(weight="bold") if j == 0 else None
            ctk.CTkLabel(cell, text=val, font=font, anchor="center").pack(padx=6, pady=4)
