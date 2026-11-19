import { Link, useSearchParams } from 'react-router'
import { usePeladas, useRanking, type TipoRanking } from '../api/hooks'
import { Carregando, Erro, Titulo } from '../components/ui'
import { formatarData } from '../lib/datas'

const ABAS: { tipo: TipoRanking; rotulo: string; unidade: [string, string] }[] = [
  { tipo: 'gols', rotulo: 'Gols', unidade: ['gol', 'gols'] },
  { tipo: 'assistencias', rotulo: 'Assistências', unidade: ['assist.', 'assist.'] },
  { tipo: 'vitorias', rotulo: 'Vitórias', unidade: ['vitória', 'vitórias'] },
]

const MEDALHA: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }

/** Ranking geral ou de uma pelada. Aba e filtro ficam na URL (?tipo=&pelada=), dá para compartilhar. */
export function Ranking() {
  const [params, setParams] = useSearchParams()
  const tipo = (ABAS.find((a) => a.tipo === params.get('tipo'))?.tipo ?? 'gols') as TipoRanking
  const peladaId = params.get('pelada') ? Number(params.get('pelada')) : null
  const aba = ABAS.find((a) => a.tipo === tipo)!

  const peladas = usePeladas()
  const ranking = useRanking(tipo, peladaId)

  function mudar(novo: { tipo?: TipoRanking; pelada?: number | null }) {
    const p = new URLSearchParams(params)
    if (novo.tipo) p.set('tipo', novo.tipo)
    if (novo.pelada !== undefined) {
      if (novo.pelada === null) p.delete('pelada')
      else p.set('pelada', String(novo.pelada))
    }
    setParams(p, { replace: true })
  }

  return (
    <>
      <Titulo>Ranking</Titulo>

      <div className="mb-3 flex border-b border-slate-200" role="tablist">
        {ABAS.map((a) => (
          <button
            key={a.tipo}
            role="tab"
            aria-selected={a.tipo === tipo}
            className={`-mb-px min-h-11 flex-1 border-b-2 text-sm font-semibold ${
              a.tipo === tipo ? 'border-marca text-marca' : 'border-transparent text-slate-500'
            }`}
            onClick={() => mudar({ tipo: a.tipo })}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <select
        className="mb-4 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3"
        value={peladaId ?? ''}
        onChange={(e) => mudar({ pelada: e.target.value ? Number(e.target.value) : null })}
        aria-label="Filtrar por pelada"
      >
        <option value="">Todas as peladas</option>
        {peladas.data?.map((p) => (
          <option key={p.id} value={p.id}>
            {formatarData(p.data)}
          </option>
        ))}
      </select>

      {ranking.isPending && <Carregando />}
      {ranking.isError && <Erro erro={ranking.error} tentarDeNovo={() => ranking.refetch()} />}
      {ranking.data?.length === 0 && (
        <p className="py-10 text-center text-slate-500">Ninguém pontuou ainda.</p>
      )}

      <ol className="space-y-2">
        {ranking.data?.map((item) => {
          const e = item.estatisticas
          return (
            <li key={item.jogador.id}>
              <Link
                to={`/jogadores/${item.jogador.id}`}
                className="flex items-center gap-3 rounded-2xl bg-white p-3 active:bg-slate-50"
              >
                <span className="w-8 text-center text-lg font-bold text-slate-400 tabular-nums">
                  {MEDALHA[item.posicao] ?? `${item.posicao}º`}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{item.jogador.nome}</span>
                  <span className="block text-xs text-slate-500">
                    {e.partidas} {e.partidas === 1 ? 'partida' : 'partidas'} · {e.vitorias}V {e.empates}E{' '}
                    {e.derrotas}D
                  </span>
                </span>
                <span className="text-right">
                  <span className="block text-2xl leading-none font-bold tabular-nums">{item.valor}</span>
                  <span className="text-xs text-slate-500">{aba.unidade[item.valor === 1 ? 0 : 1]}</span>
                </span>
              </Link>
            </li>
          )
        })}
      </ol>
    </>
  )
}
