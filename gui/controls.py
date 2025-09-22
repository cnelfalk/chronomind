from CTkMessagebox import CTkMessagebox
import customtkinter as ctk
import string
import random

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
        popup.geometry("260x140")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        popup.update_idletasks()
        w, h = popup.winfo_width(), popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"+{x}+{y}")

        ctk.CTkLabel(popup, text="Selecciona una acción:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        ctk.CTkButton(popup, text="Nombrar procesos alfabéticamente",
                      command=lambda: [self._rename_processes(), popup.destroy()]).pack(pady=5)
        ctk.CTkButton(popup, text="Randomizar tiempos y patrones",
                      command=lambda: [self._randomize_processes(), popup.destroy()]).pack(pady=5)
        
        popup.after(110, lambda: popup.iconbitmap(self.app.icon_path))


    def _rename_processes(self):
        if hasattr(self.master, "table"):
            for i, (name_entry, *_rest) in enumerate(self.master.table.rows):
                name_entry.delete(0, "end")
                name_entry.insert(0, string.ascii_uppercase[i % 26])

    def _randomize_processes(self):
        # Randomiza llegada y patrón simple: ej. "a,(b),c" con valores chicos
        if hasattr(self.master, "table"):
            for (_name, arrival_frame, pattern_entry, *_rest) in self.master.table.rows:
                arrival_frame.entry.delete(0, "end")
                arrival_frame.entry.insert(0, str(random.randint(0, 5)))
                # patrón: CPU 1-5, opcional bloqueo 0-3, luego CPU 1-5
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
                fg_color="#FFFFFF",     # fondo blanco
                text_color="#000000"    # texto negro
            )
        else:
            self.quantum_entry.configure(
                state="disabled",
                fg_color="#A9A9A9",     # gris oscuro
                text_color="#555555"    # texto gris
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
