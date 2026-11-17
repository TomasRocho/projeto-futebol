import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type Dispatch, type SetStateAction } from 'react'
import { useAdmin } from '../../admin'
import { chaves } from '../../api/chaves'
import {
  api,
  ok,
  type EquipePartida,
  type JogadorPublic,
  type PartidaDetalhe,
  type PeladaEstado,
} from '../../api/client'
import { usePartida } from '../../api/hooks'
import { Sheet } from '../../components/Sheet'
import { Botao, Carregando, Erro } from '../../components/ui'
import { corEquipe } from '../../lib/cores'
import { resumoEncerramento } from '../../lib/encerramento'
import { FaseEntrePartidas } from './FaseEntrePartidas'

type Lado = 'a' | 'b'

/** Partida em andamento: placar, gols, e (admin) lançar gol / desfazer / encerrar. */
export function FaseJogo({
  estado,
  onEncerrada,
}: {
  estado: PeladaEstado
  onEncerrada: (resumo: string[]) => void
}) {
  const { ehAdmin } = useAdmin()
  const partida = usePartida(estado.partida_em_andamento!.id)
  const [golDo, setGolDo] = useState<Lado | null>(null)
  const [encerrando, setEncerrando] = useState(false)

  if (partida.isPending) return <Carregando />
  if (partida.isError) return <Erro erro={partida.error} tentarDeNovo={() => partida.refetch()} />
  const p = partida.data

  return (
    <>
      <Placar partida={p} onGol={ehAdmin ? setGolDo : undefined} />
      <ListaGols partida={p} admin={ehAdmin} />
      {ehAdmin && (
        <Botao className="mt-4 w-full text-lg" onClick={() => setEncerrando(true)}>
          🏁 Encerrar partida
        </Botao>
      )}

      <FaseEntrePartidas estado={estado} somenteLeitura />

      {golDo && <GolSheet partida={p} lado={golDo} fechar={() => setGolDo(null)} />}
      {encerrando && (
        <EncerrarSheet
          estado={estado}
          partida={p}
          fechar={() => setEncerrando(false)}
          onEncerrada={onEncerrada}
        />
      )}
    </>
  )
}

// --- Placar ---

