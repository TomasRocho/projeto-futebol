import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { EVENTO_ADMIN_SAIU, lerChave, salvarChave } from './api/client'

type Admin = {
  ehAdmin: boolean
  /** Valida a chave no servidor e, se estiver certa, entra no modo admin. */
  entrar: (chave: string) => Promise<void>
  sair: () => void
}

const AdminContext = createContext<Admin | null>(null)

export function AdminProvider({ children }: { children: ReactNode }) {
  const [chave, setChave] = useState<string | null>(lerChave)

  // O client da API dispara esse evento quando recebe 401 (chave inválida).
  useEffect(() => {
    const saiu = () => setChave(null)
    window.addEventListener(EVENTO_ADMIN_SAIU, saiu)
    return () => window.removeEventListener(EVENTO_ADMIN_SAIU, saiu)
  }, [])

  async function entrar(nova: string) {
    const r = await fetch('/api/admin/check', { headers: { 'X-API-Key': nova } })
    if (r.status !== 204) throw new Error('Chave inválida')
    salvarChave(nova)
    setChave(nova)
  }

  function sair() {
    salvarChave(null)
    setChave(null)
  }

  return (
    <AdminContext.Provider value={{ ehAdmin: chave !== null, entrar, sair }}>
      {children}
    </AdminContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAdmin(): Admin {
  const ctx = useContext(AdminContext)
  if (!ctx) throw new Error('useAdmin precisa estar dentro de <AdminProvider>')
  return ctx
}
