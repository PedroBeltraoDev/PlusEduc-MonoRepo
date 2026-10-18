from __future__ import annotations

import logging
import threading
from pathlib import Path

try:  # opcionais: sem eles a aplicação segue funcionando pelo caminho em Python
    import numpy as np
    import pyopencl as cl
except ImportError:  # pragma: no cover - depende do ambiente
    np = cl = None

logger = logging.getLogger(__name__)

KERNEL_FILE = Path(__file__).with_name("grade_stats.cl")
MAX_LOCAL_SIZE = 128
NO_STAMP = -(2**63)  # LONG_MIN do kernel


class OpenCLRuntime:
    """Escolhe o dispositivo, compila o kernel uma vez e serializa o uso da fila de comandos.

    As rotas rodam em várias threads; o contexto é compartilhado e cada execução do kernel acontece
    sob um lock (a fila e o objeto ``cl.Kernel`` não são thread-safe).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._context = None
        self._queue = None
        self._kernel = None
        self._local_size = 0
        self.device_name: str | None = None
        self.error: str | None = None
        self.kernel_calls = 0

    @property
    def ready(self) -> bool:
        return self._kernel is not None

    def initialize(self, device_hint: str = "") -> bool:
        """Prepara o primeiro dispositivo com fp64 (GPU de preferência). Nunca levanta exceção."""
        if self.ready:
            return True
        if cl is None:
            self.error = "pyopencl/numpy não instalados"
            return False
        try:
            device = self._pick_device(device_hint)
            if device is None:
                self.error = "nenhum dispositivo OpenCL com suporte a fp64"
                return False
            self._context = cl.Context([device])
            self._queue = cl.CommandQueue(self._context)  # criar a fila custa ~18 ms: uma só, reutilizada
            program = cl.Program(self._context, KERNEL_FILE.read_text(encoding="utf-8")).build()
            self._kernel = cl.Kernel(program, "grade_stats")
            size = 1
            while size * 2 <= min(MAX_LOCAL_SIZE, device.max_work_group_size):
                size *= 2
            self._local_size = size
            self.device_name = device.name.strip()
            self.error = None
            logger.info("OpenCL pronto em '%s' (work-group %d)", self.device_name, size)
            return True
        except Exception as exc:  # noqa: BLE001 - driver ausente ou falha de compilação não pode derrubar a API
            self._kernel = None
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("OpenCL indisponível, usando o caminho em Python: %s", self.error)
            return False

    @staticmethod
    def _pick_device(hint: str):
        candidates = [
            device
            for platform in cl.get_platforms()
            for device in platform.get_devices()
            if device.double_fp_config and hint.lower() in device.name.lower()
        ]
        candidates.sort(key=lambda device: not (device.type & cl.device_type.GPU))
        return candidates[0] if candidates else None

    def grade_stats(self, values, attendance, stamps, offsets):
        """Executa o kernel e devolve (soma, contagem, registradas, presentes, última data) por grupo."""
        groups = len(offsets) - 1
        flags = cl.mem_flags
        outputs = (
            np.empty(groups, np.float64), np.empty(groups, np.int32), np.empty(groups, np.int32),
            np.empty(groups, np.int32), np.empty(groups, np.int64),
        )
        with self._lock:
            context, queue, size = self._context, self._queue, self._local_size
            inputs = [
                cl.Buffer(context, flags.READ_ONLY | flags.COPY_HOST_PTR, hostbuf=array)
                for array in (values, attendance, stamps, offsets)
            ]
            result_buffers = [cl.Buffer(context, flags.WRITE_ONLY, array.nbytes) for array in outputs]
            self._kernel.set_args(
                *inputs, *result_buffers,
                cl.LocalMemory(size * 8), cl.LocalMemory(size * 4), cl.LocalMemory(size * 4), cl.LocalMemory(size * 8),
            )
            cl.enqueue_nd_range_kernel(queue, self._kernel, (groups * size,), (size,))
            for array, buffer in zip(outputs, result_buffers):
                cl.enqueue_copy(queue, array, buffer)
            queue.finish()
            self.kernel_calls += 1
        return outputs
