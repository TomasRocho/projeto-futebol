/** Cores das equipes = cores dos coletes (nomes vêm do sorteio: Azul, Vermelho, Verde, Amarelo). */

type Cor = { faixa: string; texto: string; ponto: string }

const CORES: Record<string, Cor> = {
  Azul: { faixa: 'bg-blue-600 text-white', texto: 'text-blue-700', ponto: 'bg-blue-600' },
  Vermelho: { faixa: 'bg-red-600 text-white', texto: 'text-red-700', ponto: 'bg-red-600' },
  Verde: { faixa: 'bg-green-600 text-white', texto: 'text-green-700', ponto: 'bg-green-600' },
  Amarelo: { faixa: 'bg-yellow-400 text-slate-900', texto: 'text-yellow-700', ponto: 'bg-yellow-400' },
}

const PADRAO: Cor = { faixa: 'bg-slate-600 text-white', texto: 'text-slate-700', ponto: 'bg-slate-500' }

export function corEquipe(nome: string): Cor {
  return CORES[nome] ?? PADRAO
}
