import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAdmin } from '../admin'
import { useJogadores } from '../api/hooks'
import { NovoJogadorRapido } from '../components/NovoJogadorRapido'
import { Carregando, Erro, Rating, Titulo } from '../components/ui'

export function Jogadores() {
  const { ehAdmin } = useAdmin()
  const navigate = useNavigate()
  const jogadores = useJogadores()
  const [busca, setBusca] = useState('')

  // busca sem acento e sem diferenciar maiúscula ("joao" acha "João")
  const normalizar = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  const filtrados = jogadores.data?.filter((j) => normalizar(j.nome).includes(normalizar(busca)))

  return (
    <>
      <Titulo>Jogadores</Titulo>

      {ehAdmin && (
        <div className="mb-4">
          <NovoJogadorRapido onCriado={(j) => navigate(`/jogadores/${j.id}`)} />
        </div>
      )}

      <input
        type="search"
        placeholder="Buscar jogador"
        className="mb-3 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
      />

      {jogadores.isPending && <Carregando />}
      {jogadores.isError && <Erro erro={jogadores.error} tentarDeNovo={() => jogadores.refetch()} />}
      {filtrados?.length === 0 && (
        <p className="py-6 text-center text-slate-500">
          {busca ? 'Ninguém com esse nome.' : 'Nenhum jogador cadastrado ainda.'}
        </p>
      )}

      {filtrados && filtrados.length > 0 && (
        <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white">
          {filtrados.map((j) => (
            <li key={j.id}>
              <Link
                to={`/jogadores/${j.id}`}
                className="flex min-h-12 items-center justify-between gap-2 px-4 active:bg-slate-50"
              >
                <span className="truncate">{j.nome}</span>
                <Rating valor={j.rating} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {jogadores.data && (
        <p className="mt-2 text-center text-xs text-slate-400">{jogadores.data.length} jogadores</p>
      )}
    </>
  )
}
