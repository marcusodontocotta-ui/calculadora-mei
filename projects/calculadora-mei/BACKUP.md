# BACKUP — Calculadora MEI

Roteiro de backup mensal das tabelas `mei_*` no PostgreSQL compartilhado com o SISGERSA.

> **Importante**: o banco é **compartilhado** (`sisgersa`). Este roteiro despeja **somente** as tabelas
> com prefixo `mei_*`. Nunca executar `pg_dump` de banco inteiro nem `DROP`/`TRUNCATE` fora das tabelas `mei_*`.

---

## 1. Situação atual (auditoria em 2026-08-27)

- Nenhum script/estratégia de backup existia no repositório (verificado).
- O serviço não possui `DATABASE_URL` configurada no Render — a aplicação usa uma credencial
  hardcoded em `database.py` (a mesma conexão de app do SISGERSA).
- **Snapshot de validação já executado com sucesso** neste roteiro:
  - Arquivo: `mei_backup_20260827_223630.dump` (formato custom, gzip)
  - Tamanho: 12.630 bytes · SHA256 `B7A8EAE99A17ADC4660527F57E5CAFEAC620285D7467FC88881787C4A784EF34`
  - Conteúdo verificado via `pg_restore --list`: 5 tabelas + sequences + constraints + dados (40 entradas TOC)
  - Servidor: PostgreSQL **18.4** (Debian), host oregon-postgres Render

Dados atuais: `mei_produtos` 0 · `mei_vendas` 0 · `mei_despesas` 0 · `mei_clientes` 1 · `mei_assinaturas` 4.

---

## 2. Pré-requisitos

| Recurso | Onde | Observação |
|---|---|---|
| Docker | máquina local / runner CI | imagem `postgres:18-alpine` (pg_dump 18 = compatível com o servidor 18) |
| `DATABASE_URL` | Render (secret) **ou** valor atual em `database.py` | **nunca** gravar a senha em arquivo versionado |
| Destino do arquivo | disco local, R2/S3, Drive, etc. | ver "Guardas e retenção" |

O `DATABASE_URL` usado pelo app aponta para o banco `sisgersa` no host
`dpg-d9hqikr7uimc73dt3e0g-a.oregon-postgres.render.com` (SSL obrigatório). Define-se por variável de ambiente:

```powershell
$env:DATABASE_URL = "postgresql://USUARIO:SENHA@HOST/BANCO?sslmode=require"
```

---

## 3. Backup manual (com Docker, validado)

Comandos exatos usados na auditoria (formato custom, comprimido, só `mei_*`):

```powershell
# 1) diretório de destino
New-Item -ItemType Directory -Force -Path "C:\backups\mei" | Out-Null

# 2) despeja (pg_dump 18 via container) - usa a string de conexão do $env:DATABASE_URL
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker run --rm `
  -v "C:\backups\mei:/bk" `
  -e "PGPASSWORD=<SENHA>" `
  postgres:18-alpine pg_dump `
    -h "<HOST>" -U "<USUARIO>" -d "<BANCO>" `
    -t "mei_*" --no-owner --no-privileges -Fc `
    -f "/bk/mei_backup_$stamp.dump"

# 3) validação de integridade
docker run --rm -v "C:\backups\mei:/bk" postgres:18-alpine pg_restore --list "/bk/mei_backup_$stamp.dump"
```

Parâmetros explicados:
- `-t "mei_*"` → restringe a dump às tabelas `mei_*` (public). Não toca nas tabelas do SISGERSA.
- `-Fc` → formato custom: comprimido, permite `pg_restore --list`, restauração seletiva.
- `--no-owner --no-privileges` → dump transportável entre usuários/instâncias.
- `pg_dump 18` → necessário porque o servidor é PostgreSQL 18 (cliente mais antigo pode falhar).

### Linux / macOS / CI

```bash
export DATABASE_URL="postgresql://USUARIO:SENHA@HOST/BANCO?sslmode=require"
STAMP=$(date +%Y%m%d_%H%M%S)
docker run --rm -v "$HOME/backups/mei:/bk" -e "DATABASE_URL=$DATABASE_URL" postgres:18-alpine sh -c '
  pg_dump "$DATABASE_URL" -t "mei_*" --no-owner --no-privileges -Fc -f "/bk/mei_backup_'"$STAMP"'.dump"
'
```

---

## 4. Backup automatizado (GitHub Actions, todo dia 1)

Criar `.github/workflows/backup-mei.yml` na raiz do repo (ou em `projects/calculadora-mei/.github/`):

