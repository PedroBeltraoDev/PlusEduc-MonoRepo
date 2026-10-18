from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# Pool próprio e limitado para consultas de I/O: nunca é o mesmo pool que atende as rotas,
# então uma rota esperando aqui não consome a thread de que as próprias tarefas precisam.
_EXECUTOR = ThreadPoolExecutor(max_workers=16, thread_name_prefix="pluseduc-io")


def run_parallel(*tasks: Callable[[], Any]) -> list[Any]:
    """Executa tarefas independentes de I/O ao mesmo tempo e devolve os resultados na ordem recebida.

    As tarefas não podem chamar ``run_parallel`` (evita esgotar o pool). A primeira roda na thread
    atual; o tempo total passa a ser o da mais lenta, não a soma. Uma exceção é propagada ao chamador.
    """
    if not tasks:
        return []
    futures = [_EXECUTOR.submit(task) for task in tasks[1:]]
    first = tasks[0]()
    return [first, *(future.result() for future in futures)]
