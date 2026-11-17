import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router'
import { chaves } from '../api/chaves'
import { api, ok } from '../api/client'
import { Carregando, Erro } from '../components/ui'
import { hojeISO } from '../lib/datas'

/** "/" leva direto para a pelada de hoje; se não tiver, para a lista de peladas. */
export function Inicio() {
  const peladas = useQuery({ queryKey: chaves.peladas, queryFn: () => ok(api.GET('/api/peladas')) })

  if (peladas.isPending) return <Carregando />
  if (peladas.isError) return <Erro erro={peladas.error} tentarDeNovo={() => peladas.refetch()} />

  const hoje = peladas.data.find((p) => p.data === hojeISO())
  return <Navigate to={hoje ? `/peladas/${hoje.id}` : '/peladas'} replace />
}
