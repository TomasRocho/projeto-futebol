import { useState, type FormEvent } from 'react'
import { useAdmin } from '../admin'
import { Sheet } from './Sheet'
import { Botao } from './ui'

export function AdminModal({ fechar }: { fechar: () => void }) {
  const { ehAdmin, entrar, sair } = useAdmin()
  const [chave, setChave] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      await entrar(chave.trim())
      fechar()
    } catch (err) {
      setErro((err as Error).message)
    } finally {
      setEnviando(false)
    }
  }

  if (ehAdmin) {
    return (
      <Sheet titulo="Modo admin" fechar={fechar}>
        <p className="mb-4 text-stone-600">Você pode sortear, lançar gols e encerrar partidas.</p>
        <div className="flex gap-2">
          <Botao variante="secundario" className="flex-1" onClick={fechar}>
            Fechar
          </Botao>
          <Botao
            variante="perigo"
            className="flex-1"
            onClick={() => {
              sair()
              fechar()
            }}
          >
            Sair do modo admin
          </Botao>
        </div>
      </Sheet>
    )
  }

  return (
    <Sheet titulo="Entrar como admin" fechar={fechar}>
      <form onSubmit={enviar}>
        <label className="mb-1 block text-sm text-stone-600" htmlFor="chave">
          API key
        </label>
        <input
          id="chave"
          type="password"
          autoComplete="current-password"
          className="mb-2 w-full rounded-xl border border-stone-300 px-3 py-3"
          value={chave}
          onChange={(e) => setChave(e.target.value)}
          autoFocus
        />
        {erro && <p className="mb-2 text-sm text-red-700">{erro}</p>}
        <div className="mt-2 flex gap-2">
          <Botao type="button" variante="secundario" className="flex-1" onClick={fechar}>
            Cancelar
          </Botao>
          <Botao type="submit" className="flex-1" disabled={!chave.trim() || enviando}>
            {enviando ? 'Conferindo…' : 'Entrar'}
          </Botao>
        </div>
      </form>
    </Sheet>
  )
}
