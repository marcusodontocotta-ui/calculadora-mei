# Auditoria Final de Estética/UX — Calculadora MEI

**Build:** 817387c · **Ambiente:** produção https://calculadora-mei.onrender.com
**Equipe:** Estética/UX · **Modo:** somente leitura/report (nenhum código alterado)
**Data:** 27/08/2026

Permissão de escopo: avaliação via `webfetch` da landing de produção + leitura local de `templates/index.html`, `templates/termos.html`, `templates/privacidade.html`, `static/style.css`, `static/app.js`, `calculadora.py` e `QA_PRODUCAO.md`.

---

## Achados por área

### 1. Mobile & Hambúrguer — ⭐ 9/10
**Status geral: implementado e funcional.**
- `index.html:34` — botão hambúrguer existe: `<button type="button" class="nav-toggle" id="navToggle" aria-label="Abrir menu" aria-expanded="false">` com 3 spans.
- `style.css:2055-2077` (`@media max-width:768px`) — `.nav-links { display:none }` e `.nav-links.ativo { display:flex }`. Correto.
- `app.js:25-39,84-86` — `toggleMenu()` alterna `.ativo`, atualiza `aria-expanded`, fecha ao clicar num link. Bom a11y do toggle.
- Login visível no mobile: `.nav-links .nav-user { flex-wrap:wrap }` (`style.css:2079`) mantém "Entrar/Criar conta" dentro do menu. Resolvido.
- Navbar é `position: sticky/fixed` (menu dropdown `top:100%`), então o menu abre sobre o conteúdo sem quebra de layout.

> **Nota:** webfetch não permite interação de clique, então a abertura real foi validada pela lógica JS/CSS (robusta). Risco residual baixo — apenas não testado em device físico real.

### 2. Hero — ⭐ 8.5/10
- Promessa clara no H1: "Seu DAS simplificado, seus alertas automáticos, seu lucro controlado." (`index.html:51`).
- Subtitle com benefício quantificado: "economiza R$ 150/mes de contador" (`:52`).
- **CTA acima da dobra:** "Começar Grátis" (`btn-primary btn-lg`, `:57`) com anchor de preço "de R$ 149,90 por R$ 9,90/mes" (`:58-60`).
- Visual com mockup de celular mostrando "FALTAM 7 DIAS / R$ 86,05 / DAS de Agosto" — reforça a proposta (alerta + valor correto).
- Badge "22 milhões de MEIs no Brasil" dá contexto social.

> Resíduo: o anchor "de R$ 149,90" convive com o card "Contador R$ 150+" na seção de preços (mesma tela) — leve dissonância de precificação, não bloqueante.

### 3. Seção de Preços — ⭐ 8/10
- **Contradição "Grátis × R$ 9,90/mes" removida.** A hierarquia agora é coerente: card **Gratis R$ 0 / para sempre** ↔ card **PRO R$ 9,90 / por mês** (`index.html:1029-1056`). Não há mais texto de comparação contraditório.
- **Selo "Garantia de 7 dias"** presente: `badge-garantia` "Garantia de 7 dias - reembolso garantido" (`index.html:1108`).
- **Selo "Pagamento 100% seguro com Mercado Pago"** presente em dois pontos do checkout (`:1131` `pro-seguro` + `:1132` `pro-legal`).
- Card "Contador R$ 150+" como 3ª coluna é didático, mas continua enfraquecendo o anchor do hero (PRESERVADO do achado antigo — ver P1-2).

### 4. Checkout PRO — ⭐ 8.5/10
- Campos claros: e-mail (`proEmail`, `:1115`) + cupom (`cupomInput`, `:1122`).
- **Feedback de cupom inline, sem `alert`:** `cupomStatus` (`:1127`) é preenchido por `aplicarCupom()` (`app.js:1387-1423`) com mensagens de sucesso/erro/validação reais ("Cupom aplicado: -X% = R$ Y", "Cupom inválido", "Entre na sua conta para usar um cupom").
- E-mail validado via `/api/validar-email` (`app.js:1440`) com torsões: `mostrarToast` para faltas (`:1433`). Sem `alert()`.
- Fluxo amarra conta antes de assinar — correto para cobrança recorrente.
- Toast substituiu `alert()` globalmente (`app.js:11-21`, `.toast` no CSS).

