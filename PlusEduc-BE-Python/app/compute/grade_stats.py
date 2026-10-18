from __future__ import annotations

import logging
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.compute.opencl_runtime import NO_STAMP, OpenCLRuntime

logger = logging.getLogger(__name__)

EPOCH = datetime(1970, 1, 1)
ONE_MICROSECOND = timedelta(microseconds=1)


@dataclass(frozen=True, slots=True)
class GroupStats:
    count: int = 0
    total: float = 0.0
    recorded: int = 0  # lançamentos em que a presença foi registrada
    attended: int = 0
    last: datetime | None = None  # UTC sem fuso

    @property
    def average(self) -> float:
        return self.total / self.count if self.count else 0.0

    @property
    def absences(self) -> int:
        return self.recorded - self.attended

    @property
    def attendance_rate(self) -> int:
        return int(self.attended * 100 / self.recorded) if self.recorded else 0

    @classmethod
    def combine(cls, items: Iterable[GroupStats]) -> GroupStats:
        items = list(items)
        stamps = [item.last for item in items if item.last is not None]
        return cls(
            count=sum(item.count for item in items),
            total=sum(item.total for item in items),
            recorded=sum(item.recorded for item in items),
            attended=sum(item.attended for item in items),
            last=max(stamps) if stamps else None,
        )


class _State:
    enabled = False
    min_records = 0
    runtime = OpenCLRuntime()


def configure(settings: Any) -> None:
    """Liga/desliga o OpenCL conforme as configurações e compila o kernel já na subida da API."""
    _State.enabled = bool(getattr(settings, "opencl_enabled", False))
    _State.min_records = int(getattr(settings, "opencl_min_records", 0))
    if _State.enabled:
        _State.runtime.initialize(getattr(settings, "opencl_device", ""))


def status() -> dict[str, Any]:
    runtime = _State.runtime
    return {
        "enabled": _State.enabled,
        "active": _State.enabled and runtime.ready,
        "device": runtime.device_name,
        "minRecords": _State.min_records,
        "kernelCalls": runtime.kernel_calls,
        "error": runtime.error if _State.enabled and not runtime.ready else None,
    }


def grade_value(document: dict[str, Any]) -> float:
    return float(document.get("grade", document.get("gradeValue")) or 0)


def stats_by(
    documents: Sequence[dict[str, Any]],
    key: Callable[[dict[str, Any]], Hashable],
    stamp: Callable[[dict[str, Any]], datetime | None] | None = None,
) -> dict[Hashable, GroupStats]:
    """Agrupa lançamentos de nota por ``key`` e calcula contagem, soma, presença e última data.

    Usa o kernel OpenCL quando está ativo e há registros suficientes; qualquer falha na GPU cai no
    caminho em Python, que produz o mesmo resultado (a soma pode diferir só na última casa decimal).
    """
    keys = [key(document) for document in documents]
    values = [grade_value(document) for document in documents]
    # Só `True` conta como presença; a ausência do campo (nota de atividade online) não vira aula.
    flags = [-1 if document.get("attendance") is None else int(document["attendance"] is True) for document in documents]
    stamps = [stamp(document) if stamp else None for document in documents]
    if _State.enabled and _State.runtime.ready and len(documents) >= max(_State.min_records, 1):
        try:
            return _stats_opencl(keys, values, flags, stamps)
        except Exception:  # noqa: BLE001 - a GPU nunca pode impedir a resposta
            logger.exception("Falha no kernel OpenCL; usando o caminho em Python")
    return _stats_python(keys, values, flags, stamps)


def _stats_python(keys, values, flags, stamps) -> dict[Hashable, GroupStats]:
    grouped: dict[Hashable, list[int]] = {}
    for index, key in enumerate(keys):
        grouped.setdefault(key, []).append(index)
    result = {}
    for key, indexes in grouped.items():
        recorded = [flags[i] for i in indexes if flags[i] >= 0]
        dates = [stamps[i] for i in indexes if stamps[i] is not None]
        result[key] = GroupStats(
            count=len(indexes),
            total=sum(values[i] for i in indexes),
            recorded=len(recorded),
            attended=sum(recorded),
            last=max(dates) if dates else None,
        )
    return result


def _stats_opencl(keys, values, flags, stamps) -> dict[Hashable, GroupStats]:
    import numpy as np

    ids: dict[Hashable, int] = {}
    group = np.fromiter((ids.setdefault(key, len(ids)) for key in keys), np.int32, count=len(keys))
    order = np.argsort(group, kind="stable")  # estável: mantém a ordem original dentro de cada grupo
    offsets = np.zeros(len(ids) + 1, np.int32)
    np.cumsum(np.bincount(group, minlength=len(ids)), out=offsets[1:])
    micros = np.fromiter(
        (NO_STAMP if moment is None else (moment - EPOCH) // ONE_MICROSECOND for moment in stamps), np.int64, count=len(stamps)
    )
    sums, counts, recorded, attended, last = _State.runtime.grade_stats(
        np.asarray(values, np.float64)[order], np.asarray(flags, np.int8)[order], micros[order], offsets
    )
    return {
        key: GroupStats(
            count=int(counts[index]),
            total=float(sums[index]),
            recorded=int(recorded[index]),
            attended=int(attended[index]),
            last=None if last[index] == NO_STAMP else EPOCH + int(last[index]) * ONE_MICROSECOND,
        )
        for key, index in ids.items()
    }
