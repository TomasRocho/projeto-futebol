"""Schemas de entrada/saída da API (o que trafega em JSON).

Separados das tabelas (models.py): a API valida aqui e devolve 422,
antes de chegar numa constraint do banco.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Rating = Annotated[int, Field(ge=0, le=5)]


# --- Jogador ---


class JogadorCreate(BaseModel):
    nome: Nome
    rating: Rating


class JogadorUpdate(BaseModel):
    """PATCH: campo omitido = não muda. `null` explícito é erro."""

    nome: Nome | None = None
    rating: Rating | None = None

    @field_validator("nome", "rating")
    @classmethod
    def _sem_null(cls, v):
        if v is None:
            raise ValueError("não pode ser null; omita o campo para não alterar")
        return v


class JogadorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    rating: int


class Estatisticas(BaseModel):
    partidas: int = 0
    vitorias: int = 0
    empates: int = 0
    derrotas: int = 0
    gols: int = 0
    assistencias: int = 0


class JogadorDetalhe(JogadorPublic):
    estatisticas: Estatisticas


# --- Pelada ---


class PeladaCreate(BaseModel):
    data: date
    numero_times: Annotated[int, Field(ge=2, le=4)]
    jogadores_por_time: Literal[6, 7]


class PeladaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    numero_times: int
    jogadores_por_time: int


class EquipeEstado(BaseModel):
    id: int
    nome: str
    ordem_fila: int | None  # None = em quadra
    rating_medio: float | None  # None = equipe sem ninguém
    jogadores: list[JogadorPublic]


class PartidaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    equipe_a_id: int
    equipe_b_id: int


class PeladaEstado(PeladaPublic):
    """Foto do momento: equipes (em quadra primeiro, depois a fila), avulsos e partida atual."""

    equipes: list[EquipeEstado]
    esperando: list[JogadorPublic]
    partida_em_andamento: PartidaResumo | None


# --- Presença ---


class PresencasDefinir(BaseModel):
    jogador_ids: list[int]


class PresencaCreate(BaseModel):
    jogador_id: int


class PresencaUpdate(BaseModel):
    equipe_id: int | None  # obrigatório; null = esperando
