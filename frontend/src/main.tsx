import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { AdminProvider } from './admin'
import { ApiError } from './api/client'
import { Layout } from './components/Layout'
import { EmConstrucao, Titulo } from './components/ui'
import './index.css'
import { Inicio } from './pages/Inicio'
import { Peladas } from './pages/Peladas'
import { PeladaPage } from './pages/pelada/PeladaPage'

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
      { path: 'peladas/:id/estatisticas', element: <EmConstrucao titulo="Estatísticas do dia" /> },
      { path: 'partidas/:id', element: <EmConstrucao titulo="Partida" /> },
      { path: 'ranking', element: <EmConstrucao titulo="Ranking" /> },
      { path: 'jogadores', element: <EmConstrucao titulo="Jogadores" /> },
      { path: 'jogadores/:id', element: <EmConstrucao titulo="Jogador" /> },
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
