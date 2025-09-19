import customtkinter as ctk

class DualScrollFrame(ctk.CTkFrame):
    def __init__(self, master, width=600, height=200, bg_color="#2b2b2b"):
        super().__init__(master)

        # Canvas para contener el contenido desplazable
        self.canvas = ctk.CTkCanvas(self, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.h_scrollbar = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.v_scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)

        # Frame interno que contendrá los widgets
        self.inner_frame = ctk.CTkFrame(self.canvas, fg_color=bg_color)

        # Crear ventana dentro del canvas con tag para poder modificarla
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw", tags="inner")

        # Configurar scroll
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)

        # Posicionar elementos
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")

        # Expandir canvas dentro del frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Actualizar región de scroll cuando el contenido cambia
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Asegurar que el ancho del inner_frame se ajuste al canvas
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("inner", width=e.width))
