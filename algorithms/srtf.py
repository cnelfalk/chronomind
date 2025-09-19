from typing import List, Optional, Dict, Tuple
from ..core.scheduler_base import SchedulerStrategy
from ..core.models import Process, ScheduleResult, ExecSlice

class SRTF(SchedulerStrategy):
    """
    Preemptive Shortest Remaining Time First (SRTF) scheduler with support for
    patterns composed of ("CPU", t) and ("BLOCK", t) segments.

    Guarantees:
    - BLOCK segments are represented as ExecSlice("{name}_BLOCK", start, end).
    - A process in BLOCK is never present in the ready set.
    - Time advances to next relevant event when nothing is ready.
    - Deterministic tie-breaks: (remaining, arrival, input order).
    """

    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        if not processes:
            return ScheduleResult()

        # Prepare structures
        patterns: Dict[str, List[Tuple[str, int]]] = {
            p.name: (p.pattern.copy() if p.pattern else [("CPU", p.burst)]) for p in processes
        }
        arrivals: Dict[str, int] = {p.name: p.arrival for p in processes}
        index_by_name = {p.name: i for i, p in enumerate(processes)}
        n = len(processes)

        next_idx: Dict[str, int] = {p.name: 0 for p in processes}    # index into pattern
        rem_cpu: Dict[str, int] = {}                                 # remaining for current CPU segment
        blocked_until: Dict[str, int] = {}                           # process -> unlock time
        ready: List[str] = []                                        # names of ready processes
        timeline: List[ExecSlice] = []
        per_proc: Dict[str, List[Tuple[int, int]]] = {p.name: [] for p in processes}
        completion: Dict[str, int] = {}
        done = set()

        def curr_seg(name: str):
            i = next_idx[name]
            pat = patterns[name]
            return pat[i] if i < len(pat) else None

        def make_ready(name: str, t: int):
            """Put process into ready if it has a CPU segment; otherwise register block or completion."""
            if name in done or name in blocked_until:
                return
            seg = curr_seg(name)
            if seg is None:
                completion[name] = t
                done.add(name)
                rem_cpu.pop(name, None)
                return
            kind, dur = seg
            if kind == "BLOCK":
                # register block slice and advance
                if dur > 0:
                    timeline.append(ExecSlice(f"{name}_BLOCK", t, t + dur))
                blocked_until[name] = t + dur
                next_idx[name] += 1
                rem_cpu.pop(name, None)
                return
            # CPU
            if name not in rem_cpu:
                rem_cpu[name] = dur
            if name not in ready:
                ready.append(name)

        # Initialize time at earliest arrival
        time = min(p.arrival for p in processes)
        # Add initial arrivals (<= time)
        for p in processes:
            if p.arrival <= time:
                make_ready(p.name, time)

        # Helper to advance and process unblocks/arrivals at that time
        def flush_events_at(t: int):
            # unblocks
            for name in sorted(list(blocked_until), key=lambda k: blocked_until[k]):
                if blocked_until[name] <= t:
                    blocked_until.pop(name, None)
                    make_ready(name, blocked_until.get(name, t))
            # arrivals
            for p in processes:
                if p.name in done or p.name in blocked_until:
                    continue
                if next_idx[p.name] == 0 and arrivals[p.name] <= t and p.name not in ready:
                    make_ready(p.name, t)

        def cpu_remaining_total(name: str) -> int:
            """Suma de CPU restante desde next_idx en adelante (incluye todos los tramos CPU futuros)."""
            pat = patterns[name]
            idx = next_idx[name]
            return sum(d for k, d in pat[idx:] if k == "CPU")

        while len(done) < n:
            # Unblock and process arrivals at current time
            flush_events_at(time)

            # If nothing ready, jump to next event (arrival or unblock)
            if not ready:
                future = []
                # future arrivals for processes not yet started
                for p in processes:
                    if p.name in done or p.name in blocked_until:
                        continue
                    if next_idx[p.name] == 0 and arrivals[p.name] > time:
                        future.append(arrivals[p.name])
                # future unblocks
                future.extend(t for t in blocked_until.values() if t > time)
                if not future:
                    break
                time = min(future)
                flush_events_at(time)
                continue

            # Choose process with least total remaining CPU (deterministic tie-break)
            def key(nm: str):
                return (cpu_remaining_total(nm), arrivals[nm], index_by_name[nm])
            ready.sort(key=key)
            active = ready.pop(0)

            # Defensive: verify active still has a CPU segment
            seg = curr_seg(active)
            if seg is None:
                completion[active] = time
                done.add(active)
                rem_cpu.pop(active, None)
                continue
            kind, _ = seg
            if kind != "CPU":
                # If next is BLOCK (race), handle it and continue loop
                make_ready(active, time)
                continue

            # Determine next possible preemption event
            seg_remaining = rem_cpu.get(active, 0)
            if seg_remaining <= 0:
                # defensive: nothing to run
                continue

            # Next arrival of a not-yet-started process
            next_arrival = min(
                (arrivals[p.name] for p in processes
                 if p.name not in done and p.name not in blocked_until and next_idx[p.name] == 0 and arrivals[p.name] > time),
                default=None
            )
            # Next unblock time
            next_unblock = min((t for t in blocked_until.values() if t > time), default=None)
            seg_end = time + seg_remaining

            candidates = [seg_end]
            if next_arrival is not None:
                candidates.append(next_arrival)
            if next_unblock is not None:
                candidates.append(next_unblock)
            t_next = min(candidates)

            # Append execution slice [time, t_next)
            if t_next > time:
                timeline.append(ExecSlice(active, time, t_next))
                per_proc[active].append((time, t_next))
                run = t_next - time
                rem_cpu[active] -= run
                time = t_next

            # Process events at the new time
            flush_events_at(time)

            # If current CPU segment finished, consume it and react
            if rem_cpu.get(active, 0) == 0:
                # consume CPU segment
                seg_now = curr_seg(active)
                if seg_now and seg_now[0] == "CPU":
                    next_idx[active] += 1
                nxt = curr_seg(active)
                if nxt is None:
                    completion[active] = time
                    done.add(active)
                    rem_cpu.pop(active, None)
                else:
                    if nxt[0] == "BLOCK":
                        bdur = nxt[1]
                        if bdur > 0:
                            timeline.append(ExecSlice(f"{active}_BLOCK", time, time + bdur))
                        blocked_until[active] = time + bdur
                        next_idx[active] += 1
                        rem_cpu.pop(active, None)
                    else:
                        # next is CPU: initialize its remaining and requeue
                        rem_cpu[active] = nxt[1]
                        if active not in ready and active not in blocked_until and active not in done:
                            ready.append(active)
            else:
                # still has remaining on current CPU segment -> preempted by event
                if active not in ready and active not in blocked_until and active not in done:
                    ready.append(active)

        # Compute metrics
        turnaround: Dict[str, int] = {}
        waiting: Dict[str, int] = {}
        for p in processes:
            orig_pat = p.pattern if p.pattern else patterns[p.name]
            total_cpu = sum(d for k, d in (orig_pat or []) if k == "CPU")
            total_block = sum(d for k, d in (orig_pat or []) if k == "BLOCK")
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
