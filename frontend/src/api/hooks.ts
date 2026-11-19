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

export function usePeladas() {
  return useQuery({ queryKey: chaves.peladas, queryFn: () => ok(api.GET('/api/peladas')) })
}

export function useJogador(id: number) {
  return useQuery({
    queryKey: chaves.jogador(id),
    queryFn: () => ok(api.GET('/api/jogadores/{jogador_id}', { params: { path: { jogador_id: id } } })),
  })
}

export type TipoRanking = 'gols' | 'assistencias' | 'vitorias'

export function useRanking(tipo: TipoRanking, peladaId: number | null) {
  return useQuery({
    queryKey: chaves.ranking(tipo, peladaId),
    queryFn: () =>
      ok(api.GET('/api/ranking', { params: { query: { tipo, pelada_id: peladaId ?? undefined } } })),
  })
}

export function useEstatisticasDaPelada(id: number) {
  return useQuery({
    queryKey: chaves.estatisticasDaPelada(id),
    queryFn: () =>
      ok(api.GET('/api/peladas/{pelada_id}/estatisticas', { params: { path: { pelada_id: id } } })),
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
