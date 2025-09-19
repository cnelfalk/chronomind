from typing import List, Optional, Dict, Tuple
from collections import deque
from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class FIFO(SchedulerStrategy):
    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        # Orden estable por llegada para iterar altas
        procs = processes  # mantener orden original
        n = len(procs)

        time = 0
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in procs}
        completion: Dict[str, int] = {}
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}

        # Copia de patrones; si no hay, usar CPU total
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)])
            for p in procs
        }

        arrivals = {p.name: p.arrival for p in procs}
        blocked: Dict[str, int] = {}           # proceso -> t de desbloqueo
        ready: deque[str] = deque()            # cola FIFO por disponibilidad real
        done = set()
        idx = 0                                # puntero de llegadas

        # Estado del proceso activo (no-preemptivo)
        active: Optional[str] = None
        seg_kind: Optional[str] = None
        seg_rem: int = 0                       # duración restante del segmento CPU activo

        def enqueue_arrivals(up_to_t: int):
            nonlocal idx
            while idx < n and procs[idx].arrival <= up_to_t:
                name = procs[idx].name
                if name not in done and name not in blocked and name not in ready:
                    ready.append(name)
                idx += 1

        def unblock_ready(at_t: int):
            # Mover procesos cuyo bloqueo terminó en o antes de at_t
            for name in sorted(list(blocked), key=lambda k: blocked[k]):
                if blocked[name] <= at_t:
                    blocked.pop(name)
                    if name not in done and name not in ready:
                        ready.append(name)

        def next_arrival_after(t: int) -> Optional[int]:
            return procs[idx].arrival if idx < n else None

        def next_unblock_after(t: int) -> Optional[int]:
            future = [u for u in blocked.values() if u > t]
            return min(future) if future else None

        # Inicial: llegadas en t=0
        enqueue_arrivals(time)

        while len(done) < n:
            # Procesar desbloqueos y llegadas exactos en 'time'
            unblock_ready(time)
            enqueue_arrivals(time)

            # Elegir activo si no hay
            if active is None:
                if ready:
                    active = ready.popleft()
                    # Asegurar no iniciar antes de su llegada
                    if time < arrivals[active]:
                        time = arrivals[active]
                        # en ese t pueden haber eventos exactos
                        unblock_ready(time)
                        enqueue_arrivals(time)
                    # Cargar primer segmento si no hay ejecutando
                    if not patterns[active]:
                        completion[active] = time
                        done.add(active)
                        active = None
                        continue
                    seg_kind, seg_rem = patterns[active][0]
                    if seg_kind == "BLOCK":
                        # Registrar bloqueo y liberar CPU inmediatamente (no avanzar 'time' a end)
                        start = time
                        end = start + seg_rem
                        timeline.append(ExecSlice(f"{active}_BLOCK", start, end))
                        blocked[active] = end
                        patterns[active].pop(0)
                        active = None
                        seg_kind = None
                        seg_rem = 0
                        # loop continúa para asignar otro
                        continue
                    # seg_kind == "CPU": listo para ejecutar
                else:
                    # No hay listos: saltar a próximo evento (llegada o desbloqueo)
                    na = next_arrival_after(time)
                    nu = next_unblock_after(time)
                    if na is None and nu is None:
                        break
                    time = min([t for t in [na, nu] if t is not None])
                    continue

            # Si hay activo con CPU, ejecutar hasta el próximo evento relevante
            if active is not None and seg_kind == "CPU" and seg_rem > 0:
                # Próximo evento externo durante este tramo
                na = next_arrival_after(time)
                nu = next_unblock_after(time)
                seg_end = time + seg_rem

                # Elegimos el más cercano de (na, nu, seg_end)
                candidates = [seg_end]
                if na is not None and na > time:
                    candidates.append(na)
                if nu is not None and nu > time:
                    candidates.append(nu)
                t_next = min(candidates)

                # Ejecutar CPU desde 'time' hasta 't_next'
                if t_next > time:
                    timeline.append(ExecSlice(active, time, t_next))
                    per_proc[active].append((time, t_next))
                    run = t_next - time
                    seg_rem -= run
                    time = t_next

                # Encolar eventos exactos que ocurrieron en 'time' (fin de este paso)
                unblock_ready(time)
                enqueue_arrivals(time)

                # Si se terminó el segmento de CPU
                if seg_rem == 0:
                    # Consumir segmento
                    patterns[active].pop(0)
                    # Ver si queda más patrón o entra a BLOQUEO
                    if patterns[active]:
                        next_kind, next_dur = patterns[active][0]
                        if next_kind == "BLOCK":
                            start = time
                            end = start + next_dur
                            timeline.append(ExecSlice(f"{active}_BLOCK", start, end))
                            blocked[active] = end
                            patterns[active].pop(0)
                            active = None
                            seg_kind = None
                            seg_rem = 0
                            continue
                        else:
                            # Otro segmento de CPU: cargarlo y seguir en el mismo bucle
                            seg_kind = "CPU"
                            seg_rem = next_dur
                            # No se desaloja al activo; seguirá en el próximo ciclo cortando por eventos
                            continue
                    else:
                        # Proceso completado
                        completion[active] = time
                        done.add(active)
                        active = None
                        seg_kind = None
                        seg_rem = 0
                        continue

                # Si aún queda CPU en el mismo segmento, seguimos con el mismo activo
                # (no-preemptivo) y repetimos el ciclo para cortar nuevamente en el próximo evento.
                continue

            # Si el activo no está en CPU (caso bloqueado ya manejado arriba), liberar y continuar
            if active is not None and seg_kind == "BLOCK":
                # Ya tratado en el lugar correspondiente
                active = None
                seg_kind = None
                seg_rem = 0
                continue

        # Métricas
        for p in procs:
            pat = p.pattern if p.pattern else [("CPU", p.burst)]
            total_cpu = sum(d for k, d in pat if k == "CPU")
            total_block = sum(d for k, d in pat if k == "BLOCK")
            turnaround[p.name] = completion[p.name] - p.arrival
            waiting[p.name] = turnaround[p.name] - total_cpu - total_block

        n = max(1, len(procs))
        return ScheduleResult(
            timeline=timeline,
            per_process_slices=per_proc,
            turnaround=turnaround,
            waiting=waiting,
            avg_turnaround=sum(turnaround.values()) / n,
            avg_waiting=sum(waiting.values()) / n
        )
