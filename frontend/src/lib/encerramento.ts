import type { PartidaDetalhe, PeladaEstado } from '../api/client'

/** "Ana", "Ana e Bia", "Ana, Bia e Caio" */
function lista(nomes: string[]): string {
  return nomes.length <= 1 ? nomes.join('') : `${nomes.slice(0, -1).join(', ')} e ${nomes.at(-1)}`
}

const plural = (n: number, um: string, varios: string) => (n > 1 ? varios : um)

/**
 * Explica o que aconteceu ao encerrar: resultado e o que o rodízio mudou.
 * Compara o estado da pelada antes e depois (o backend é quem aplica a regra).
 */
export function resumoEncerramento(
  antes: PeladaEstado,
  depois: PeladaEstado,
  partida: PartidaDetalhe,
  penaltis: { a: number; b: number } | null,
): string[] {
  const linhas: string[] = []
  const { equipe_a: a, equipe_b: b } = partida

  if (a.gols !== b.gols) {
    const [v, p] = a.gols > b.gols ? [a, b] : [b, a]
    linhas.push(`${v.nome} venceu ${v.gols} x ${p.gols}.`)
  } else if (penaltis) {
    const vencedor = penaltis.a > penaltis.b ? a.nome : b.nome
    const [maior, menor] = [Math.max(penaltis.a, penaltis.b), Math.min(penaltis.a, penaltis.b)]
    linhas.push(`${a.gols} x ${b.gols}: ${vencedor} venceu nos pênaltis (${maior} x ${menor}).`)
  } else {
    linhas.push(`Empate em ${a.gols} x ${b.gols}.`)
  }

  const emQuadra = (e: PeladaEstado) => e.equipes.filter((q) => q.ordem_fila === null).map((q) => q.nome)
  const saiu = emQuadra(antes).filter((n) => !emQuadra(depois).includes(n))
  const entrou = emQuadra(depois).filter((n) => !emQuadra(antes).includes(n))
  if (saiu.length > 0) {
    linhas.push(
      `${lista(saiu)} ${plural(saiu.length, 'vai', 'vão')} para a fila · ` +
        `${lista(entrou)} ${plural(entrou.length, 'entra', 'entram')}.`,
    )
  }

  const esperavam = new Set(antes.esperando.map((j) => j.id))
  for (const equipe of depois.equipes) {
    const vieram = equipe.jogadores.filter((j) => esperavam.has(j.id)).map((j) => j.nome)
    if (vieram.length > 0) {
      linhas.push(`${lista(vieram)} ${plural(vieram.length, 'entrou', 'entraram')} no ${equipe.nome}.`)
    }
  }
  const foram = depois.esperando.filter((j) => !esperavam.has(j.id)).map((j) => j.nome)
  if (foram.length > 0) linhas.push(`${lista(foram)} ${plural(foram.length, 'foi', 'foram')} esperar.`)

  return linhas
}
