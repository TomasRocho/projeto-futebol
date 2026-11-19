/**
 * Chaves do cache do TanStack Query, num lugar só.
 * ['pelada', id, ...] fica "dentro" de ['pelada', id]: invalidar a pelada recarrega as partidas dela também.
 */
export const chaves = {
  peladas: ['peladas'] as const,
  pelada: (id: number) => ['pelada', id] as const,
  partidasDaPelada: (id: number) => ['pelada', id, 'partidas'] as const,
  estatisticasDaPelada: (id: number) => ['pelada', id, 'estatisticas'] as const,
  partida: (id: number) => ['partida', id] as const,
  jogadores: ['jogadores'] as const,
  jogador: (id: number) => ['jogadores', id] as const,
  ranking: (tipo: string, peladaId: number | null) => ['ranking', tipo, peladaId] as const,
}
