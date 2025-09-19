from typing import Dict, Type, Optional
from .scheduler_base import SchedulerStrategy
from ..algorithms.fifo import FIFO
from ..algorithms.sjf import SJF
from ..algorithms.srtf import SRTF
from ..algorithms.round_robin import RoundRobin

class SchedulerFactory:
    _strategies: Dict[str, Type[SchedulerStrategy]] = {
        "FIFO": FIFO,
        "SJF": SJF,
        "SRTF": SRTF,
        "Round Robin": RoundRobin,
    }

    @classmethod
    def create(cls, name: str) -> Optional[SchedulerStrategy]:
        strategy_cls = cls._strategies.get(name)
        return strategy_cls() if strategy_cls else None

    @classmethod
    def list_algorithms(cls):
        return list(cls._strategies.keys())
