from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Process, ScheduleResult

class SchedulerStrategy(ABC):
    @abstractmethod
    def schedule(self, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
        ...