```yaml
name: backup-mei-mensal
on:
  schedule:
    - cron: "0 5 1 * *"   # 1o dia do mes, 05:00 UTC
  workflow_dispatch: {}   # permite disparo manual

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Executa pg_dump (somente mei_*)
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          STAMP=$(date +%Y%m%d_%H%M%S)
          docker run --rm \
            -e "DATABASE_URL=$DATABASE_URL" \
            postgres:18-alpine pg_dump \
              "$DATABASE_URL" -t "mei_*" --no-owner --no-privileges -Fc -f - \
            | gzip > "mei_backup_$STAMP.dump.gz"
          echo "FILE=mei_backup_$STAMP.dump.gz" >> "$GITHUB_ENV"

      - name: Verifica integridade
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          docker run --rm -i -e "DATABASE_URL=$DATABASE_URL" \
            postgres:18-alpine sh -c \
            'gunzip -c - | pg_restore --list - | grep -i "TABLE public mei_" | wc -l'

      - name: Publica artefato
        uses: actions/upload-artifact@v4
        with:
          name: ${{ env.FILE }}
          path: ${{ env.FILE }}
          retention-days: 30

      - name: Upload opcional para R2/S3 (ativa se houver credenciais)
        if: env.AWS_ACCESS_KEY_ID != ''
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_ENDPOINT_URL_S3: ${{ secrets.AWS_ENDPOINT_URL_S3 }}
          BUCKET: ${{ secrets.BACKUP_BUCKET }}
        run: |
          curl -s https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
          unzip -q awscliv2.zip && sudo ./aws/install
          aws s3 cp "$FILE" "s3://$BUCKET/calculadora-mei/$FILE" --endpoint-url "$AWS_ENDPOINT_URL_S3"

      - name: Aviso no Telegram (opcional)
        if: failure() && env.TELEGRAM_BOT_TOKEN != ''
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" -d text="BACKUP MEI FALHOU - $(date)"
```

**Secrets a criar no GitHub** (Settings → Secrets and variables → Actions):
- `DATABASE_URL` (obrigatória)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_ENDPOINT_URL_S3` / `BACKUP_BUCKET` (opcional — R2/S3)
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (opcional)

> Recomendado: depois de rotacionar a senha (ver `DEV_OPS.md`), a `DATABASE_URL` secret do
> GitHub deve ser a mesma do Render.

Alternativa sem GitHub Actions: agendar no Windows o comando da seção 3 (Task Scheduler,
mensal, com tarefa de "run whether user is logged on").

---

## 5. Restauração (teste / recuperação)

Sempre testar em banco separado antes de qualquer uso em produção.

```powershell
# 1) sobe um Postgres temporário
docker run -d --name mei_restore_test -e POSTGRES_PASSWORD=teste -p 5433:5432 postgres:18-alpine

# 2) cria banco alvo
docker exec mei_restore_test psql -U postgres -c "CREATE DATABASE mei_restore OWNER postgres;"

# 3) restaura o dump
docker run --rm -v "C:\backups\mei:/bk" --network host postgres:18-alpine \
  pg_restore --no-owner -d "postgresql://postgres:teste@localhost:5433/mei_restore" "/bk/mei_backup_<STAMP>.dump"

# 4) confere volumes
docker exec mei_restore_test psql -U postgres -d mei_restore -c "
  SELECT 'produtos' t, count(*) FROM mei_produtos
  UNION ALL SELECT 'vendas', count(*) FROM mei_vendas
  UNION ALL SELECT 'despesas', count(*) FROM mei_despesas
  UNION ALL SELECT 'clientes', count(*) FROM mei_clientes
  UNION ALL SELECT 'assinaturas', count(*) FROM mei_assinaturas;"

# 5) limpa
docker rm -f mei_restore_test
```

Para restauração real em produção (indisponibilidade): apontar `DATABASE_URL` do Render para
o banco restaurado ou restaurar no próprio `sisgersa` (apenas tabelas `mei_*`; não afeta SISGERSA).

---

## 6. Guardas e retenção

| Item | Política sugerida |
|---|---|
| Frequência | Mensal (dia 1) + 1 manual antes de mudanças grandes |
| Retenção local | 13 meses (12 mensais + 1 corrente) |
| Retenção offsite (S3/R2/Drive) | 13 meses + 1 cópia anual permanente |
| Guarda segura | Arquivos comprimidos com senha (ex.: `gpg -c`) se houver dados sensíveis |
| Teste | A cada 3 meses: restaurar em banco temporário e conferir contagens (seção 5) |

---

## 7. Segurança

- **Nunca** commitar a `DATABASE_URL` nem a senha em texto plano (há hoje uma credencial hardcoded
  em `database.py` — ver `DEV_OPS.md`, item crítico C1).
- Rodar o backup com a string em variável de ambiente / Secret, nunca em linha de comando visível
  em logs (use `env: DB_URL: ${{ secrets.DATABASE_URL }}` no CI).
- O dump contém dados de clientes/assinaturas → tratar como dado sensível (LGPD).
- Após rotacionar a senha do banco, atualizar: Render (secret), GitHub (secret `DATABASE_URL`),
  e qualquer agendador local.

---

## Checklist mensal

- [ ] Disparou o backup (agendado ou manual)
- [ ] `pg_restore --list` sem erros
- [ ] Arquivo gerado e copiado para o destino offsite
- [ ] Backup antigo (>13 meses) removido
- [ ] (trimestral) Restore de teste na seção 5 executado com sucesso