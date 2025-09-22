# app/gui/controls.py
from CTkMessagebox import CTkMessagebox
import customtkinter as ctk
import string
import random
import os
from ..exportacion.exportador_excel import ExportadorExcel

class ControlsFrame(ctk.CTkFrame):
    def __init__(self, master, algorithms, on_calculate, on_reset, app):
        super().__init__(master)
        self.on_calculate = on_calculate
        self.on_reset = on_reset
        self.app = app

        self.grid_columnconfigure(6, weight=1)

        # Algoritmo
        ctk.CTkLabel(self, text="Algoritmo:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.algobox = ctk.CTkComboBox(
            self, values=algorithms, state="readonly", command=self._on_algorithm_change
        )
        self.algobox.set(algorithms[0])
        self.algobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Quantum
        ctk.CTkLabel(self, text="Quantum (RR):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.quantum_entry = ctk.CTkEntry(self, width=80)
        self.quantum_entry.insert(0, "2")
        self.quantum_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Cantidad de procesos
        ctk.CTkLabel(self, text="Cantidad de procesos:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.count_box = ctk.CTkComboBox(
            self, values=[str(i) for i in range(1, 21)], state="readonly", width=70, command=self._on_count_change
        )
        self.count_box.set("6")
        self.count_box.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # Botones
        self.calc_btn = ctk.CTkButton(self, text="Calcular", command=self.on_calculate)
        self.calc_btn.grid(row=0, column=7, padx=5, pady=5)
        self.reset_btn = ctk.CTkButton(self, text="Reiniciar tabla", fg_color="gray", command=self.on_reset)
        self.reset_btn.grid(row=0, column=8, padx=5, pady=5)
        self.fullscreen_btn = ctk.CTkButton(self, text="Pantalla completa", command=self._on_fullscreen)
        self.fullscreen_btn.grid(row=0, column=9, padx=5, pady=5)
        self.actions_btn = ctk.CTkButton(self, text="Acciones rápidas", command=self._show_actions_menu)
        self.actions_btn.grid(row=0, column=10, padx=5, pady=5)

        # Estado inicial del campo Quantum
        self._on_algorithm_change(self.algobox.get())

    def _show_actions_menu(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Acciones")
        popup.geometry("260x165")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        popup.update_idletasks()
        w, h = popup.winfo_width(), popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"+{x}+{y}")

        ctk.CTkLabel(popup, text="Selecciona una acción:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))

        def _action_then_close(fn):
            def wrapper():
                try:
                    try:
                        popup.grab_release()
                    except Exception:
                        pass
                    fn()
                    try:
                        if self.master and hasattr(self.master, "focus_force"):
                            self.master.focus_force()
                        elif self.master and hasattr(self.master, "focus_set"):
                            self.master.focus_set()
                    except Exception:
                        pass
                finally:
                    try:
                        if popup.winfo_exists():
                            popup.after(80, lambda: popup.destroy() if popup.winfo_exists() else None)
                    except Exception:
                        pass
            return wrapper

        ctk.CTkButton(popup, text="Nombrar procesos alfabéticamente",
                      command=_action_then_close(self._rename_processes)).pack(pady=5)
        ctk.CTkButton(popup, text="Randomizar tiempos y patrones",
                      command=_action_then_close(self._randomize_processes)).pack(pady=5)
        ctk.CTkButton(popup, text="Exportar a Excel", command=_action_then_close(self._export_excel)).pack(pady=5)

        try:
            if popup.winfo_exists():
                popup.iconbitmap(self.app.icon_path)
        except Exception:
            pass

    def _rename_processes(self):
        if hasattr(self.master, "table"):
            for i, (name_entry, *_rest) in enumerate(self.master.table.rows):
                name_entry.delete(0, "end")
                name_entry.insert(0, string.ascii_uppercase[i % 26])

    def _randomize_processes(self):
        if hasattr(self.master, "table"):
            for (_name, arrival_frame, pattern_entry, *_rest) in self.master.table.rows:
                arrival_frame.entry.delete(0, "end")
                arrival_frame.entry.insert(0, str(random.randint(0, 5)))
                a = random.randint(1, 5)
                b = random.randint(0, 3)
                c = random.randint(1, 5)
                pattern = f"{a},({b}),{c}" if b > 0 else f"{a},{c}"
                pattern_entry.delete(0, "end")
                pattern_entry.insert(0, pattern)

    def _on_algorithm_change(self, value):
        if value == "Round Robin":
            self.quantum_entry.configure(
                state="normal",
                fg_color="#FFFFFF",
                text_color="#000000"
            )
        else:
            self.quantum_entry.configure(
                state="disabled",
                fg_color="#A9A9A9",
                text_color="#555555"
            )

    def _on_fullscreen(self):
        self.app.show_fullscreen_gantt()

    def _on_count_change(self, value):
        if hasattr(self.master, "table"):
            self.master.table.set_rows(int(value))

    def get_algorithm(self):
        return self.algobox.get()

    def get_quantum(self):
        txt = self.quantum_entry.get().strip()
        if txt.isdigit():
            return int(txt)
        else:
            CTkMessagebox(
                title="Error de Quantum",
                message="Por favor, ingresa un número entero válido para el Quantum.",
                icon="cancel"
            )
            return None
        
    def _export_excel(self):
        if not hasattr(self.app, "_last_schedule_result") or not self.app._last_schedule_result:
            CTkMessagebox(title="Aviso", message="Primero debes calcular antes de exportar.", icon="info")
            return

        from tkinter import filedialog
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx")],
            title="Guardar como..."
        )
        if not ruta:
            return

        try:
            exp = ExportadorExcel()
            exp.exportar_con_gantt(
            ruta,
            resultado=self.app._last_schedule_result,
            opciones={"color_cpu_por_pid": self.app._last_colors},
            procesos=self.app._last_processes,
            hojas=[
                # ======= Hoja Procesos =======
                ("Procesos", (lambda: [
                    *[
                        {"Proceso": p.name,
                        "Llegada": p.arrival,
                        "Burst": p.burst,
                        "Patrón": str(p.pattern)}
                        for p in self.app._last_processes
                    ],
                    # Fila extra con la suma total de CPU
                    {"Proceso": "TOTAL CPU",
                    "Llegada": "",
                    "Burst": sum(p.burst for p in self.app._last_processes),
                    "Patrón": ""}
                ])()),

                # ======= Hoja Métricas =======
                ("Métricas", (lambda: [
                    *[
                        {"Proceso": pid,
                        "Turnaround": self.app._last_schedule_result.turnaround.get(pid, ""),
                        "Waiting": self.app._last_schedule_result.waiting.get(pid, "")}
                        for pid in self.app._last_schedule_result.turnaround.keys()
                    ],
                    # Fila extra con promedios
                    {"Proceso": "PROMEDIO",
                    "Turnaround": round(self.app._last_schedule_result.avg_turnaround, 2),
                    "Waiting": round(self.app._last_schedule_result.avg_waiting, 2)}
                ])())
            ]
        )

            CTkMessagebox(
                title="Éxito",
                message=f"Exportación completada.\nArchivo guardado en:\n{os.path.abspath(ruta)}",
                icon="check"
            )

        except Exception as e:
            CTkMessagebox(title="Error", message=f"No se pudo exportar: {e}", icon="cancel")


    