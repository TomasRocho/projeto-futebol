import { useIsFetching, useQueryClient } from '@tanstack/react-query'
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

  const abas = [
    { para: '/', rotulo: 'Pelada', ativa: pathname === '/' || /^\/(peladas|partidas)/.test(pathname) },
    { para: '/ranking', rotulo: 'Ranking' },
    { para: '/jogadores', rotulo: 'Jogadores' },
  ]

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-2 bg-green-700 px-4 py-3 text-white">
        <Link to="/" className="flex-1 text-lg font-bold">
          ⚽ Pelada
        </Link>
        <button
          className="grid size-10 place-items-center rounded-full text-xl active:bg-green-800"
          onClick={() => queryClient.invalidateQueries()}
          aria-label="Atualizar"
          title="Atualizar"
        >
          <span className={buscando ? 'animate-spin' : ''}>↻</span>
        </button>
        <button
          className={`grid size-10 place-items-center rounded-full text-xl active:bg-green-800 ${ehAdmin ? 'bg-yellow-400/30' : ''}`}
          onClick={() => setModalAberto(true)}
          aria-label={ehAdmin ? 'Modo admin (ativo)' : 'Entrar como admin'}
          title={ehAdmin ? 'Modo admin' : 'Entrar como admin'}
        >
          {ehAdmin ? '🔓' : '🔒'}
        </button>
      </header>

      <main className="flex-1 px-4 pt-4 pb-24">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto flex max-w-xl">
          {abas.map((aba) => (
            <NavLink
              key={aba.para}
              to={aba.para}
              className={({ isActive }) =>
                `flex-1 py-4 text-center font-semibold ${
                  (aba.ativa ?? isActive) ? 'text-green-700' : 'text-stone-500'
                }`
              }
            >
              {aba.rotulo}
            </NavLink>
          ))}
        </div>
      </nav>

      {modalAberto && <AdminModal fechar={() => setModalAberto(false)} />}
    </div>
  )
}
