/** Regras do sorteio repetidas no front só para mostrar o resumo antes de sortear. */

/** Mesmo cálculo do backend (app/sorteio.py): tamanhos diferem em no máximo 1. */
export function tamanhos(presentes: number, numeroTimes: number, porTime: number): number[] {
  const jogam = Math.min(presentes, numeroTimes * porTime)
  const base = Math.floor(jogam / numeroTimes)
  const resto = jogam % numeroTimes
  return Array.from({ length: numeroTimes }, (_, i) => (i < resto ? base + 1 : base))
}

export function resumoPresenca(presentes: number, numeroTimes: number, porTime: number): string {
  const capacidade = numeroTimes * porTime
  const inicio = `${presentes} ${presentes === 1 ? 'presente' : 'presentes'}`
  if (presentes < numeroTimes) return `${inicio} · precisa de pelo menos ${numeroTimes} para sortear`
  if (presentes > capacidade) {
    const sobram = presentes - capacidade
    return `${inicio} · ${numeroTimes} times de ${porTime} · ${sobram} ${sobram === 1 ? 'vai' : 'vão'} esperar`
  }
  if (presentes === capacidade) return `${inicio} · ${numeroTimes} times completos`
  return `${inicio} · times incompletos (${tamanhos(presentes, numeroTimes, porTime).join(' / ')})`
}
