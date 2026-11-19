import { useIsFetching, useQueryClient } from '@tanstack/react-query'
import { Lock, LockOpen, RefreshCw, Shirt, Trophy, Users, type LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { useAdmin } from '../admin'
import { AdminModal } from './AdminModal'

export function Layout() {
  const { ehAdmin } = useAdmin()
  const [modalAberto, setModalAberto] = useState(false)
  const queryClient = useQueryClient()
  const buscando = useIsFetching() > 0
  const { pathname } = useLocation()

  const abas: { para: string; rotulo: string; icone: LucideIcon; ativa?: boolean }[] = [
    {
      para: '/',
      rotulo: 'Pelada',
      icone: Shirt,
      ativa: pathname === '/' || /^\/(peladas|partidas)/.test(pathname),
    },
    { para: '/ranking', rotulo: 'Ranking', icone: Trophy },
    { para: '/jogadores', rotulo: 'Jogadores', icone: Users },
  ]

  const LockIcone = ehAdmin ? LockOpen : Lock

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-1 bg-marca px-4 py-2.5 text-white">
        <Link to="/" className="flex-1 text-lg font-extrabold tracking-tight">
          ⚽ Pelada
        </Link>
        <button
          className="grid size-10 place-items-center rounded-full active:bg-white/15"
          onClick={() => queryClient.invalidateQueries()}
          aria-label="Atualizar"
          title="Atualizar"
        >
          <RefreshCw size={20} className={buscando ? 'animate-spin' : ''} />
        </button>
        <button
          className={`grid size-10 place-items-center rounded-full active:bg-white/15 ${ehAdmin ? 'bg-white/20' : ''}`}
          onClick={() => setModalAberto(true)}
          aria-label={ehAdmin ? 'Modo admin (ativo)' : 'Entrar como admin'}
          title={ehAdmin ? 'Modo admin' : 'Entrar como admin'}
        >
          <LockIcone size={20} />
        </button>
      </header>

      <main className="flex-1 px-4 pt-4 pb-24">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-xl">
          {abas.map(({ para, rotulo, icone: Icone, ativa }) => (
            <NavLink
              key={para}
              to={para}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-0.5 pt-2 pb-1.5 text-xs font-semibold ${
                  (ativa ?? isActive) ? 'text-marca' : 'text-slate-500'
                }`
              }
            >
              <Icone size={22} />
              {rotulo}
            </NavLink>
          ))}
        </div>
      </nav>

      {modalAberto && <AdminModal fechar={() => setModalAberto(false)} />}
    </div>
  )
}
