# CLAUDE.md — projeto-futebol

API REST para organizar a pelada dos amigos do Tomás (sorteio de times equilibrado, rodízio, placar, estatísticas).

## Fonte da verdade do design
O design fica no vault do Tomás, **fora deste repo**. Leia antes de mexer em modelo ou regra:
- `~/Documents/cerebro/Projetos/Projeto-Futebol/ProjetoFutebol.md`: nota-índice (decisões, "Onde parei", próximos passos)
- `~/Documents/cerebro/Projetos/Projeto-Futebol/Diagrama-Classes.md`: classes e **regras do rodízio, fila e empate**
- `~/Documents/cerebro/Projetos/Projeto-Futebol/Modelo-Relacional.md`: tabelas e SQL (SQLite)
- `~/Documents/cerebro/Projetos/Projeto-Futebol/Endpoints-API.md`: rotas

Se o código precisar divergir do design, avise e atualize a nota correspondente. Não deixe os dois desalinhados.

## Ao abrir uma sessão
Leia o "Onde parei" da nota-índice e me lembre em 2–3 linhas onde paramos.

## Ao fim de cada sessão de trabalho
Adicione uma linha datada (`- AAAA-MM-DD: ...`) no **"Onde parei"** da nota-índice, dizendo o que foi feito e qual é o próximo passo. Decisões novas vão em **"Decisões"**.
No vault: **nunca apague** nada (proponha mover para `~/Documents/cerebro/Arquivo/` e espere o ok). Nomes de arquivo sem acento, com hífen.

## Stack
- Python, FastAPI, SQLModel, SQLite (migrar para PostgreSQL depois)
- SQLite: ligar `PRAGMA foreign_keys = ON` **em toda conexão** (event listener no engine). Sem isso, as FKs do modelo não valem.
- Admin único: escrita protegida por header `X-API-Key`, leitura pública.

## Como responder
- Português, termos técnicos em inglês.
- Direto e informal, curto por padrão.
- Se eu estiver errado, diga. Não invente fatos técnicos.
