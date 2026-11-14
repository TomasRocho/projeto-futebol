"""Sorteio de times equilibrado pela soma dos ratings (função pura, sem banco).

1. Embaralha os presentes. Se tem mais gente do que cabe (numero_times x jogadores_por_time),
   os que sobram viram avulsos (aleatórios).
2. Tamanhos dos times diferem em no máximo 1 (pouca gente = times incompletos por igual).
3. Várias tentativas: divide aleatoriamente e melhora trocando pares entre times enquanto
   a diferença de soma diminuir. Fica a tentativa com menor diferença entre o time mais
   forte e o mais fraco. Para cedo se achar o equilíbrio perfeito; como cada tentativa
   começa de uma divisão aleatória, refazer o sorteio dá times diferentes.
"""

import random
from dataclasses import dataclass

Jogador = tuple[int, int]  # (jogador_id, rating)


@dataclass
class ResultadoSorteio:
    times: list[list[int]]  # ids por time
    avulsos: list[int]


def tamanhos(n_presentes: int, n_times: int, por_time: int) -> list[int]:
    jogam = min(n_presentes, n_times * por_time)
    base, resto = divmod(jogam, n_times)
    return [base + 1 if i < resto else base for i in range(n_times)]


def sortear_times(
    jogadores: list[Jogador],
    n_times: int,
    por_time: int,
    rng: random.Random,
    tentativas: int = 200,
) -> ResultadoSorteio:
    pool = list(jogadores)
    rng.shuffle(pool)
    sizes = tamanhos(len(pool), n_times, por_time)
    jogam, avulsos = pool[: sum(sizes)], pool[sum(sizes) :]

    total = sum(r for _, r in jogam)
    ideal = 0 if total % n_times == 0 else 1  # menor diferença possível

    melhor: list[list[Jogador]] = []
    melhor_dif = float("inf")
    for _ in range(tentativas):
        rng.shuffle(jogam)
        times = _dividir(jogam, sizes)
        _equilibrar(times)
        dif = diferenca(times)
        if dif < melhor_dif:
            melhor, melhor_dif = times, dif
        if melhor_dif <= ideal:
            break

    return ResultadoSorteio(
        times=[[jid for jid, _ in t] for t in melhor],
        avulsos=[jid for jid, _ in avulsos],
    )


def diferenca(times: list[list[Jogador]]) -> int:
    """Soma do time mais forte menos a do mais fraco."""
    somas = [sum(r for _, r in t) for t in times]
    return max(somas) - min(somas)


def _dividir(jogadores: list[Jogador], sizes: list[int]) -> list[list[Jogador]]:
    times, i = [], 0
    for n in sizes:
        times.append(jogadores[i : i + n])
        i += n
    return times


def _equilibrar(times: list[list[Jogador]]) -> None:
    """Troca pares entre dois times sempre que isso aproxima as somas dos dois.

    Cada troca reduz a soma dos quadrados das somas (que é inteira), então o laço termina.
    """
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                ti, tj = times[i], times[j]
                dif = sum(r for _, r in ti) - sum(r for _, r in tj)
                for a in range(len(ti)):
                    for b in range(len(tj)):
                        d = ti[a][1] - tj[b][1]
                        if abs(dif - 2 * d) < abs(dif):
                            ti[a], tj[b] = tj[b], ti[a]
                            dif -= 2 * d
                            melhorou = True
