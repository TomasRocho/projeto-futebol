from fastapi import APIRouter

from app.db import SessionDep, get_or_404
from app.estatisticas import estatisticas_pelada, ranking
from app.models import Pelada
from app.schemas import PeladaEstatisticas, RankingItem, TipoRanking

router = APIRouter(tags=["estatisticas"])


@router.get("/ranking", response_model=list[RankingItem])
def ver_ranking(session: SessionDep, tipo: TipoRanking = "gols", pelada_id: int | None = None):
    """Ranking geral, ou de uma pelada só (`pelada_id`). Só lista quem tem valor > 0."""
    if pelada_id is not None:
        get_or_404(session, Pelada, pelada_id, "Pelada não encontrada")
    return ranking(session, tipo, pelada_id)


@router.get("/peladas/{pelada_id}/estatisticas", response_model=PeladaEstatisticas)
def ver_estatisticas_pelada(pelada_id: int, session: SessionDep):
    """V/E/D e gols de cada equipe no dia, e os artilheiros."""
    return estatisticas_pelada(session, get_or_404(session, Pelada, pelada_id, "Pelada não encontrada"))
