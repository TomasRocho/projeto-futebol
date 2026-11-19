import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, type PeladaEstado } from '../../api/client'
import { usePeladaEstado } from '../../api/hooks'
import { Carregando, Erro, Titulo } from '../../components/ui'
import { formatarData, hojeISO } from '../../lib/datas'
import { FaseEntrePartidas } from './FaseEntrePartidas'
import { FaseJogo } from './FaseJogo'
import { FasePresenca } from './FasePresenca'

/** Tela principal: muda conforme a fase da pelada (ver Telas-Frontend.md). */
export function PeladaPage() {
  const id = Number(useParams().id)
  // key: trocar de pelada recomeça a tela (e some o aviso da anterior)
  return <Pelada key={id} id={id} />
}

function Pelada({ id }: { id: number }) {
  const estado = usePeladaEstado(id)
  const [aviso, setAviso] = useState<string[] | null>(null)

  if (estado.isPending) return <Carregando />
  if (estado.isError) {
    if (estado.error instanceof ApiError && estado.error.status === 404) {
      return (
        <>
          <Titulo>Pelada não encontrada</Titulo>
          <Link to="/peladas" className="font-semibold text-marca">
            Ver todas as peladas
          </Link>
        </>
      )
    }
    return <Erro erro={estado.error} tentarDeNovo={() => estado.refetch()} />
  }

  const e = estado.data
  return (
    <>
      <div className="mb-4">
        <h1 className="text-2xl font-bold">
          {e.data === hojeISO() ? 'Pelada de hoje' : formatarData(e.data)}
        </h1>
        <p className="text-sm text-slate-500">
          {e.numero_times} times de {e.jogadores_por_time} ·{' '}
          <Link to={`/peladas/${e.id}/estatisticas`} className="font-semibold text-marca">
            Estatísticas
          </Link>{' '}
          ·{' '}
          <Link to="/peladas" className="font-semibold text-marca">
            Outras peladas
          </Link>
        </p>
      </div>

      {aviso && <Aviso linhas={aviso} fechar={() => setAviso(null)} />}
      <Fase estado={e} onEncerrada={setAviso} />
    </>
  )
}

function Fase({ estado, onEncerrada }: { estado: PeladaEstado; onEncerrada: (resumo: string[]) => void }) {
  if (estado.equipes.length === 0) return <FasePresenca estado={estado} />
  if (estado.partida_em_andamento) return <FaseJogo estado={estado} onEncerrada={onEncerrada} />
  return <FaseEntrePartidas estado={estado} />
}

/** Resumo do que o encerramento fez (resultado + rodízio). */
function Aviso({ linhas, fechar }: { linhas: string[]; fechar: () => void }) {
  return (
    <div className="mb-4 flex items-start gap-2 rounded-xl border border-marca/20 bg-marca-clara p-3 text-marca-escura">
      <div className="flex-1 space-y-0.5">
        {linhas.map((l) => (
          <p key={l}>{l}</p>
        ))}
      </div>
      <button className="-m-1 grid size-9 place-items-center rounded-full active:bg-white/60" onClick={fechar} aria-label="Fechar aviso">
        ✕
      </button>
    </div>
  )
}
