from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class ExecSlice:
    process: str
    start: int
    end: int

@dataclass
class ScheduleResult:
    # Secuencia de ejecución en el tiempo (para Gantt global si se desea)
    timeline: List[ExecSlice] = field(default_factory=list)
    # Para cada proceso: lista de intervalos de ejecución
    per_process_slices: Dict[str, List[Tuple[int, int]]] = field(default_factory=dict)
    # Métricas
    turnaround: Dict[str, int] = field(default_factory=dict)  # TR
    waiting: Dict[str, int] = field(default_factory=dict)     # TE
    avg_turnaround: Optional[float] = None
    avg_waiting: Optional[float] = None

@dataclass
class Process:
    name: str
    arrival: int
    burst: int  # Este puede mantenerse como suma total si querés compatibilidad
    pattern: Optional[List[Tuple[str, int]]] = None  # Ej: [("CPU", 3), ("BLOCK", 2), ("CPU", 4)]
