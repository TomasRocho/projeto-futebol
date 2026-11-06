"""Tabelas do banco. Espelha o SQL de Modelo-Relacional.md (vault).

Regras que o banco garante sozinho estão aqui (CHECK, FK composta, RESTRICT/CASCADE).
Regras de fila, rodízio e "equipe pertence à partida" ficam na camada de serviço.
"""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


class Jogador(SQLModel, table=True):
    __tablename__ = "jogador"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (CheckConstraint("rating BETWEEN 0 AND 5", name="ck_jogador_rating"),)

    id: int | None = Field(default=None, primary_key=True)
    nome: str
    rating: int


class Pelada(SQLModel, table=True):
    __tablename__ = "pelada"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        CheckConstraint("numero_times BETWEEN 2 AND 4", name="ck_pelada_numero_times"),
        CheckConstraint("jogadores_por_time IN (6, 7)", name="ck_pelada_jogadores_por_time"),
    )

    id: int | None = Field(default=None, primary_key=True)
    data: date
    numero_times: int
    jogadores_por_time: int


class Time(SQLModel, table=True):
    # "time" é tipo em SQL, por isso a tabela se chama "equipe".
    __tablename__ = "equipe"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("id", "pelada_id", name="uq_equipe_id_pelada"),  # alvo das FKs compostas
        UniqueConstraint("pelada_id", "nome", name="uq_equipe_pelada_nome"),
    )

    id: int | None = Field(default=None, primary_key=True)
    pelada_id: int = Field(foreign_key="pelada.id", ondelete="CASCADE")
    nome: str
    ordem_fila: int | None = None  # None = em quadra; 1, 2... = posição na fila


class Presenca(SQLModel, table=True):
    __tablename__ = "presenca"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        ForeignKeyConstraint(
            ["equipe_id", "pelada_id"],
            ["equipe.id", "equipe.pelada_id"],
            ondelete="CASCADE",
            name="fk_presenca_equipe",
        ),
    )

    pelada_id: int = Field(foreign_key="pelada.id", primary_key=True, ondelete="CASCADE")
    jogador_id: int = Field(foreign_key="jogador.id", primary_key=True, ondelete="RESTRICT")
    equipe_id: int | None = None  # None = esperando (avulso)


class Partida(SQLModel, table=True):
    __tablename__ = "partida"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("pelada_id", "numero", name="uq_partida_pelada_numero"),
        ForeignKeyConstraint(
            ["equipe_a_id", "pelada_id"],
            ["equipe.id", "equipe.pelada_id"],
            ondelete="CASCADE",
            name="fk_partida_equipe_a",
        ),
        ForeignKeyConstraint(
            ["equipe_b_id", "pelada_id"],
            ["equipe.id", "equipe.pelada_id"],
            ondelete="CASCADE",
            name="fk_partida_equipe_b",
        ),
        CheckConstraint("equipe_a_id <> equipe_b_id", name="ck_partida_equipes_distintas"),
        CheckConstraint(
            "(penaltis_a IS NULL) = (penaltis_b IS NULL)", name="ck_partida_penaltis_ambos"
        ),
        CheckConstraint(
            "penaltis_a IS NULL OR penaltis_a <> penaltis_b", name="ck_partida_penaltis_sem_empate"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    pelada_id: int = Field(foreign_key="pelada.id", ondelete="CASCADE")
    numero: int  # ordem da partida na pelada (1, 2, 3...)
    equipe_a_id: int
    equipe_b_id: int
    penaltis_a: int | None = None
    penaltis_b: int | None = None
    encerrada: bool = False


class Escalacao(SQLModel, table=True):
    """Foto de quem jogou cada partida, e por qual equipe. Nunca muda depois."""

    __tablename__ = "escalacao"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("idx_escalacao_jogador", "jogador_id"),)

    partida_id: int = Field(foreign_key="partida.id", primary_key=True, ondelete="CASCADE")
    jogador_id: int = Field(foreign_key="jogador.id", primary_key=True, ondelete="RESTRICT")
    equipe_id: int = Field(foreign_key="equipe.id", ondelete="CASCADE")


class Gol(SQLModel, table=True):
    __tablename__ = "gol"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        # autor e assistente precisam estar escalados nessa partida
        ForeignKeyConstraint(
            ["partida_id", "autor_id"],
            ["escalacao.partida_id", "escalacao.jogador_id"],
            ondelete="CASCADE",
            name="fk_gol_autor",
        ),
        ForeignKeyConstraint(
            ["partida_id", "assistente_id"],
            ["escalacao.partida_id", "escalacao.jogador_id"],
            ondelete="CASCADE",
            name="fk_gol_assistente",
        ),
        CheckConstraint(
            "assistente_id IS NULL OR assistente_id <> autor_id", name="ck_gol_assistente_autor"
        ),
        CheckConstraint("NOT gol_contra OR assistente_id IS NULL", name="ck_gol_contra_sem_assist"),
        Index("idx_gol_autor", "autor_id"),
        Index("idx_gol_assistente", "assistente_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    partida_id: int = Field(foreign_key="partida.id", ondelete="CASCADE")
    equipe_id: int = Field(foreign_key="equipe.id", ondelete="CASCADE")  # time beneficiado
    autor_id: int
    assistente_id: int | None = None
    gol_contra: bool = False
