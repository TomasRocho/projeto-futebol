import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { chaves } from '../api/chaves'
import { api, ok, type JogadorPublic } from '../api/client'
import { Botao, Erro, SeletorRating } from './ui'

/** Cadastro rápido de jogador novo (alguém apareceu pela primeira vez na pelada). */
export function NovoJogadorRapido({ onCriado }: { onCriado: (jogador: JogadorPublic) => void }) {
  const queryClient = useQueryClient()
  const [aberto, setAberto] = useState(false)
  const [nome, setNome] = useState('')
  const [rating, setRating] = useState(3)

  const criar = useMutation({
    mutationFn: () => ok(api.POST('/api/jogadores', { body: { nome: nome.trim(), rating } })),
    onSuccess: (jogador) => {
      queryClient.invalidateQueries({ queryKey: chaves.jogadores })
      onCriado(jogador)
      setNome('')
      setRating(3)
      setAberto(false)
    },
  })

  function enviar(e: FormEvent) {
    e.preventDefault()
    criar.mutate()
  }

  if (!aberto) {
    return (
      <button className="min-h-11 w-full font-semibold text-green-700" onClick={() => setAberto(true)}>
        + Cadastrar jogador novo
      </button>
    )
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-xl border border-stone-200 bg-stone-50 p-3">
      <input
        placeholder="Nome"
        className="w-full rounded-xl border border-stone-300 bg-white px-3 py-3"
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        autoFocus
        required
      />
      <SeletorRating valor={rating} mudar={setRating} />
      {criar.isError && <Erro erro={criar.error} />}
      <div className="flex gap-2">
        <Botao type="button" variante="secundario" className="flex-1" onClick={() => setAberto(false)}>
          Cancelar
        </Botao>
        <Botao type="submit" className="flex-1" disabled={!nome.trim() || criar.isPending}>
          Cadastrar
        </Botao>
      </div>
    </form>
  )
}
