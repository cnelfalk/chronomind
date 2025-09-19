from typing import List, Optional, Dict, Tuple
from collections import deque
from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class RoundRobin(SchedulerStrategy):
    """
    Round Robin que garantiza: un BLOCK solo comienza tras la completa consumición
    del tramo CPU previo. Quantum define cuánto se ejecuta por paso; si no se completa
    el tramo CPU, el proceso se reencola y NO se inicia el BLOCK.
    """

    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        if quantum is None or quantum <= 0:
            raise ValueError("Quantum inválido para Round Robin.")

        if not processes:
            return ScheduleResult()

        # Orden determinista por llegada
        procs = sorted(processes, key=lambda p: p.arrival)
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)]) for p in procs
        }
        arrivals: Dict[str, int] = {p.name: p.arrival for p in procs}
        n = len(procs)

        # Estado
        time = min(p.arrival for p in procs)
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in procs}
        completion: Dict[str, int] = {}
        blocked: Dict[str, int] = {}   # proceso -> tiempo de desbloqueo
        ready = deque()
        idx = 0                        # puntero para llegadas
        done = set()

        # Remanente del tramo CPU actual por proceso (si existe)
        rem_cpu: Dict[str, int] = {}

        def enqueue_arrivals(upto: int):
            nonlocal idx
            while idx < len(procs) and procs[idx].arrival <= upto:
                name = procs[idx].name
                if name not in ready and name not in blocked and name not in done:
                    ready.append(name)
                idx += 1

        # Inicial: enqueue de llegadas en 'time'
        enqueue_arrivals(time)

        while len(done) < n:
            # Procesar desbloqueos que terminaron en o antes de 'time'
            for name in sorted(list(blocked)):
                if blocked[name] <= time:
                    blocked.pop(name)
                    if name not in ready and name not in done:
                        ready.append(name)

            # Aceptar llegadas en 'time'
            enqueue_arrivals(time)

            if not ready:
                # Saltar al siguiente evento real (llegada futura o fin de bloqueo)
                future = []
                future.extend(t for t in blocked.values() if t > time)
                future.extend(p.arrival for p in procs if p.name not in done and p.name not in blocked and p.arrival > time)
                if not future:
                    break
                time = min(future)
                # loop volverá a procesar desbloqueos/llegadas en la cima
                continue

            current = ready.popleft()

            # Defensa: si cambió su estado mientras tanto, saltarlo
            if current in blocked or current in done:
                continue

            pattern = patterns.get(current, [])

            # Si no hay patrón: terminar
            if not pattern:
                completion[current] = time
                done.add(current)
                rem_cpu.pop(current, None)
                continue

            # Asegurar rem_cpu para el tramo CPU actual si corresponde
            kind, duration = pattern[0]

            # Si el primer segmento es BLOCK (caso raro si la entrada lo define así),
            # no lo arrancamos a menos que llegue el momento de comenzar bloqueos.
            if kind == "BLOCK":
                # Esto solo puede ocurrir si la definición empieza por BLOCK; respetamos y lo ejecutamos
                if duration > 0:
                    timeline.append(ExecSlice(f"{current}_BLOCK", time, time + duration))
                blocked[current] = time + duration
                # consumir ese segmento del patrón
                pattern.pop(0)
                rem_cpu.pop(current, None)
                # NO avanzar 'time' aquí: permitimos que otros ready usen CPU en el mismo instante
                continue

            # kind == "CPU": inicializar rem_cpu si no existe
            if current not in rem_cpu:
                rem_cpu[current] = duration

            # Ejecutar min(quantum, rem_cpu)
            run = min(quantum, rem_cpu[current])
            start = time
            end = start + run
            timeline.append(ExecSlice(current, start, end))
            per_proc[current].append((start, end))
            rem_cpu[current] -= run
            time = end

            # Tras ejecutar, procesar llegadas y desbloqueos que ocurrieron hasta 'time'
            enqueue_arrivals(time)
            # desbloqueos que finalizan <= time
            for name in list(blocked):
                if blocked[name] <= time:
                    blocked.pop(name)
                    if name not in ready and name not in done and name != current:
                        ready.append(name)

            # Si remanente del tramo CPU quedó > 0: tramo no terminado -> reencolar, NO iniciar BLOCK
            if rem_cpu[current] > 0:
                if current not in ready and current not in blocked and current not in done:
                    ready.append(current)
                continue

            # Si rem_cpu == 0: terminamos ese segmento CPU -> avanzamos el patrón
            pattern.pop(0)
            rem_cpu.pop(current, None)

            # Ahora mirar siguiente segmento del patrón: si es BLOCK, iniciarlo inmediatamente
            if pattern:
                next_kind, next_dur = pattern[0]
                if next_kind == "BLOCK":
                    # Registrar bloque iniciando en 'time' y marcar desbloqueo
                    if next_dur > 0:
                        timeline.append(ExecSlice(f"{current}_BLOCK", time, time + next_dur))
                    blocked[current] = time + next_dur
                    # consumir el segmento BLOCK del patrón
                    pattern.pop(0)
                    # No reencolar ahora; volverá a ready cuando se desbloquee
                    # Si el proceso quedó sin más segmentos después del BLOCK, lo marcaríamos completado en su desbloqueo
                    # (se completará cuando blocked se procese y make it ready, then pattern empty => completion).
                    continue
                else:
                    # Siguiente también es CPU: inicializar su remanente y reencolar
                    rem_cpu[current] = next_dur
                    if current not in ready and current not in blocked and current not in done:
                        ready.append(current)
                    continue
            else:
                # No quedan segmentos -> proceso completado ahora
                completion[current] = time
                done.add(current)
                continue

        # Métricas
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}
        for p in procs:
            orig_pat = p.pattern if p.pattern else patterns.get(p.name, [("CPU", p.burst)])
            total_cpu = sum(d for k, d in (orig_pat or []) if k == "CPU")
            total_block = sum(d for k, d in (orig_pat or []) if k == "BLOCK")
            fin = completion.get(p.name, time)
            tr = fin - p.arrival
            te = tr - total_cpu - total_block
            turnaround[p.name] = max(0, tr)
            waiting[p.name] = max(0, te)

        n_effective = max(1, len(procs))
        return ScheduleResult(
            timeline=timeline,
            per_process_slices=per_proc,
            turnaround=turnaround,
            waiting=waiting,
            avg_turnaround=sum(turnaround.values()) / n_effective,
            avg_waiting=sum(waiting.values()) / n_effective
        )
