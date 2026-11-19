/** Peças de partida usadas na fase Jogo e no detalhe da partida. */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { chaves } from '../api/chaves'
import { api, ok, type EquipePartida, type PartidaDetalhe } from '../api/client'
import { corEquipe } from '../lib/cores'
import { Erro } from './ui'

export type Lado = 'a' | 'b'

export function Placar({ partida, onGol }: { partida: PartidaDetalhe; onGol?: (lado: Lado) => void }) {
  const temPenaltis = partida.penaltis_a !== null && partida.penaltis_b !== null
  return (
    <section className="rounded-2xl bg-white p-4">
      <p className="mb-3 flex items-center justify-center gap-2 text-sm text-slate-500">
        Partida {partida.numero}
        {partida.encerrada ? (
          <span>· encerrada</span>
        ) : (
          <span className="rounded-md bg-aovivo px-1.5 py-0.5 text-xs font-bold tracking-wide text-white">
            AO VIVO
          </span>
        )}
      </p>
      <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-3">
        <LadoPlacar equipe={partida.equipe_a} onGol={onGol && (() => onGol('a'))} />
        <span className="pt-10 text-3xl text-slate-300">x</span>
        <LadoPlacar equipe={partida.equipe_b} onGol={onGol && (() => onGol('b'))} />
      </div>
      {temPenaltis && (
        <p className="mt-3 text-center text-sm text-slate-500">
          Pênaltis: {partida.penaltis_a} x {partida.penaltis_b}
        </p>
      )}
    </section>
  )
}

function LadoPlacar({ equipe, onGol }: { equipe: EquipePartida; onGol?: () => void }) {
  const cor = corEquipe(equipe.nome)
  return (
    <div className="flex flex-col items-center gap-2">
      <span className={`max-w-full truncate rounded-full px-3 py-1 text-sm font-bold ${cor.faixa}`}>
        {equipe.nome}
      </span>
      <span className="text-6xl leading-none font-bold tabular-nums">{equipe.gols}</span>
      {onGol && (
        <button
          className={`mt-1 min-h-12 w-full rounded-xl font-semibold active:opacity-80 ${cor.faixa}`}
          onClick={onGol}
        >
          + gol
        </button>
      )}
    </div>
  )
}

/** Gols em ordem. Com `admin`, tocar num gol pergunta se é para desfazer. */
export function ListaGols({ partida, admin }: { partida: PartidaDetalhe; admin: boolean }) {
  const queryClient = useQueryClient()
  const desfazer = useMutation({
    mutationFn: (golId: number) =>
      ok(
        api.DELETE('/api/partidas/{partida_id}/gols/{gol_id}', {
          params: { path: { partida_id: partida.id, gol_id: golId } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.partida(partida.id) }),
  })

  if (partida.gols.length === 0) {
    return <p className="mt-4 text-center text-slate-500">Nenhum gol.</p>
  }

  const nomeEquipe = (id: number) =>
    id === partida.equipe_a.id ? partida.equipe_a.nome : partida.equipe_b.nome

  return (
    <>
      <ul className="mt-4 divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white">
        {partida.gols.map((g) => {
          const equipe = nomeEquipe(g.equipe_id)
          const cor = corEquipe(equipe)
          const conteudo = (
            <>
              <span className={`size-3 shrink-0 rounded-full ${cor.ponto}`} />
              <span className="flex-1">
                ⚽ {g.autor.nome}
                {g.gol_contra ? (
                  <span className="text-slate-500"> (contra)</span>
                ) : (
                  g.assistente && <span className="text-slate-500"> ({g.assistente.nome})</span>
                )}
              </span>
              <span className={`text-sm font-semibold ${cor.texto}`}>{equipe}</span>
            </>
          )
          return (
            <li key={g.id}>
              {admin ? (
                <button
                  className="flex min-h-12 w-full items-center gap-3 px-4 text-left active:bg-slate-50 disabled:opacity-50"
                  disabled={desfazer.isPending}
                  onClick={() =>
                    window.confirm(`Desfazer o gol de ${g.autor.nome}?`) && desfazer.mutate(g.id)
                  }
                >
                  {conteudo}
                </button>
              ) : (
                <div className="flex min-h-12 items-center gap-3 px-4">{conteudo}</div>
              )}
            </li>
          )
        })}
      </ul>
      {admin && <p className="mt-1 text-center text-xs text-slate-400">Toque num gol para desfazer.</p>}
      {desfazer.isError && (
        <div className="mt-2">
          <Erro erro={desfazer.error} />
        </div>
      )}
    </>
  )
}
