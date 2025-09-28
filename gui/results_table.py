# app/gui/results_table.py

import customtkinter as ctk
from typing import List, Dict
from ..core.models import Process

class ResultsTable(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Layout: 2 filas => 0: body (scrollable con encabezado + datos), 1: footer (fijo)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Body (fila 0): scrollable
        self.body = ctk.CTkScrollableFrame(self, height=200)
        self.body.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        # Configurar columnas del body
        for col in range(6):
            self.body.grid_columnconfigure(col, weight=1)

        # Footer (fila 1): promedios
        self.footer = ctk.CTkFrame(
            self,
            fg_color="#af53ab",
            corner_radius=4,
            height=32      # altura fija para que no crezca
        )
        self.footer.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.footer.grid_propagate(False)

    def clear(self):
        # Borra filas (incluyendo encabezado) del body
        for w in self.body.winfo_children():
            w.destroy()
        # Borra footer (promedios)
        for w in self.footer.winfo_children():
            w.destroy()

    def update(
        self,
        processes: List[Process],
        tr: Dict[str, int],
        te: Dict[str, int],
        avg_tr: float,
        avg_te: float
    ):
        self.clear()

        # 1) Encabezado dentro del scrollable body
        headers = ["Proceso", "Llegada", "CPU", "Salida", "TR", "TE"]
        for j, h in enumerate(headers):
            cell = ctk.CTkFrame(
                self.body,
                fg_color="#200a0a",
                corner_radius=4
            )
            cell.grid(row=0, column=j, padx=1, pady=1, sticky="nsew")
            lbl = ctk.CTkLabel(cell, text=h, font=ctk.CTkFont(weight="bold"))
            lbl.pack(padx=4, pady=2)

        # 2) Filas de datos
        for i, p in enumerate(processes, start=1):
            tr_val = max(0, tr.get(p.name, 0))
            te_val = max(0, te.get(p.name, 0))
            salida = p.arrival + tr_val
            fila_vals = [
                p.name, p.arrival, p.burst,
                salida, tr_val, te_val
            ]
            for j, val in enumerate(fila_vals):
                cell = ctk.CTkFrame(
                    self.body,
                    fg_color="#2e2e2e",
                    corner_radius=4
                )
                cell.grid(row=i, column=j, padx=1, pady=1, sticky="nsew")
                lbl = ctk.CTkLabel(cell, text=str(val))
                lbl.pack(padx=4, pady=2)

        # 3) Footer con promedio (permanece fijo)
        avg_tr_disp = max(0.0, avg_tr or 0.0)
        avg_te_disp = max(0.0, avg_te or 0.0)
        footer_vals = [
            "Promedio", "—", "—", "—",
            f"{avg_tr_disp:.2f}", f"{avg_te_disp:.2f}"
        ]
        for j, val in enumerate(footer_vals):
            cell = ctk.CTkFrame(
                self.footer,
                fg_color="#af53ab",
                corner_radius=4
            )
            cell.grid(row=0, column=j, padx=1, pady=1, sticky="nsew")
            font = ctk.CTkFont(weight="bold") if j == 0 else None
            lbl = ctk.CTkLabel(cell, text=str(val), font=font)
            lbl.pack(padx=4, pady=2)
            self.footer.grid_columnconfigure(j, weight=1)
