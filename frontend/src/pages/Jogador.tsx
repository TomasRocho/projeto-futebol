import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAdmin } from '../admin'
import { chaves } from '../api/chaves'
import { api, ApiError, ok } from '../api/client'
import { useJogador } from '../api/hooks'
import { Botao, Carregando, Erro, SeletorRating, Titulo } from '../components/ui'

export function Jogador() {
  const id = Number(useParams().id)
  const { ehAdmin } = useAdmin()
  const jogador = useJogador(id)
  const [editando, setEditando] = useState(false)

  if (jogador.isPending) return <Carregando />
  if (jogador.isError) {
    if (jogador.error instanceof ApiError && jogador.error.status === 404) {
      return (
        <>
          <Titulo>Jogador não encontrado</Titulo>
          <Link to="/jogadores" className="font-semibold text-marca">
            Ver todos os jogadores
          </Link>
        </>
      )
    }
    return <Erro erro={jogador.error} tentarDeNovo={() => jogador.refetch()} />
  }

  const j = jogador.data
  const e = j.estatisticas

  return (
    <>
      <Link to="/jogadores" className="mb-2 inline-block text-sm font-semibold text-marca">
        ← Jogadores
      </Link>

      {editando ? (
        <EditarJogador id={id} nome={j.nome} rating={j.rating} fechar={() => setEditando(false)} />
      ) : (
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold">{j.nome}</h1>
            <p className="text-slate-500">Rating ★{j.rating}</p>
          </div>
          {ehAdmin && (
            <Botao variante="secundario" onClick={() => setEditando(true)}>
              Editar
            </Botao>
          )}
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <Numero rotulo="Partidas" valor={e.partidas} />
        <Numero rotulo="Gols" valor={e.gols} />
        <Numero rotulo="Assist." valor={e.assistencias} />
        <Numero rotulo="Vitórias" valor={e.vitorias} cor="text-vitoria" />
        <Numero rotulo="Empates" valor={e.empates} cor="text-slate-500" />
        <Numero rotulo="Derrotas" valor={e.derrotas} cor="text-derrota" />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Pênalti conta como empate. Gol contra não conta como gol do jogador.
      </p>
    </>
  )
}

function Numero({ rotulo, valor, cor = '' }: { rotulo: string; valor: number; cor?: string }) {
  return (
    <div className="rounded-2xl bg-white p-3 text-center">
      <p className={`text-3xl font-bold tabular-nums ${cor}`}>{valor}</p>
      <p className="text-xs text-slate-500">{rotulo}</p>
    </div>
  )
}

function EditarJogador({
  id,
  nome: nomeAtual,
  rating: ratingAtual,
  fechar,
}: {
  id: number
  nome: string
  rating: number
  fechar: () => void
}) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [nome, setNome] = useState(nomeAtual)
  const [rating, setRating] = useState(ratingAtual)
  const path = { params: { path: { jogador_id: id } } }

  const salvar = useMutation({
    mutationFn: () => ok(api.PATCH('/api/jogadores/{jogador_id}', { ...path, body: { nome: nome.trim(), rating } })),
    onSuccess: () => {
      // nome/rating aparecem em várias telas (lista, ranking, pelada): recarrega tudo
      queryClient.invalidateQueries()
      fechar()
    },
  })
  const apagar = useMutation({
    mutationFn: () => ok(api.DELETE('/api/jogadores/{jogador_id}', path)),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: chaves.jogador(id) })
      queryClient.invalidateQueries({ queryKey: chaves.jogadores })
      navigate('/jogadores', { replace: true })
    },
  })

  function enviar(ev: FormEvent) {
    ev.preventDefault()
    salvar.mutate()
  }

  return (
    <form onSubmit={enviar} className="mb-4 space-y-3 rounded-2xl bg-white p-4">
      <label className="block">
        <span className="mb-1 block text-sm text-slate-600">Nome</span>
        <input
          className="w-full rounded-xl border border-slate-300 px-3 py-3"
          value={nome}
          onChange={(ev) => setNome(ev.target.value)}
          required
        />
      </label>
      <div>
        <span className="mb-1 block text-sm text-slate-600">Rating</span>
        <SeletorRating valor={rating} mudar={setRating} />
      </div>
      {salvar.isError && <Erro erro={salvar.error} />}
      <div className="flex gap-2">
        <Botao type="button" variante="secundario" onClick={fechar}>
          Cancelar
        </Botao>
        <Botao type="submit" className="flex-1" disabled={!nome.trim() || salvar.isPending}>
          {salvar.isPending ? 'Salvando…' : 'Salvar'}
        </Botao>
      </div>

      <hr className="border-slate-200" />
      <Botao
        type="button"
        variante="perigo"
        className="w-full"
        disabled={apagar.isPending}
        onClick={() => window.confirm(`Apagar ${nomeAtual}? Não dá para desfazer.`) && apagar.mutate()}
      >
        Apagar jogador
      </Botao>
      {apagar.isError && <Erro erro={apagar.error} />}
    </form>
  )
}
