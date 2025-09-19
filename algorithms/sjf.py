from typing import List, Optional, Dict, Tuple
from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class SJF(SchedulerStrategy):
    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        # Mantener orden original de entrada
        procs = processes
        n = len(procs)

        time = 0
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in procs}
        completion: Dict[str, int] = {}
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}

        # Estado por proceso
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)]) for p in procs
        }
        # Índice del siguiente segmento a ejecutar por proceso
        next_index: Dict[str, int] = {p.name: 0 for p in procs}
        arrivals: Dict[str, int] = {p.name: p.arrival for p in procs}

        # Cola de listos (por disponibilidad real); se selecciona siempre el de menor CPU restante total
        ready: List[str] = []

        # Bloqueados: nombre -> tiempo de desbloqueo
        blocked: Dict[str, int] = {}

        # Fin absoluto del último tramo (CPU o BLOCK) por proceso
        # Se usa para inferir completion si no se fijó explícitamente
        last_end_by_proc: Dict[str, int] = {p.name: p.arrival for p in procs}

        # Conjunto de procesos ya finalizados
        done = set()

        def cpu_remaining_total(name: str) -> int:
            """Suma de CPU restante desde next_index en adelante."""
            pat = patterns[name]
            idx = next_index[name]
            return sum(d for k, d in pat[idx:] if k == "CPU")

        def enqueue_arrivals_at(t: int):
            """Agregar a listos todos los procesos cuyo arrival <= t y que aún no hayan empezado."""
            for p in procs:
                if p.name in done:
                    continue
                if p.name in blocked:
                    continue
                # Si nunca entró a la cola (no ha arrancado aún) y ya llegó:
                if next_index[p.name] == 0 and arrivals[p.name] <= t and p.name not in ready:
                    ready.append(p.name)

        def unblock_at(t: int):
            """Mover a listos todo lo que terminó bloqueo en o antes de t."""
            for name in sorted(list(blocked), key=lambda k: blocked[k]):
                if blocked[name] <= t:
                    blocked.pop(name, None)
                    if name not in ready and name not in done:
                        ready.append(name)

        def next_future_event_after(t: int) -> Optional[int]:
            """Próximo evento futuro: llegada futura o fin de bloqueo futuro."""
            future_arrivals = [
                arrivals[p.name]
                for p in procs
                if next_index[p.name] == 0 and arrivals[p.name] > t and p.name not in done
            ]
            future_unblocks = [u for u in blocked.values() if u > t]
            future = future_arrivals + future_unblocks
            return min(future) if future else None

        # Inicial: llegadas en t=0
        enqueue_arrivals_at(time)

        while len(done) < n:
            # Procesar eventos exactos en 'time'
            unblock_at(time)
            enqueue_arrivals_at(time)

            # Si no hay listos, saltar a próximo evento
            if not ready:
                t_next = next_future_event_after(time)
                if t_next is None:
                    # No quedan eventos; corte defensivo
                    break
                time = t_next
                continue

            # Elegir el proceso con menor CPU restante total
            selected = min(ready, key=cpu_remaining_total)
            ready.remove(selected)

            # Si ya no quedan segmentos, cerrar métricas y continuar
            if next_index[selected] >= len(patterns[selected]):
                # Ya completó; usar el último fin conocido
                completion[selected] = last_end_by_proc[selected]
                done.add(selected)
                continue

            kind, duration = patterns[selected][next_index[selected]]

            # Si el siguiente segmento es BLOCK: registrar el bloqueo y ceder CPU sin avanzar 'time'
            if kind == "BLOCK":
                # Duraciones 0 generan barras de duración 0; evitarlas en timeline pero avanzar estado
                start = time
                end = start + duration
                if duration > 0:
                    timeline.append(ExecSlice(f"{selected}_BLOCK", start, end))
                last_end_by_proc[selected] = max(last_end_by_proc[selected], end)
                blocked[selected] = end
                next_index[selected] += 1

                # Si consumió todo el patrón, fijar completion al final del último tramo
                if next_index[selected] >= len(patterns[selected]):
                    completion[selected] = last_end_by_proc[selected]
                    done.add(selected)

                # No avanzamos el reloj aquí; el bucle saltará al próximo evento si no hay listos
                continue

            # Si es CPU: ejecutar el CPU completo (SJF no-preemptivo por tramo)
            if kind == "CPU":
                start = time
                end = start + duration
                timeline.append(ExecSlice(selected, start, end))
                per_proc[selected].append((start, end))
                last_end_by_proc[selected] = max(last_end_by_proc[selected], end)
                time = end
                next_index[selected] += 1

                # Si terminó su patrón completo, cerrar
                if next_index[selected] >= len(patterns[selected]):
                    completion[selected] = last_end_by_proc[selected]
                    done.add(selected)
                else:
                    # Mirar el siguiente segmento: si es BLOCK, registrarlo ahora (en el mismo 'time')
                    nkind, ndur = patterns[selected][next_index[selected]]
                    if nkind == "BLOCK":
                        bstart = time
                        bend = bstart + ndur
                        if ndur > 0:
                            timeline.append(ExecSlice(f"{selected}_BLOCK", bstart, bend))
                        last_end_by_proc[selected] = max(last_end_by_proc[selected], bend)
                        blocked[selected] = bend
                        next_index[selected] += 1
                        if next_index[selected] >= len(patterns[selected]):
                            completion[selected] = last_end_by_proc[selected]
                            done.add(selected)
                    else:
                        # Siguiente también es CPU: volver a competir por CPU según SJF
                        if selected not in ready and selected not in blocked and selected not in done:
                            ready.append(selected)

                # Tras ejecutar CPU, procesar eventos exactos en el 'time' actual
                unblock_at(time)
                enqueue_arrivals_at(time)

                # Si no hay listos, saltar a próximo evento (llegada o fin de bloqueo)
                if not ready:
                    t_next = next_future_event_after(time)
                    if t_next is None:
                        break
                    time = t_next

                continue

        # Métricas finales robustas
        for p in procs:
            pat = patterns[p.name]
            total_cpu = sum(d for k, d in pat if k == "CPU")
            total_block = sum(d for k, d in pat if k == "BLOCK")
            fin_real = completion.get(p.name, last_end_by_proc[p.name])
            tr = fin_real - p.arrival
            te = tr - total_cpu - total_block
            # Protección final contra negativos si algún proceso quedó sin registrar
            turnaround[p.name] = max(0, tr)
            waiting[p.name] = max(0, te)

        n = max(1, len(procs))
        return ScheduleResult(
            timeline=timeline,
            per_process_slices=per_proc,
            turnaround=turnaround,
            waiting=waiting,
            avg_turnaround=sum(turnaround.values()) / n,
            avg_waiting=sum(waiting.values()) / n
        )
