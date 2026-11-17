import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from './chaves'
import { api, ok, type PeladaEstado } from './client'

export function usePeladaEstado(id: number) {
  return useQuery({
    queryKey: chaves.pelada(id),
    queryFn: () => ok(api.GET('/api/peladas/{pelada_id}', { params: { path: { pelada_id: id } } })),
  })
}

export function useJogadores() {
  return useQuery({ queryKey: chaves.jogadores, queryFn: () => ok(api.GET('/api/jogadores')) })
}

export function usePartidasDaPelada(id: number, enabled = true) {
  return useQuery({
    queryKey: chaves.partidasDaPelada(id),
    queryFn: () =>
      ok(api.GET('/api/peladas/{pelada_id}/partidas', { params: { path: { pelada_id: id } } })),
    enabled,
  })
}

export function usePartida(id: number) {
  return useQuery({
    queryKey: chaves.partida(id),
    queryFn: () => ok(api.GET('/api/partidas/{partida_id}', { params: { path: { partida_id: id } } })),
  })
}

/**
 * Ação que devolve o novo estado da pelada (presenças, sorteio, encerrar):
 * grava o estado direto no cache, sem precisar de outro GET.
 */
export function useAcaoNaPelada<V = void>(peladaId: number, acao: (vars: V) => Promise<PeladaEstado>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: acao,
    onSuccess: (estado) => {
      queryClient.setQueryData(chaves.pelada(peladaId), estado)
      queryClient.invalidateQueries({ queryKey: chaves.partidasDaPelada(peladaId) })
    },
  })
}
