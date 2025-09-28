from typing import List, Optional, Dict, Tuple
import heapq

from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class SJF(SchedulerStrategy):
    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        # Orden original y cantidad
        procs = processes
        n = len(procs)

        # Reloj, resultados y métricas
        time = 0
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in procs}
        completion: Dict[str, int] = {}
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}

        # Patrón (CPU/BLOCK) y siguientes índices
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)])
            for p in procs
        }
        next_index: Dict[str, int] = {p.name: 0 for p in procs}
        arrivals: Dict[str, int] = {p.name: p.arrival for p in procs}

        # 1) Calcular CPU total fijo por proceso (criterio puro SJF)
        total_cpu: Dict[str, int] = {
            p.name: sum(d for k, d in patterns[p.name] if k == "CPU")
            for p in procs
        }

        # 2) Ready como min-heap de (total_cpu, arrival, name)
        ready_heap: List[Tuple[int, int, str]] = []
        ready_set = set()       # Para evitar duplicados
        blocked: Dict[str, int] = {}  # nombre -> tiempo de desbloqueo
        done = set()                 # procesos completos
        last_end: Dict[str, int] = {p.name: p.arrival for p in procs}

        def enqueue_arrivals(t: int):
            for p in procs:
                name = p.name
                if name in done or name in blocked or name in ready_set:
                    continue
                if next_index[name] == 0 and arrivals[name] <= t:
                    heapq.heappush(ready_heap, (total_cpu[name], arrivals[name], name))
                    ready_set.add(name)

        def unblock_at(t: int):
            to_unblock = [name for name, unb in blocked.items() if unb <= t]
            for name in to_unblock:
                blocked.pop(name)
                if name in done or name in ready_set:
                    continue
                heapq.heappush(ready_heap, (total_cpu[name], arrivals[name], name))
                ready_set.add(name)

        # Primeros arribos en t=0
        enqueue_arrivals(time)

        while len(done) < n:
            unblock_at(time)
            enqueue_arrivals(time)

            if not ready_heap:
                # Saltar al próximo evento (llegada o desbloqueo)
                future_arr = [
                    arrivals[p.name]
                    for p in procs
                    if next_index[p.name] == 0 and p.name not in done and arrivals[p.name] > time
                ]
                future_unb = [u for u in blocked.values() if u > time]
                future = future_arr + future_unb
                if not future:
                    break
                time = min(future)
                continue

            # Selección no-preemptiva por CPU total inmutable
            _, _, selected = heapq.heappop(ready_heap)
            ready_set.remove(selected)

            idx = next_index[selected]
            # Si ya acabó todos sus tramos:
            if idx >= len(patterns[selected]):
                completion[selected] = last_end[selected]
                done.add(selected)
                continue

            kind, dur = patterns[selected][idx]

            if kind == "BLOCK":
                start, end = time, time + dur
                if dur > 0:
                    timeline.append(ExecSlice(f"{selected}_BLOCK", start, end))
                last_end[selected] = max(last_end[selected], end)
                blocked[selected] = end
                next_index[selected] += 1

                if next_index[selected] >= len(patterns[selected]):
                    completion[selected] = last_end[selected]
                    done.add(selected)
                # El reloj no avanza aquí
                continue

            # Ejecutar tramo CPU completo
            start, end = time, time + dur
            timeline.append(ExecSlice(selected, start, end))
            per_proc[selected].append((start, end))
            last_end[selected] = max(last_end[selected], end)
            time = end
            next_index[selected] += 1

            # Tras CPU, chequear siguiente tramo inmediato
            if next_index[selected] < len(patterns[selected]):
                nk, nd = patterns[selected][next_index[selected]]
                if nk == "BLOCK":
                    bstart, bend = time, time + nd
                    if nd > 0:
                        timeline.append(ExecSlice(f"{selected}_BLOCK", bstart, bend))
                    last_end[selected] = max(last_end[selected], bend)
                    blocked[selected] = bend
                    next_index[selected] += 1
                    if next_index[selected] >= len(patterns[selected]):
                        completion[selected] = last_end[selected]
                        done.add(selected)
                else:
                    # Sigue CPU: volver a entrar a ready con misma prioridad
                    heapq.heappush(ready_heap, (total_cpu[selected], arrivals[selected], selected))
                    ready_set.add(selected)
            else:
                # Patrón completo
                completion[selected] = last_end[selected]
                done.add(selected)

        # Cálculo final de turnaround y waiting
        for p in procs:
            pat = patterns[p.name]
            cpu_sum = sum(d for k, d in pat if k == "CPU")
            block_sum = sum(d for k, d in pat if k == "BLOCK")
            fin = completion.get(p.name, last_end[p.name])
            tr = fin - p.arrival
            wt = tr - cpu_sum - block_sum
            turnaround[p.name] = max(0, tr)
            waiting[p.name] = max(0, wt)

        # Resultado
        return ScheduleResult(
            timeline=timeline,
            per_process_slices=per_proc,
            turnaround=turnaround,
            waiting=waiting,
            avg_turnaround=sum(turnaround.values()) / max(1, n),
            avg_waiting=sum(waiting.values()) / max(1, n)
        )