function Placar({ partida, onGol }: { partida: PartidaDetalhe; onGol?: (lado: Lado) => void }) {
  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="mb-3 text-center text-sm text-stone-500">Partida {partida.numero} · em andamento</p>
      <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-3">
        <LadoPlacar equipe={partida.equipe_a} onGol={onGol && (() => onGol('a'))} />
        <span className="pt-10 text-3xl text-stone-300">x</span>
        <LadoPlacar equipe={partida.equipe_b} onGol={onGol && (() => onGol('b'))} />
      </div>
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

// --- Gols ---

function ListaGols({ partida, admin }: { partida: PartidaDetalhe; admin: boolean }) {
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
    return <p className="mt-4 text-center text-stone-500">Nenhum gol ainda.</p>
  }

  const nomeEquipe = (id: number) =>
    id === partida.equipe_a.id ? partida.equipe_a.nome : partida.equipe_b.nome

  return (
    <>
      <ul className="mt-4 divide-y divide-stone-100 overflow-hidden rounded-xl bg-white shadow-sm">
        {partida.gols.map((g) => {
          const equipe = nomeEquipe(g.equipe_id)
          const cor = corEquipe(equipe)
          const conteudo = (
            <>
              <span className={`size-3 shrink-0 rounded-full ${cor.ponto}`} />
              <span className="flex-1">
                ⚽ {g.autor.nome}
                {g.gol_contra ? (
                  <span className="text-stone-500"> (contra)</span>
                ) : (
                  g.assistente && <span className="text-stone-500"> ({g.assistente.nome})</span>
                )}
              </span>
              <span className={`text-sm font-semibold ${cor.texto}`}>{equipe}</span>
            </>
          )
          return (
            <li key={g.id}>
              {admin ? (
                <button
                  className="flex min-h-12 w-full items-center gap-3 px-4 text-left active:bg-stone-50 disabled:opacity-50"
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
      {admin && <p className="mt-1 text-center text-xs text-stone-400">Toque num gol para desfazer.</p>}
      {desfazer.isError && (
        <div className="mt-2">
          <Erro erro={desfazer.error} />
        </div>
      )}
    </>
  )
}

/** Lançar gol: autor (ou gol contra) → assistência. Listas vêm da escalação da partida. */
function GolSheet({ partida, lado, fechar }: { partida: PartidaDetalhe; lado: Lado; fechar: () => void }) {
  const queryClient = useQueryClient()
  const [beneficiada, adversaria] =
    lado === 'a' ? [partida.equipe_a, partida.equipe_b] : [partida.equipe_b, partida.equipe_a]
  const [contra, setContra] = useState(false)
  const [autor, setAutor] = useState<JogadorPublic | null>(null)

  const registrar = useMutation({
    mutationFn: (gol: { autor_id: number; assistente_id: number | null; gol_contra: boolean }) =>
      ok(
        api.POST('/api/partidas/{partida_id}/gols', {
          params: { path: { partida_id: partida.id } },
          body: { equipe_id: beneficiada.id, ...gol },
        }),
      ),
    onSuccess: (detalhe) => {
      queryClient.setQueryData(chaves.partida(partida.id), detalhe)
      fechar()
    },
  })

  const erro = registrar.isError && (
    <div className="mt-3">
      <Erro erro={registrar.error} />
    </div>
  )

  if (autor) {
    return (
      <Sheet titulo={`Gol de ${autor.nome}: assistência?`} fechar={fechar}>
        <Botao
          className="mb-3 w-full"
          disabled={registrar.isPending}
          onClick={() => registrar.mutate({ autor_id: autor.id, assistente_id: null, gol_contra: false })}
        >
          Sem assistência
        </Botao>
        <BotoesJogadores
          jogadores={beneficiada.jogadores.filter((j) => j.id !== autor.id)}
          desabilitado={registrar.isPending}
          onEscolher={(j) => registrar.mutate({ autor_id: autor.id, assistente_id: j.id, gol_contra: false })}
        />
        <button className="mt-3 min-h-11 w-full font-semibold text-stone-600" onClick={() => setAutor(null)}>
          ← Voltar
        </button>
        {erro}
      </Sheet>
    )
  }

  return (
    <Sheet
      titulo={contra ? `Gol contra, a favor do ${beneficiada.nome}` : `Gol do ${beneficiada.nome}: quem fez?`}
      fechar={fechar}
    >
      <button
        className={`mb-3 min-h-11 w-full rounded-xl border font-semibold ${
          contra ? 'border-stone-800 bg-stone-800 text-white' : 'border-stone-300 text-stone-700'
        }`}
        onClick={() => setContra((c) => !c)}
      >
        {contra ? `✓ Gol contra: quem do ${adversaria.nome}?` : 'Foi gol contra?'}
      </button>
      <BotoesJogadores
        jogadores={contra ? adversaria.jogadores : beneficiada.jogadores}
        desabilitado={registrar.isPending}
        onEscolher={(j) =>
          contra
            ? registrar.mutate({ autor_id: j.id, assistente_id: null, gol_contra: true })
            : setAutor(j)
        }
      />
      {erro}
    </Sheet>
  )
}

function BotoesJogadores({
  jogadores,
  desabilitado,
  onEscolher,
}: {
  jogadores: JogadorPublic[]
  desabilitado: boolean
  onEscolher: (j: JogadorPublic) => void
}) {
  if (jogadores.length === 0) return <p className="text-stone-500">Ninguém escalado.</p>
  return (
    <ul className="grid grid-cols-2 gap-2">
      {jogadores.map((j) => (
        <li key={j.id}>
          <button
            disabled={desabilitado}
            className="min-h-12 w-full truncate rounded-xl bg-stone-100 px-3 font-semibold active:bg-stone-200 disabled:opacity-50"
            onClick={() => onEscolher(j)}
          >
            {j.nome}
          </button>
        </li>
      ))}
    </ul>
  )
}

// --- Encerrar ---

function EncerrarSheet({
  estado,
  partida,
  fechar,
  onEncerrada,
}: {
  estado: PeladaEstado
  partida: PartidaDetalhe
  fechar: () => void
  onEncerrada: (resumo: string[]) => void
}) {
  const queryClient = useQueryClient()
  const { equipe_a: a, equipe_b: b } = partida
  const empate = a.gols === b.gols
  const pedePenaltis = empate && estado.numero_times < 4
  const [penA, setPenA] = useState(0)
  const [penB, setPenB] = useState(0)

  const encerrar = useMutation({
    mutationFn: () =>
      ok(
        api.POST('/api/partidas/{partida_id}/encerrar', {
          params: { path: { partida_id: partida.id } },
          body: pedePenaltis ? { penaltis_a: penA, penaltis_b: penB } : {},
        }),
      ),
    onSuccess: (novoEstado) => {
      onEncerrada(resumoEncerramento(estado, novoEstado, partida, pedePenaltis ? { a: penA, b: penB } : null))
      fechar()
      queryClient.setQueryData(chaves.pelada(estado.id), novoEstado)
      queryClient.invalidateQueries({ queryKey: chaves.partida(partida.id) })
      queryClient.invalidateQueries({ queryKey: chaves.partidasDaPelada(estado.id) })
    },
  })

  let texto: string
  if (!empate) {
    const [v, p] = a.gols > b.gols ? [a, b] : [b, a]
    texto = `${v.nome} venceu ${v.gols} x ${p.gols}.`
    if (estado.numero_times > 2) texto += ` ${p.nome} vai para a fila.`
  } else if (pedePenaltis) {
    texto = `Empate em ${a.gols} x ${b.gols}: quanto ficou nos pênaltis?`
  } else {
    texto = `Empate em ${a.gols} x ${b.gols}: com 4 times, os dois saem.`
  }

  const penaltisEmpatados = pedePenaltis && penA === penB

  return (
    <Sheet titulo="Encerrar partida?" fechar={fechar}>
      <p className="mb-4 text-stone-700">{texto}</p>

      {pedePenaltis && (
        <div className="mb-4 space-y-2">
          <ContadorPenaltis equipe={a.nome} valor={penA} mudar={setPenA} />
          <ContadorPenaltis equipe={b.nome} valor={penB} mudar={setPenB} />
          <p className="text-xs text-stone-500">
            {penaltisEmpatados
              ? 'Os pênaltis não podem terminar empatados.'
              : 'Pênalti só decide quem sai: nas estatísticas conta como empate.'}
          </p>
        </div>
      )}

      {encerrar.isError && (
        <div className="mb-3">
          <Erro erro={encerrar.error} />
        </div>
      )}
      <div className="flex gap-2">
        <Botao variante="secundario" onClick={fechar}>
          Cancelar
        </Botao>
        <Botao
          className="flex-1"
          disabled={encerrar.isPending || penaltisEmpatados}
          onClick={() => encerrar.mutate()}
        >
          {encerrar.isPending ? 'Encerrando…' : '🏁 Encerrar'}
        </Botao>
      </div>
    </Sheet>
  )
}

function ContadorPenaltis({
  equipe,
  valor,
  mudar,
}: {
  equipe: string
  valor: number
  // updater funcional: dois toques rápidos contam dois (não lê um `valor` velho)
  mudar: Dispatch<SetStateAction<number>>
}) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-stone-50 p-2">
      <span className={`rounded-full px-3 py-1 text-sm font-bold ${corEquipe(equipe).faixa}`}>{equipe}</span>
      <div className="flex items-center gap-3">
        <button
          className="size-11 rounded-full bg-white text-2xl shadow-sm disabled:opacity-40"
          disabled={valor === 0}
          onClick={() => mudar((v) => Math.max(0, v - 1))}
          aria-label={`Menos um pênalti para ${equipe}`}
        >
          −
        </button>
        <span className="w-8 text-center text-2xl font-bold tabular-nums">{valor}</span>
        <button
          className="size-11 rounded-full bg-white text-2xl shadow-sm"
          onClick={() => mudar((v) => v + 1)}
          aria-label={`Mais um pênalti para ${equipe}`}
        >
          +
        </button>
      </div>
    </div>
  )
}
