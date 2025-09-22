from typing import List, Optional, Dict, Tuple
from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class SRTF(SchedulerStrategy):
    """
    Deterministic preemptive Shortest Remaining Time First (SRTF) scheduler.
    Reglas de diseño (buscadas para reproducibilidad y coincidencia con trazas
    académicas estrictas):
    - Eventos procesados en este orden en cada instante t:
      1) se liberan procesos bloqueados cuyo unblock_time <= t,
      2) se aceptan todas las llegadas con arrival <= t,
      3) se decide el siguiente proceso a ejecutar en ready (si hay).
    - La métrica de selección es el tiempo CPU total restante (suma de todos
      los tramos CPU pendientes). En caso de empate se aplica orden por llegada
      (arrival menor), luego por orden de entrada en la lista 'processes'.
    - Si un nuevo proceso llega exactamente en t y su remanente es menor que el
      remanente del activo, se preemite inmediatamente (es decir, preempción en
      el punto temporal exacto).
    - Un tramo BLOCK nunca se inicia hasta que el tramo CPU anterior haya sido
      completado. Cuando un proceso entra en BLOCK se marca su desbloqueo y no
      está en ready hasta entonces.
    - Se representan los tramos BLOCK como ExecSlice("{name}_BLOCK", start, end).
    - Se evita avanzar el reloj mientras existan listos; el reloj avanza al próximo
      evento (llegada futura o unblock) solo cuando ready está vacío.
    """

    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        if not processes:
            return ScheduleResult()

        # Normalizar patrones y construir estructuras iniciales
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)]) for p in processes
        }
        arrivals: Dict[str, int] = {p.name: p.arrival for p in processes}
        index_by_name = {p.name: i for i, p in enumerate(processes)}
        n = len(processes)

        # Estado por proceso
        next_idx: Dict[str, int] = {p.name: 0 for p in processes}    # índice dentro del patrón
        rem_cpu_seg: Dict[str, int] = {}                             # remanente del tramo CPU en curso
        blocked_until: Dict[str, int] = {}                           # proceso -> tiempo de desbloqueo
        ready: List[str] = []                                        # lista de nombres listos
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in processes}
        completion: Dict[str, int] = {}
        done = set()

        def curr_seg(name: str):
            i = next_idx[name]
            pat = patterns[name]
            return pat[i] if i < len(pat) else None

        def total_cpu_remaining(name: str) -> int:
            """Suma de todos los tramos CPU desde next_idx en adelante (incluye rem_cpu_seg)."""
            pat = patterns[name]
            idx = next_idx[name]
            rem = 0
            # si hay remanente del segmento actual, usarlo
            if name in rem_cpu_seg:
                rem += rem_cpu_seg[name]
                idx += 1  # ya contamos el tramo actual
            # sumar futuros tramos CPU
            rem += sum(d for k, d in pat[idx:] if k == "CPU")
            return rem

        def make_ready_if_cpu(name: str, now: int):
            """Pone en ready si el siguiente segmento es CPU; si es BLOCK lo registra."""
            if name in done or name in blocked_until:
                return
            seg = curr_seg(name)
            if seg is None:
                # completado
                completion[name] = now
                done.add(name)
                rem_cpu_seg.pop(name, None)
                return
            kind, dur = seg
            if kind == "BLOCK":
                # iniciar bloqueos inmediatamente (no consumen CPU) y programar desbloqueo
                if dur > 0:
                    timeline.append(ExecSlice(f"{name}_BLOCK", now, now + dur))
                blocked_until[name] = now + dur
                next_idx[name] += 1
                rem_cpu_seg.pop(name, None)
                return
            # CPU
            if name not in rem_cpu_seg:
                rem_cpu_seg[name] = dur
            if name not in ready:
                ready.append(name)

        # Inicializar tiempo en la mínima llegada
        time = min(p.arrival for p in processes)
        # Aceptar llegadas iniciales y posibles bloques que comenzaran en t=time
        for p in processes:
            if p.arrival <= time:
                make_ready_if_cpu(p.name, time)

        def process_unblocks_and_arrivals(t: int):
            # 1) desbloqueos cuyo tiempo <= t
            for name in sorted(list(blocked_until), key=lambda k: blocked_until[k]):
                if blocked_until[name] <= t:
                    unblock_time = blocked_until.pop(name)
                    make_ready_if_cpu(name, unblock_time)
            # 2) llegadas con arrival <= t que aún no empezaron (next_idx==0)
            for p in processes:
                if p.name in done or p.name in blocked_until:
                    continue
                if next_idx[p.name] == 0 and arrivals[p.name] <= t and p.name not in ready:
                    make_ready_if_cpu(p.name, t)

        def next_future_event_after(t: int) -> Optional[int]:
            events = []
            # próximas llegadas de procesos no iniciados
            for p in processes:
                if p.name in done or p.name in blocked_until:
                    continue
                if next_idx[p.name] == 0 and arrivals[p.name] > t:
                    events.append(arrivals[p.name])
            # próximos desbloqueos
            events.extend(v for v in blocked_until.values() if v > t)
            return min(events) if events else None

        # Bucle principal
        while len(done) < n:
            # Procesar desbloqueos y llegadas exactamente en 'time' (orden: unblocks then arrivals)
            process_unblocks_and_arrivals(time)

            # Si no hay listos, saltamos al siguiente evento relevante
            if not ready:
                t_next = next_future_event_after(time)
                if t_next is None:
                    # puede haber procesos que ya terminaron o estamos al final
                    break
                time = t_next
                process_unblocks_and_arrivals(time)
                continue

            # Selección determinista: ordenar ready por (total_remaining, arrival, input_order)
            ready.sort(key=lambda nm: (total_cpu_remaining(nm), arrivals[nm], index_by_name[nm]))
            active = ready.pop(0)

            # Validación: si el siguiente segmento no es CPU, tratarlo (race)
            seg = curr_seg(active)
            if seg is None:
                completion[active] = time
                done.add(active)
                rem_cpu_seg.pop(active, None)
                continue
            kind, _ = seg
            if kind != "CPU":
                # si por alguna razón el siguiente es BLOCK, procesarlo
                make_ready_if_cpu(active, time)
                continue

            # Calcular próximo evento que puede preemptar al activo:
            # - llegada futura de proceso no iniciado (arrival > time)
            # - desbloqueo futuro (blocked_until)
            seg_rem = rem_cpu_seg.get(active, 0)
            if seg_rem <= 0:
                # nada que correr (defensa)
                continue

            # Próxima llegada de procesos no iniciados
            next_arrival_times = [
                arrivals[p.name] for p in processes
                if p.name not in done and p.name not in blocked_until and next_idx[p.name] == 0 and arrivals[p.name] > time
            ]
            next_arrival = min(next_arrival_times) if next_arrival_times else None
            # Próximo desbloqueo
            next_unblock_times = [t for t in blocked_until.values() if t > time]
            next_unblock = min(next_unblock_times) if next_unblock_times else None

            seg_end = time + seg_rem
            candidates = [seg_end]
            if next_arrival is not None:
                candidates.append(next_arrival)
            if next_unblock is not None:
                candidates.append(next_unblock)
            t_next = min(candidates)

            # Ejecutar desde time hasta t_next (posible preempción en t_next)
            if t_next > time:
                timeline.append(ExecSlice(active, time, t_next))
                per_proc[active].append((time, t_next))
                run = t_next - time
                rem_cpu_seg[active] -= run
                time = t_next

            # En el instante 'time' procesamos primero desbloqueos y llegadas
            process_unblocks_and_arrivals(time)

            # Si el segmento CPU actual terminó exactamente en 'time'
            if rem_cpu_seg.get(active, 0) == 0:
                # consumir el segmento actual (avanzar índice)
                seg_now = curr_seg(active)
                if seg_now and seg_now[0] == "CPU":
                    next_idx[active] += 1
                # Ver el siguiente segmento después de consumir
                nxt = curr_seg(active)
                if nxt is None:
                    completion[active] = time
                    done.add(active)
                    rem_cpu_seg.pop(active, None)
                else:
                    if nxt[0] == "BLOCK":
                        # iniciar bloqueo inmediatamente
                        bdur = nxt[1]
                        if bdur > 0:
                            timeline.append(ExecSlice(f"{active}_BLOCK", time, time + bdur))
                        blocked_until[active] = time + bdur
                        next_idx[active] += 1
                        rem_cpu_seg.pop(active, None)
                    else:
                        # siguiente es CPU: inicializar remanente y volver a ready
                        rem_cpu_seg[active] = nxt[1]
                        if active not in ready and active not in blocked_until and active not in done:
                            ready.append(active)
            else:
                # Aún queda remanente: fue preemptado en 'time'. Reencolar respetando orden determinista.
                if active not in ready and active not in blocked_until and active not in done:
                    ready.append(active)

            # Nota: al reentrar al while se procesarán desbloqueos/arrivas en el mismo 'time' antes de decidir.

        # Cálculo de métricas finales (turnaround y waiting)
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}
        for p in processes:
            pat = patterns[p.name]
            total_cpu = sum(d for k, d in pat if k == "CPU")
            total_block = sum(d for k, d in pat if k == "BLOCK")
            fin = completion.get(p.name, time)
            tr = fin - p.arrival
            te = tr - total_cpu - total_block
            turnaround[p.name] = max(0, tr)
            waiting[p.name] = max(0, te)

        n_effective = max(1, len(processes))
        return ScheduleResult(
            timeline=timeline,
            per_process_slices=per_proc,
            turnaround=turnaround,
            waiting=waiting,
            avg_turnaround=sum(turnaround.values()) / n_effective,
            avg_waiting=sum(waiting.values()) / n_effective
        )
