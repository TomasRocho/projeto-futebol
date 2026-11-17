/** Data de hoje no fuso do celular, no formato da API (AAAA-MM-DD). */
export function hojeISO(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** "2026-11-14" -> "sáb, 14/11/2026" (sem passar por fuso horário). */
export function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.split('-').map(Number)
  const d = new Date(ano, mes - 1, dia)
  const semana = d.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '')
  return `${semana}, ${String(dia).padStart(2, '0')}/${String(mes).padStart(2, '0')}/${ano}`
}
