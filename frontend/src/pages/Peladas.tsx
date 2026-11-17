import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAdmin } from '../admin'
import { chaves } from '../api/chaves'
import { api, ok } from '../api/client'
import { Botao, Carregando, Erro, Titulo } from '../components/ui'
import { formatarData, hojeISO } from '../lib/datas'

export function Peladas() {
  const { ehAdmin } = useAdmin()
  const peladas = useQuery({ queryKey: chaves.peladas, queryFn: () => ok(api.GET('/api/peladas')) })
  const [criando, setCriando] = useState(false)

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <Titulo>Peladas</Titulo>
        {ehAdmin && !criando && <Botao onClick={() => setCriando(true)}>+ Nova</Botao>}
      </div>

      {criando && <NovaPelada cancelar={() => setCriando(false)} />}

      {peladas.isPending && <Carregando />}
      {peladas.isError && <Erro erro={peladas.error} tentarDeNovo={() => peladas.refetch()} />}
      {peladas.data?.length === 0 && (
        <p className="py-10 text-center text-stone-500">
          Nenhuma pelada ainda.{!ehAdmin && ' Entre no modo admin (🔒) para criar.'}
        </p>
      )}

      <ul className="space-y-2">
        {peladas.data?.map((p) => (
          <li key={p.id}>
            <Link
              to={`/peladas/${p.id}`}
              className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm active:bg-stone-50"
            >
              <span className="font-semibold">{formatarData(p.data)}</span>
              <span className="text-sm text-stone-500">
                {p.data === hojeISO() && (
                  <span className="mr-2 rounded-full bg-green-100 px-2 py-0.5 font-semibold text-green-800">
                    Hoje
                  </span>
                )}
                {p.numero_times} times de {p.jogadores_por_time}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  )
}

function NovaPelada({ cancelar }: { cancelar: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [data, setData] = useState(hojeISO())
  const [numeroTimes, setNumeroTimes] = useState(2)
  const [porTime, setPorTime] = useState<6 | 7>(6)

  const criar = useMutation({
    mutationFn: () =>
      ok(
        api.POST('/api/peladas', {
          body: { data, numero_times: numeroTimes, jogadores_por_time: porTime },
        }),
      ),
    onSuccess: (pelada) => {
      queryClient.invalidateQueries({ queryKey: chaves.peladas })
      navigate(`/peladas/${pelada.id}`)
    },
  })

  function enviar(e: FormEvent) {
    e.preventDefault()
    criar.mutate()
  }

  const opcao = (ativo: boolean) =>
    `flex-1 min-h-12 rounded-xl border font-semibold ${
      ativo ? 'border-green-700 bg-green-700 text-white' : 'border-stone-300 bg-white'
    }`

  return (
    <form onSubmit={enviar} className="mb-6 space-y-4 rounded-xl bg-white p-4 shadow-sm">
      <label className="block">
        <span className="mb-1 block text-sm text-stone-600">Data</span>
        <input
          type="date"
          required
          className="w-full rounded-xl border border-stone-300 px-3 py-3"
          value={data}
          onChange={(e) => setData(e.target.value)}
        />
      </label>

      <fieldset>
        <legend className="mb-1 text-sm text-stone-600">Número de times</legend>
        <div className="flex gap-2">
          {[2, 3, 4].map((n) => (
            <button type="button" key={n} className={opcao(numeroTimes === n)} onClick={() => setNumeroTimes(n)}>
              {n}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-1 text-sm text-stone-600">Jogadores por time</legend>
        <div className="flex gap-2">
          {([6, 7] as const).map((n) => (
            <button type="button" key={n} className={opcao(porTime === n)} onClick={() => setPorTime(n)}>
              {n}
            </button>
          ))}
        </div>
      </fieldset>

      {criar.isError && <Erro erro={criar.error} />}

      <div className="flex gap-2">
        <Botao type="button" variante="secundario" className="flex-1" onClick={cancelar}>
          Cancelar
        </Botao>
        <Botao type="submit" className="flex-1" disabled={criar.isPending}>
          {criar.isPending ? 'Criando…' : 'Criar pelada'}
        </Botao>
      </div>
    </form>
  )
}