### 5. FAQ / Valores de DAS — ⭐ 9.5/10
- **Corrigido de forma completa.** FAQ "Quanto custa o DAS?" agora traz `Serviços: R$ 86,05 / Comércio: R$ 82,05 / Misto: R$ 87,05` (`index.html:1156`).
- Sem mais "R$ 150/225 de DAS" em lugar nenhum; o único "R$ 150" restante é corretamente o **preço do contador** (não do DAS).
- Backend alinhado: `calculadora.py`/`QA_PRODUCAO.md` confirmam 86,05 / 82,05 / 87,05; mockup do hero e simulador de eficiência também usam 86,05 (`app.js:597`).
- Consistência cruzada cuidada (hero + FAQ + eficiência + tabela + API).

### 6. Landing: dashboard empurrando a calculadora — ⭐ 4/10 ❗
- **Achado antigo NÃO corrigido.** A seção **"Meus Ganhos"** (a suíte completa com dashboard `resumoDashboard`, Produtos, Vendas, Despesas, Resumo, Limite, Clientes) continua **no meio da landing** (`index.html:586`), **antes** de "Dor" (`:828`), "Comparativo" (`:862`) e, principalmente, **antes** da própria **Calculadora DAS gratuita** (`id="app"`, `:911`).
- Impacto: o dashboard complexo aparece antes do recurso gratuito protagonista, desvia a atenção e empurra o CTA de conversão (a calculadora) para baixo — contradiz o funil "calcule grátis → assine PRO".
- Este é o único achado de alto impacto que **permanece integralmente aberto** da auditoria anterior (P0-3 / "mover Meus Ganhos para fora da landing").

### 7. Consistência /termos e /privacidade — ⭐ 8/10
- Ambos reutilizam `style.css` + um bloco `<style>` `.legal-page` quase idêntico (navbar, layout 800-820px, tipografia, `.update`). Estilo consistente.
- Pequenas divergências:
  - `termos.html:35` data "27 de agosto de **2026**" vs `privacidade.html:32` "26 de agosto de **2025**" (datas de atualização divergentes).
  - Copyright no rodapé: `index.html:1202` e `privacidade.html:82` = "**2025**", `termos.html:154` = "**2026**".
  - `privacidade.html:35,39` afirma "**NÃO coleta, armazena ou transmite dados pessoais**" — **potencial contradição** com o checkout PRO que coleta e-mail para assinatura/cobrança (ver P1-3).
- Rodapé da landing (principal ponto de contato) com links reais `/termos` `/privacidade` `mailto:contato@...` (`index.html:1196-1198`) — implementado corretamente.

### 8. Acessibilidade básica — ⭐ 7.5/10
- **Contraste:** bom. Verde primário `#16a34a` sobre branco ≈ 4.8:1; texto principal `#111827` sobre branco ≈ 15:1. O `--gray-500 (#6b7280)` ≈ 4.6:1 é aceitável para corpo, mas **tenso para texto pequeno** (placeholders, `form-hint`, `price-period`, `card-sub`).
- **Alt:** o único `<img>` (foto/preview, `index.html` + `app.js`) tem `alt="Preview"` adequado. O restante da UI é texto/ícone — sem imagens sem alt faltando.
- **toggle:** `aria-expanded` atualizado e `aria-label="Abrir menu"` — bom.
- **Faltas menores:** `<meta description>` ok; não há `<html lang>` errado (pt-BR correto); não validei foco de teclado/`aria-controls` no toggle nem labels de `.navbar a` (mas inputs usam `label for` corretamente).

