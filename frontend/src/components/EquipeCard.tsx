import type { EquipeEstado, JogadorPublic } from '../api/client'
import { corEquipe } from '../lib/cores'
import { Rating } from './ui'

/** 1.8333 -> "1,8" */
function formatarMedia(media: number | null): string {
  return media === null ? '–' : media.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
}

/** Cartão de uma equipe com o elenco. Com `onJogador`, cada jogador vira um botão (admin). */
export function EquipeCard({
  equipe,
  porTime,
  rotulo,
  onJogador,
}: {
  equipe: EquipeEstado
  porTime: number
  rotulo?: string
  onJogador?: (jogador: JogadorPublic) => void
}) {
  const cor = corEquipe(equipe.nome)
  return (
    <section className="overflow-hidden rounded-xl bg-white shadow-sm">
      <header className={`px-3 py-2 ${cor.faixa}`}>
        <p className="truncate font-bold">
          {rotulo && <span className="mr-1 opacity-80">{rotulo}</span>}
          {equipe.nome}
        </p>
        <p className="text-xs tabular-nums opacity-90">
          {equipe.jogadores.length}/{porTime} · ★{formatarMedia(equipe.rating_medio)}
        </p>
      </header>
      {equipe.jogadores.length === 0 ? (
        <p className="px-3 py-3 text-sm text-stone-400">Sem jogadores</p>
      ) : (
        <ul className="divide-y divide-stone-100">
          {equipe.jogadores.map((j) => {
            const conteudo = (
              <>
                <span className="truncate">{j.nome}</span>
                <Rating valor={j.rating} />
              </>
            )
            return (
              <li key={j.id}>
                {onJogador ? (
                  <button
                    className="flex min-h-11 w-full items-center justify-between gap-2 px-3 text-left active:bg-stone-100"
                    onClick={() => onJogador(j)}
                  >
                    {conteudo}
                  </button>
                ) : (
                  <div className="flex min-h-11 items-center justify-between gap-2 px-3">{conteudo}</div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
