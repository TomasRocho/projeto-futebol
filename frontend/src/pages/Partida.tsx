import { Link, useParams } from 'react-router'
import { ApiError, type EquipePartida } from '../api/client'
import { usePartida } from '../api/hooks'
import { ListaGols, Placar } from '../components/Partida'
import { Carregando, Erro, Rating, Subtitulo, Titulo } from '../components/ui'
import { corEquipe } from '../lib/cores'

/** Detalhe de uma partida (encerrada ou não). Só leitura: lançar gol é na tela da pelada. */
export function Partida() {
  const id = Number(useParams().id)
  const partida = usePartida(id)

  if (partida.isPending) return <Carregando />
  if (partida.isError) {
    if (partida.error instanceof ApiError && partida.error.status === 404) {
      return <Titulo>Partida não encontrada</Titulo>
    }
    return <Erro erro={partida.error} tentarDeNovo={() => partida.refetch()} />
  }

  const p = partida.data
  return (
    <>
      <Link
        to={`/peladas/${p.pelada_id}/estatisticas`}
        className="mb-2 inline-block text-sm font-semibold text-marca"
      >
        ← Partidas do dia
      </Link>
      <Placar partida={p} />
      <Subtitulo>Gols</Subtitulo>
      <ListaGols partida={p} admin={false} />
      <Subtitulo>Escalação</Subtitulo>
      <div className="grid grid-cols-2 gap-2">
        <Escalacao equipe={p.equipe_a} />
        <Escalacao equipe={p.equipe_b} />
      </div>
    </>
  )
}

function Escalacao({ equipe }: { equipe: EquipePartida }) {
  return (
    <section className="overflow-hidden rounded-2xl bg-white">
      <header className={`px-3 py-2 font-bold ${corEquipe(equipe.nome).faixa}`}>{equipe.nome}</header>
      <ul className="divide-y divide-slate-100">
        {equipe.jogadores.map((j) => (
          <li key={j.id}>
            <Link
              to={`/jogadores/${j.id}`}
              className="flex min-h-11 items-center justify-between gap-2 px-3 active:bg-slate-50"
            >
              <span className="truncate">{j.nome}</span>
              <Rating valor={j.rating} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
