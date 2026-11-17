import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useAdmin } from '../../admin'
import { chaves } from '../../api/chaves'
import { api, ok, type JogadorPublic, type PeladaEstado } from '../../api/client'
import { useAcaoNaPelada, useJogadores, usePartidasDaPelada } from '../../api/hooks'
import { EquipeCard } from '../../components/EquipeCard'
import { NovoJogadorRapido } from '../../components/NovoJogadorRapido'
import { Sheet } from '../../components/Sheet'
import { Botao, Carregando, Erro, Subtitulo } from '../../components/ui'
import { corEquipe } from '../../lib/cores'

type Selecionado = { jogador: JogadorPublic; equipeId: number | null }

/** Times sorteados, nenhuma partida em andamento. Também usado (sem ações) durante o jogo. */
export function FaseEntrePartidas({ estado, somenteLeitura = false }: { estado: PeladaEstado; somenteLeitura?: boolean }) {
  const { ehAdmin } = useAdmin()
  const admin = ehAdmin && !somenteLeitura
  const [selecionado, setSelecionado] = useState<Selecionado | null>(null)
  const [chegouAlguem, setChegouAlguem] = useState(false)

  const emQuadra = estado.equipes.filter((e) => e.ordem_fila === null)
  const fila = estado.equipes.filter((e) => e.ordem_fila !== null)

  return (
    <>
      {admin && <AcoesPrincipais estado={estado} />}

      <Subtitulo>Em quadra</Subtitulo>
      <div className="grid grid-cols-2 gap-2">
        {emQuadra.map((e) => (
          <EquipeCard
            key={e.id}
            equipe={e}
            porTime={estado.jogadores_por_time}
            onJogador={admin ? (jogador) => setSelecionado({ jogador, equipeId: e.id }) : undefined}
          />
        ))}
      </div>

      {fila.length > 0 && (
        <>
          <Subtitulo>Fila</Subtitulo>
          <div className="grid grid-cols-2 gap-2">
            {fila.map((e) => (
              <EquipeCard
                key={e.id}
                equipe={e}
                porTime={estado.jogadores_por_time}
                rotulo={`${e.ordem_fila}º`}
                onJogador={admin ? (jogador) => setSelecionado({ jogador, equipeId: e.id }) : undefined}
              />
            ))}
          </div>
        </>
      )}

      <Subtitulo>Esperando</Subtitulo>
      {estado.esperando.length === 0 ? (
        <p className="text-stone-500">Ninguém esperando.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {estado.esperando.map((j) => (
            <li key={j.id}>
              {admin ? (
                <button
                  className="min-h-10 rounded-full bg-white px-3 shadow-sm active:bg-stone-100"
                  onClick={() => setSelecionado({ jogador: j, equipeId: null })}
                >
                  {j.nome}
                </button>
              ) : (
                <span className="inline-block rounded-full bg-white px-3 py-2 shadow-sm">{j.nome}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {admin && (
        <Botao variante="secundario" className="mt-6 w-full" onClick={() => setChegouAlguem(true)}>
          + Chegou alguém
        </Botao>
      )}

      {selecionado && (
        <AcoesJogador estado={estado} {...selecionado} fechar={() => setSelecionado(null)} />
      )}
      {chegouAlguem && <ChegouAlguem estado={estado} fechar={() => setChegouAlguem(false)} />}
    </>
  )
}

function AcoesPrincipais({ estado }: { estado: PeladaEstado }) {
  const queryClient = useQueryClient()
  const peladaId = estado.id
  const partidas = usePartidasDaPelada(peladaId)
  const path = { params: { path: { pelada_id: peladaId } } }

  const comecar = useMutation({
    mutationFn: () => ok(api.POST('/api/peladas/{pelada_id}/partidas', path)),
    onSuccess: (partida) => {
      queryClient.setQueryData(chaves.partida(partida.id), partida)
      queryClient.invalidateQueries({ queryKey: chaves.pelada(peladaId) })
    },
  })
  const refazer = useAcaoNaPelada(peladaId, () => ok(api.POST('/api/peladas/{pelada_id}/sorteio', path)))

  const nenhumaPartida = partidas.data?.length === 0
  const proxima = partidas.data ? partidas.data.length + 1 : null

  return (
    <div className="space-y-2">
      <Botao className="w-full text-lg" disabled={comecar.isPending} onClick={() => comecar.mutate()}>
        ▶ Começar {proxima ? `partida ${proxima}` : 'partida'}
      </Botao>
      {nenhumaPartida && (
        <Botao
          variante="secundario"
          className="w-full"
          disabled={refazer.isPending}
          onClick={() => window.confirm('Refazer o sorteio? Os times atuais serão desfeitos.') && refazer.mutate()}
        >
          🎲 Refazer sorteio
        </Botao>
      )}
      {comecar.isError && <Erro erro={comecar.error} />}
      {refazer.isError && <Erro erro={refazer.error} />}
    </div>
  )
}

function AcoesJogador({
  estado,
  jogador,
  equipeId,
  fechar,
}: Selecionado & { estado: PeladaEstado; fechar: () => void }) {
  const queryClient = useQueryClient()
  const path = { params: { path: { pelada_id: estado.id, jogador_id: jogador.id } } }

  const mover = useAcaoNaPelada(estado.id, (destino: number | null) =>
    ok(api.PATCH('/api/peladas/{pelada_id}/presencas/{jogador_id}', { ...path, body: { equipe_id: destino } })),
  )
  const foiEmbora = useMutation({
    mutationFn: () => ok(api.DELETE('/api/peladas/{pelada_id}/presencas/{jogador_id}', path)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chaves.pelada(estado.id) }),
  })

  const destinos = estado.equipes.filter((e) => e.id !== equipeId)
  const ocupado = mover.isPending || foiEmbora.isPending

  return (
    <Sheet titulo={jogador.nome} fechar={fechar}>
      <p className="mb-2 text-sm text-stone-600">Mover para</p>
      <div className="grid grid-cols-2 gap-2">
        {destinos.map((e) => {
          const cheio = e.jogadores.length >= estado.jogadores_por_time
          return (
            <button
              key={e.id}
              disabled={cheio || ocupado}
              className={`min-h-12 rounded-xl font-semibold disabled:opacity-40 ${corEquipe(e.nome).faixa}`}
              onClick={() => mover.mutate(e.id, { onSuccess: fechar })}
            >
              {e.nome}
              {cheio && ' (cheio)'}
            </button>
          )
        })}
        {equipeId !== null && (
          <button
            disabled={ocupado}
            className="min-h-12 rounded-xl bg-stone-200 font-semibold disabled:opacity-40"
            onClick={() => mover.mutate(null, { onSuccess: fechar })}
          >
            Esperando
          </button>
        )}
      </div>
      <p className="mt-2 text-xs text-stone-500">Vale a partir da próxima partida.</p>

      <Botao
        variante="perigo"
        className="mt-5 w-full"
        disabled={ocupado}
        onClick={() =>
          window.confirm(`${jogador.nome} foi embora? O time dele fica com um a menos.`) &&
          foiEmbora.mutate(undefined, { onSuccess: fechar })
        }
      >
        Foi embora
      </Botao>
      {mover.isError && <div className="mt-3"><Erro erro={mover.error} /></div>}
      {foiEmbora.isError && <div className="mt-3"><Erro erro={foiEmbora.error} /></div>}
    </Sheet>
  )
}

function ChegouAlguem({ estado, fechar }: { estado: PeladaEstado; fechar: () => void }) {
  const jogadores = useJogadores()
  const adicionar = useAcaoNaPelada(estado.id, (jogadorId: number) =>
    ok(
      api.POST('/api/peladas/{pelada_id}/presencas', {
        params: { path: { pelada_id: estado.id } },
        body: { jogador_id: jogadorId },
      }),
    ),
  )

  const presentes = new Set(
    [...estado.esperando, ...estado.equipes.flatMap((e) => e.jogadores)].map((j) => j.id),
  )
  const ausentes = jogadores.data?.filter((j) => !presentes.has(j.id)) ?? []

  return (
    <Sheet titulo="Quem chegou?" fechar={fechar}>
      <p className="mb-3 text-sm text-stone-600">Entra como esperando e troca com o time que perder.</p>
      {jogadores.isPending && <Carregando />}
      {jogadores.data && ausentes.length === 0 && (
        <p className="mb-3 text-stone-500">Todo mundo cadastrado já está na pelada.</p>
      )}
      <ul className="mb-3 divide-y divide-stone-100">
        {ausentes.map((j) => (
          <li key={j.id}>
            <button
              disabled={adicionar.isPending}
              className="min-h-12 w-full text-left active:bg-stone-50 disabled:opacity-50"
              onClick={() => adicionar.mutate(j.id, { onSuccess: fechar })}
            >
              {j.nome}
            </button>
          </li>
        ))}
      </ul>
      {adicionar.isError && <Erro erro={adicionar.error} />}
      <NovoJogadorRapido onCriado={(j) => adicionar.mutate(j.id, { onSuccess: fechar })} />
    </Sheet>
  )
}
