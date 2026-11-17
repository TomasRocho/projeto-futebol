/** Peças pequenas de interface reaproveitadas pelas telas. */
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function Carregando() {
  return <p className="py-10 text-center text-stone-500">Carregando…</p>
}

export function Erro({ erro, tentarDeNovo }: { erro: Error; tentarDeNovo?: () => void }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
      <p>{erro.message}</p>
      {tentarDeNovo && (
        <button className="mt-2 font-semibold underline" onClick={tentarDeNovo}>
          Tentar de novo
        </button>
      )}
    </div>
  )
}

export function Titulo({ children }: { children: ReactNode }) {
  return <h1 className="mb-4 text-2xl font-bold">{children}</h1>
}

type BotaoProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: 'primario' | 'secundario' | 'perigo'
}

/** Botão grande (dedo, não mouse). */
export function Botao({ variante = 'primario', className = '', ...props }: BotaoProps) {
  const cores = {
    primario: 'bg-green-700 text-white active:bg-green-800',
    secundario: 'bg-white text-stone-800 border border-stone-300 active:bg-stone-100',
    perigo: 'bg-red-600 text-white active:bg-red-700',
  }[variante]
  return (
    <button
      className={`min-h-12 rounded-xl px-4 font-semibold disabled:opacity-50 ${cores} ${className}`}
      {...props}
    />
  )
}

/** Rating de 0 a 5 em botões grandes. */
export function SeletorRating({ valor, mudar }: { valor: number; mudar: (n: number) => void }) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Rating">
      {[0, 1, 2, 3, 4, 5].map((n) => (
        <button
          type="button"
          key={n}
          role="radio"
          aria-checked={valor === n}
          onClick={() => mudar(n)}
          className={`min-h-11 flex-1 rounded-lg border font-semibold ${
            valor === n ? 'border-green-700 bg-green-700 text-white' : 'border-stone-300 bg-white'
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  )
}

export function Rating({ valor }: { valor: number | null | undefined }) {
  return <span className="text-sm text-stone-400 tabular-nums">★{valor ?? '–'}</span>
}

export function Subtitulo({ children }: { children: ReactNode }) {
  return <h2 className="mt-6 mb-2 text-sm font-semibold tracking-wide text-stone-500 uppercase">{children}</h2>
}

export function EmConstrucao({ titulo }: { titulo: string }) {
  return (
    <>
      <Titulo>{titulo}</Titulo>
      <p className="text-stone-500">Tela em construção.</p>
    </>
  )
}
