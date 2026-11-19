import { Link, useParams } from 'react-router'
import { useEstatisticasDaPelada, usePartidasDaPelada, usePeladaEstado } from '../api/hooks'
import { Carregando, Erro, Subtitulo } from '../components/ui'
import { corEquipe } from '../lib/cores'
import { formatarData } from '../lib/datas'

export function EstatisticasPelada() {
  const id = Number(useParams().id)
  const pelada = usePeladaEstado(id)
  const est = useEstatisticasDaPelada(id)
  const partidas = usePartidasDaPelada(id)

  const erro = pelada.error ?? est.error ?? partidas.error
  if (erro) return <Erro erro={erro} tentarDeNovo={() => [pelada, est, partidas].forEach((q) => q.refetch())} />
  if (!pelada.data || !est.data || !partidas.data) return <Carregando />

  const e = est.data

  return (
    <>
      <Link to={`/peladas/${id}`} className="mb-2 inline-block text-sm font-semibold text-marca">
        ← Voltar para a pelada
      </Link>
      <h1 className="text-2xl font-bold">Estatísticas</h1>
      <p className="mb-2 text-sm text-slate-500">
        {formatarData(pelada.data.data)} · {e.partidas_encerradas}{' '}
        {e.partidas_encerradas === 1 ? 'partida encerrada' : 'partidas encerradas'}
      </p>

      <Subtitulo>Equipes</Subtitulo>
      {e.equipes.length === 0 ? (
        <p className="text-slate-500">Ainda não teve sorteio.</p>
      ) : (
        <div className="overflow-hidden rounded-2xl bg-white">
          <table className="w-full text-center tabular-nums">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="py-2 pl-3 text-left font-semibold">Equipe</th>
                <th title="Partidas" className="w-8">P</th>
                <th title="Vitórias" className="w-8">V</th>
                <th title="Empates" className="w-8">E</th>
                <th title="Derrotas" className="w-8">D</th>
                <th title="Gols marcados" className="w-10">GM</th>
                <th title="Gols sofridos" className="w-12 pr-3">GS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {e.equipes.map((q) => (
                <tr key={q.id}>
                  <td className="py-2.5 pl-3 text-left font-semibold">
                    <span className={`mr-2 inline-block size-3 rounded-full ${corEquipe(q.nome).ponto}`} />
                    {q.nome}
                  </td>
                  <td>{q.partidas}</td>
                  <td>{q.vitorias}</td>
                  <td>{q.empates}</td>
                  <td>{q.derrotas}</td>
                  <td>{q.gols_marcados}</td>
                  <td className="pr-3">{q.gols_sofridos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Subtitulo>Artilheiros</Subtitulo>
      {e.artilheiros.length === 0 ? (
        <p className="text-slate-500">Nenhum gol ainda.</p>
      ) : (
        <ol className="divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white">
          {e.artilheiros.map((a) => (
            <li key={a.jogador.id}>
              <Link
                to={`/jogadores/${a.jogador.id}`}
                className="flex min-h-12 items-center gap-3 px-4 active:bg-slate-50"
              >
                <span className="w-6 text-slate-400 tabular-nums">{a.posicao}º</span>
                <span className="flex-1 truncate">{a.jogador.nome}</span>
                <span className="font-bold tabular-nums">
                  {a.valor} {a.valor === 1 ? 'gol' : 'gols'}
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}

      <Subtitulo>Partidas</Subtitulo>
      {partidas.data.length === 0 ? (
        <p className="text-slate-500">Nenhuma partida ainda.</p>
      ) : (
        <ol className="divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white">
          {partidas.data.map((p) => (
            <li key={p.id}>
              <Link to={`/partidas/${p.id}`} className="flex min-h-12 items-center gap-2 px-4 active:bg-slate-50">
                <span className="w-6 text-slate-400 tabular-nums">{p.numero}</span>
                <span className={`flex-1 truncate text-right font-semibold ${corEquipe(p.equipe_a.nome).texto}`}>
                  {p.equipe_a.nome}
                </span>
                <span className="px-1 font-bold whitespace-nowrap tabular-nums">
                  {p.equipe_a.gols} x {p.equipe_b.gols}
                </span>
                <span className={`flex-1 truncate font-semibold ${corEquipe(p.equipe_b.nome).texto}`}>
                  {p.equipe_b.nome}
                </span>
                <span className={`w-16 text-right text-xs ${p.encerrada ? 'text-slate-500' : 'font-bold text-aovivo'}`}>
                  {!p.encerrada
                    ? 'AO VIVO'
                    : p.penaltis_a !== null
                      ? `pên. ${p.penaltis_a}x${p.penaltis_b}`
                      : ''}
                </span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </>
  )
}
