import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { AdminProvider } from './admin'
import { ApiError } from './api/client'
import { Layout } from './components/Layout'
import { Titulo } from './components/ui'
import './index.css'
import { EstatisticasPelada } from './pages/EstatisticasPelada'
import { Inicio } from './pages/Inicio'
import { Jogador } from './pages/Jogador'
import { Jogadores } from './pages/Jogadores'
import { Partida } from './pages/Partida'
import { Peladas } from './pages/Peladas'
import { PeladaPage } from './pages/pelada/PeladaPage'
import { Ranking } from './pages/Ranking'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Sem atualização automática: o botão ↻ do topo recarrega (decisão em Telas-Frontend).
      refetchOnWindowFocus: false,
      // Erro 4xx (404, 401...) não melhora tentando de novo; só falha de rede/servidor.
      retry: (tentativas, erro) => !(erro instanceof ApiError && erro.status < 500) && tentativas < 1,
    },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Inicio /> },
      { path: 'peladas', element: <Peladas /> },
      { path: 'peladas/:id', element: <PeladaPage /> },
      { path: 'peladas/:id/estatisticas', element: <EstatisticasPelada /> },
      { path: 'partidas/:id', element: <Partida /> },
      { path: 'ranking', element: <Ranking /> },
      { path: 'jogadores', element: <Jogadores /> },
      { path: 'jogadores/:id', element: <Jogador /> },
      { path: '*', element: <Titulo>Página não encontrada</Titulo> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AdminProvider>
        <RouterProvider router={router} />
      </AdminProvider>
    </QueryClientProvider>
  </StrictMode>,
)
