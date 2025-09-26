# app/gui/results_table.py

import customtkinter as ctk
from typing import List, Dict
from ..core.models import Process

class ResultsTable(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Layout: 3 filas => 0: header (fijo), 1: body (expandible), 2: footer (fijo)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # Header (fila 0)
        self.header = ctk.CTkFrame(self, fg_color="#200a0a", corner_radius=4)
        self.header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        headers = ["Proceso", "Llegada", "CPU", "Salida", "TR", "TE"]
        for j, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.header,
                text=h,
                font=ctk.CTkFont(weight="bold")
            )
            lbl.grid(row=0, column=j, padx=4, pady=2, sticky="nsew")
            self.header.grid_columnconfigure(j, weight=1)

        # Body (fila 1): scrollable
        self.body = ctk.CTkScrollableFrame(self, height=200)
        self.body.grid(row=1, column=0, sticky="nsew", padx=8, pady=0)
        for j in range(len(headers)):
            self.body.grid_columnconfigure(j, weight=1)

        # Footer (fila 2)
        self.footer = ctk.CTkFrame(
            self,
            fg_color="#af53ab",
            corner_radius=4,
            height=32      # altura fija para que no crezca
        )
        self.footer.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.footer.grid_propagate(False)  # desactiva propagación para respetar height

    def clear(self):
        # Borra filas de datos
        for w in self.body.winfo_children():
            w.destroy()
        # Borra footer
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

        # Poblamos la body
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

        # Poblamos el footer con el promedio
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
