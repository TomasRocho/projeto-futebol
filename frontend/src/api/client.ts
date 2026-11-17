/**
 * Client da API, tipado a partir do OpenAPI do FastAPI (schema.d.ts é gerado: `npm run gen:api`).
 */
import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Schemas = components['schemas']
export type PeladaPublic = Schemas['PeladaPublic']
export type PeladaEstado = Schemas['PeladaEstado']
export type EquipeEstado = Schemas['EquipeEstado']
export type JogadorPublic = Schemas['JogadorPublic']
export type PartidaDetalhe = Schemas['PartidaDetalhe']
export type EquipePartida = Schemas['EquipePartida']

// --- API key do admin (localStorage) ---

const CHAVE = 'pelada.apiKey'
export const EVENTO_ADMIN_SAIU = 'pelada:admin-saiu'

export function lerChave(): string | null {
  try {
    return localStorage.getItem(CHAVE)
  } catch {
    return null
  }
}

export function salvarChave(chave: string | null): void {
  try {
    if (chave) localStorage.setItem(CHAVE, chave)
    else localStorage.removeItem(CHAVE)
  } catch {
    // navegador sem storage (aba anônima etc.): o modo admin dura só até recarregar
  }
}

// --- Client ---

export const api = createClient<paths>({ baseUrl: '' })

api.use({
  onRequest({ request }) {
    const chave = lerChave()
    if (chave) request.headers.set('X-API-Key', chave)
    return request
  },
  onResponse({ response }) {
    // Chave errada ou trocada no servidor: sai do modo admin e avisa a interface.
    if (response.status === 401 && lerChave()) {
      salvarChave(null)
      window.dispatchEvent(new Event(EVENTO_ADMIN_SAIU))
    }
    return response
  },
})

// --- Erros ---

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Mensagem legível a partir do corpo de erro do FastAPI. */
function mensagem(erro: unknown, status: number): string {
  const detail = (erro as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg ?? 'valor inválido').join('; ')
  }
  if (status === 401) return 'É preciso entrar no modo admin'
  return `Erro ${status}`
}

/**
 * Desembrulha a resposta do openapi-fetch: devolve `data` ou lança ApiError.
 * Uso: `queryFn: () => ok(api.GET('/api/peladas'))`
 */
export async function ok<T>(
  chamada: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await chamada
  if (!response.ok) throw new ApiError(response.status, mensagem(error, response.status))
  return data as T
}
