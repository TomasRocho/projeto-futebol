import { useEffect, type ReactNode } from 'react'

/** Painel que sobe de baixo no celular (modal centralizado em tela grande). Fecha no fundo ou no Esc. */
export function Sheet({
  titulo,
  fechar,
  children,
}: {
  titulo?: string
  fechar: () => void
  children: ReactNode
}) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && fechar()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [fechar])

  return (
    <div className="fixed inset-0 z-20 flex items-end bg-black/40 sm:items-center" onClick={fechar}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="max-h-[85dvh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:mx-auto sm:max-w-sm sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-2">
          <h2 className="text-lg font-bold">{titulo}</h2>
          <button
            className="-mt-1 -mr-2 grid size-10 shrink-0 place-items-center rounded-full text-xl text-stone-500 active:bg-stone-100"
            onClick={fechar}
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