---

## Notas finais por área

| Área | Nota (0-10) |
|---|---|
| Mobile & Hambúrguer | 9.0 |
| Hero (promessa + CTA above the fold) | 8.5 |
| Seção de Preços (garantia + MP + coerência) | 8.0 |
| Checkout PRO (email/cupom inline) | 8.5 |
| FAQ / Valores de DAS | 9.5 |
| Landing (dashboard empurra calculadora) | 4.0 |
| Consistência /termos e /privacidade | 8.0 |
| Acessibilidade básica | 7.5 |
| **MÉDIA GERAL** | **7.9** |

---

## Melhorias prioritárias restantes (P0/P1/P2)

| Prio | Ação | Aceite | Impacto / Justificativa |
|---|---|---|---|
| **P0-1** | **Mover a seção "Meus Ganhos" (dashboard completo) para fora da landing** (dashboard/área pós-login) e promover a Calculadora DAS gratuita como protagonista, com CTA imediato | Calculadora `#app` antes da suíte; landing com foco em conversão | Único achado alto aberto: o dashboard no meio empurra o recurso grátis (a calculadora) para baixo e dilui a mensagem de conversão. Maior impacto de UX na tela principal. |
| **P1-2** | **Revisar a 3ª coluna de preços "Contador R$ 150+"** que convive com o anchor de R$ 149,90 do hero | Precificação coerente na mesma viewport | Enfraquece o anchor e confunde o leitor: "de R$ 149,90" vs "R$ 150+". Custo baixo, clareza comercial imediata. |
| **P1-3** | **Corrigir a contradição da Política de Privacidade** ("não coletamos dados pessoais") vs o checkbox PRO que coleta e-mail/assinatura | Texto alinhado ao fluxo de assinatura Mercado Pago | Risco de LGPD/desconfiança: declaração legal falsa pode gerar problema jurídico e minar credibilidade. |
| **P2-4** | **Aplicar contraste maior em textos small-caption** (`--gray-500` em placeholders/`form-hint`/`card-sub`/`price-period`) | Passar de ~4.6:1 para ≥7:1 em texto <14px | Conforto de leitura e conformidade WCAG AA; baixo custo (só ajustar variável/tokens). |
| **P2-5** | **Unificar datas/copyright de /termos e /privacidade** (e alinhar ao rodapé da landing) | mesma data e ano nos 3 lugares | Consistência de confiança legal/editorial; hoje há 2025 vs 2026 misturados entre páginas. |

---

## Veredito final

**Nota geral: 7.9 / 10** — "Pronto para lançamento com 1 ressalva de alto impacto".

As melhorias do build 817387c foram **efetivamente aplicadas e corretas na produção**: hambúrguer + login no mobile (funcionais por código), toast no lugar de `alert()`, rodapé com links reais, selos de Garantia de 7 dias e Mercado Pago, checkout PRO com e-mail+cupom com feedback inline, e — principalmente — **a correção completa dos valores de DAS** (86,05 / 82,05 / 87,05, sem mais "R$ 150/225") e **a remoção da contradição "Grátis × R$ 9,90/mes"** nos preços.

**Top 3 achados:**
1. 🔴 **P0-1 — "Meus Ganhos" (dashboard) continua no meio da landing empurrando a calculadora DAS para baixo** — único achado de alto impacto ainda aberto.
2. 🟡 **P1-3 — Política de Privacidade contradiz o fluxo de assinatura** ("não coletamos dados pessoais" vs e-mail/MP do PRO) — risco legal/LGPD.
3. 🟢 **P1-2/P2 — Refinamentos:** 3ª coluna "Contador R$150+" vs anchor R$149,90; contraste de textos small; datas/copyright divergentes entre /termos e /privacidade.

Recomendação: **liberar** para produção a partir da estética/UX, priorizando **P0-1** (mover o dashboard) na próxima sprint — é o que mais muda a percepção da landing.
