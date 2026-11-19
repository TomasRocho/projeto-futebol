import { useState } from 'react'
import { Dices } from 'lucide-react'
import { useAdmin } from '../../admin'
import { api, ok, type PeladaEstado } from '../../api/client'
import { useAcaoNaPelada, useJogadores } from '../../api/hooks'
import { NovoJogadorRapido } from '../../components/NovoJogadorRapido'
import { Botao, Carregando, Erro, Rating, Subtitulo } from '../../components/ui'
import { resumoPresenca } from '../../lib/pelada'

/** Antes do sorteio: quem veio. Todos os presentes ainda estão "esperando" (sem equipe). */
export function FasePresenca({ estado }: { estado: PeladaEstado }) {
  const { ehAdmin } = useAdmin()
  const presentes = estado.esperando

  if (ehAdmin) {
    // key: quando o servidor devolve outra lista, o checklist recomeça a partir dela
    return <ChecklistPresenca key={presentes.map((j) => j.id).join(',')} estado={estado} />
  }

  return (
    <>
      <p className="rounded-2xl bg-white p-4 text-slate-600">
        Aguardando o sorteio ·{' '}
        {resumoPresenca(presentes.length, estado.numero_times, estado.jogadores_por_time)}
      </p>
      <Subtitulo>Presentes</Subtitulo>
      {presentes.length === 0 ? (
        <p className="text-slate-500">Ninguém marcado ainda.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {presentes.map((j) => (
            <li key={j.id} className="rounded-full bg-white px-3 py-1.5">
              {j.nome}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function ChecklistPresenca({ estado }: { estado: PeladaEstado }) {
  const peladaId = estado.id
  const jogadores = useJogadores()
  const salvos = new Set(estado.esperando.map((j) => j.id))
  const [marcados, setMarcados] = useState(() => new Set(salvos))

  const mudou = marcados.size !== salvos.size || [...marcados].some((id) => !salvos.has(id))
  const path = { params: { path: { pelada_id: peladaId } } }

  const salvar = useAcaoNaPelada(peladaId, (ids: number[]) =>
    ok(api.PUT('/api/peladas/{pelada_id}/presencas', { ...path, body: { jogador_ids: ids } })),
  )
  const sortear = useAcaoNaPelada(peladaId, () => ok(api.POST('/api/peladas/{pelada_id}/sorteio', path)))

  function alternar(id: number) {
    setMarcados((atual) => {
      const novo = new Set(atual)
      if (novo.has(id)) novo.delete(id)
      else novo.add(id)
      return novo
    })
  }

  const podeSortear = marcados.size >= estado.numero_times
  const erro = salvar.error ?? sortear.error

  return (
    <>
      <div className="space-y-3 rounded-2xl bg-white p-4">
        <p className="font-semibold">
          {resumoPresenca(marcados.size, estado.numero_times, estado.jogadores_por_time)}
        </p>
        {mudou ? (
          <div className="flex gap-2">
            <Botao variante="secundario" onClick={() => setMarcados(new Set(salvos))}>
              Desfazer
            </Botao>
            <Botao className="flex-1" disabled={salvar.isPending} onClick={() => salvar.mutate([...marcados])}>
              {salvar.isPending ? 'Salvando…' : 'Salvar presença'}
            </Botao>
          </div>
        ) : (
          <Botao className="w-full" disabled={!podeSortear || sortear.isPending} onClick={() => sortear.mutate()}>
            {sortear.isPending ? 'Sorteando…' : <><Dices size={20} /> Sortear times</>}
          </Botao>
        )}
        {erro && <Erro erro={erro} />}
      </div>

      <Subtitulo>Quem veio?</Subtitulo>
      {jogadores.isPending && <Carregando />}
      {jogadores.isError && <Erro erro={jogadores.error} tentarDeNovo={() => jogadores.refetch()} />}
      {jogadores.data && (
        <ul className="divide-y divide-slate-100 overflow-hidden rounded-2xl bg-white">
          {jogadores.data.map((j) => (
            <li key={j.id}>
              <label className="flex min-h-12 cursor-pointer items-center gap-3 px-4 active:bg-slate-50">
                <input
                  type="checkbox"
                  className="size-5 accent-marca"
                  checked={marcados.has(j.id)}
                  onChange={() => alternar(j.id)}
                />
                <span className="flex-1">{j.nome}</span>
                <Rating valor={j.rating} />
              </label>
            </li>
          ))}
          {jogadores.data.length === 0 && (
            <li className="px-4 py-3 text-slate-500">Nenhum jogador cadastrado ainda.</li>
          )}
        </ul>
      )}
      <div className="mt-3">
        <NovoJogadorRapido onCriado={(j) => setMarcados((atual) => new Set(atual).add(j.id))} />
      </div>
    </>
  )
}
