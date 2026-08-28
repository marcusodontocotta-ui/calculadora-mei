# Relatório de Estética & UX — Calculadora MEI

**Autor:** Equipe de Avaliação de Estética e UX
**Data:** 27/08/2026
**Produto avaliado (live):** https://calculadora-mei.onrender.com
**Arquivos:** `templates/index.html`, `static/style.css`, `static/app.js`, `templates/termos.html`, `templates/privacidade.html`
**Escopo:** Somente auditoria e recomendações (nenhum código alterado).

---

## 1. Notas por área (0–10)

| Área | Nota | Destaque principal |
|---|---|---|
| Hero / mensagem em 3s | 6,5 | CTA visível, mas a promessa não é objetiva |
| Hierarquia visual, tipografia, cores | 8,0 | Boa paleta verde/azul, Inter bem aplicada |
| Estrutura e ordem das seções | 6,0 | Produto completo no meio da landing = ruído |
| Velocidade percebida / assets | 6,5 | QR-code lib pesada carregada sempre |
| Responsividade / mobile | 4,5 | **Sem navegação e sem login no mobile** |
| Acessibilidade básica | 5,5 | Modais sem ARIA, ícones como texto, foco ausente |
| Fluxo cadastro/login (modal) | 6,5 | Funciona, mas usa `alert()` e sem focus-trap |
| Formulários das abas (feedback) | 6,0 | Erros/sucesso via `alert()`, não inline |
| Checkout PRO | 6,0 | Exige login antes de pagar; sem garantia/urgência |
| Consistência entre páginas | 7,0 | Rodapé da home aponta para `#`; deploy defasado |
| Psicologia de preço (PRO R$9,90) | 6,5 | Badge OK, falta urgência/garantia/ancoragem real |
| **Média geral** | **6,3** | Base sólida, fragilidade em mobile e conversão |

---

## 2. Diagnóstico por área

### 2.1 Landing / Hero
- **Mensagem em 3s:** O H1 entrega **3 promessas** ("DAS simplificado, alertas automáticos, lucro controlado") — multiclaim que não é lido de primeira. A proposta de valor real (prever vencimento / evitar multa) fica diluída. Nota 6,5.
- **Contradição de preço:** CTA primário "Começar Grátis" exibe logo ao lado "de R$ 149,90 por **R$ 9,90/mês**". O usuário não entende se é grátis ou pago. Isso confunde na hora crítica da ação.
- **CTA:** visível e bem estilizado (verde forte). Bom.
- **Social proof fraco:** badge "22 milhões de MEIs" não é prova do produto (é dado de mercado), não gera confiança.

### 2.2 Hierarquia, espaços, tipografia, cores
- Pontos fortes: `Inter` com pesos bem graduados, contraste verde (#16a34a) coerente, seções com padding consistente via `clamp()`, sombras suaves e cards bem espaçados.
- Fraco: excesso de `bg verde claro` (#dcfce7) repetido em cards de contextos diferentes (step, comparação, destaque) reduz a diferenciação semântica.

### 2.3 Seções (dor, como funciona, educação, comparação, preços, FAQ)
- **"Como funciona"** e **"Comparativo"**: objetivas e eficientes.
- **Educação** (details/accordion): muito longa e técnica na landing ("Na lei...", tabela de formatos). É conteúdo bom, mas empurra a conversão para baixo.
- **Problema estrutural:** A seção **"Meus Ganhos"** (a suíte completa: Produtos, Vendas, Despesas, Resumo, Limite, Clientes) está **no meio da landing**, antes de "Dor" e da própria "Calculadora DAS" gratuita. Isso:
  - insere um dashboard inteiro e complexo numa página que deveria converter;
  - esconde o recurso gratuito (calculadora) que é o motor de conversão;
  - dobra a landing num manual de produto.
- FAQ está ok, mas é repetitivo com a educação.

### 2.4 Velocidade percebida
- Carrega **Google Fonts** e **html5-qrcode (via unpkg)** no `<head>` de **todas** as visitas. A lib de QR (~200KB+) só é usada no escaneamento de produtos (recurso PRO/avançado). Em mobile (3G/4G) isso pesa.
- Não há lazy-load de imagens; fotos de produto são data-URI base64 inline (foto capturada fica salva no form).

### 2.5 Responsividade / mobile (crítico)
- As MEIs acessam majoritariamente pelo celular, e o site **perde recursos essenciais nesse form factor**:
  - `@media (max-width:768px)` aplica `.nav-links { display: none }` **sem hambúrguer substituto**. Logo: no mobile **não há menu**, e — pior — os botões **"Entrar" e "Criar conta"** estão **dentro** de `.nav-links`, então ficam **invisíveis**. Usuário mobile não consegue logar/cadastrar pelo header.
  - Phone mockup some (`hero-visual{display:none}`) — ok, relação de imagem é perdida.
  - Grids (steps, pain, pricing) colapsam bem — pontos positivos.
- Nota 4,5 reflete esse bloqueio real de conversão mobile.

### 2.6 Acessibilidade básica
- Labels sem `for` (vários `<label>` sem referência) → leitor de tela frágil.
- Ícones são **caracteres de texto** (`!`, `$`, `>`, `@`, `#`, `*`) com cores, não ícones semânticos; sem `aria-hidden`/texto alternativo.
- Botões "X" (delete, close) sem `aria-label`.
- Modais sem `role="dialog"`, `aria-modal`, **focus-trap nem fechamento por ESC** — acessibilidade por teclado prejudicada.
- Contraste: `--gray-500 #6b7280` sobre `#f9fafb` é limítrofe (~4,6:1) para texto pequeno.

### 2.7 Fluxo cadastro/login (modal) e checkout PRO
- Modal de login/cadastro funcional com tabs; feedback de erro aparece inline (`setAuthMessage`), bom.
- Porém sucessos usam **`alert()`** nativos (popup do navegador) — feio, bloqueante e inconsistente com a estética.
- **Checkout PRO** exige **login antes de pagar** (`assinarPro`/`iniciarAssinatura` checam token antes do checkout). O usuário que quer só pagar é freado por um formulário de conta. Fricção direta de conversão.
- O botão "Assinar" da pricing e da seção PRO no live pede e-mail; o repositório local já tem nome+e-mail — diferença de deploy (ver §2.10).

### 2.8 Consistência entre páginas (/, /termos, /privacidade)
- /termos e /privacidade usam a mesma navbar/stylesheet, com layout "legal-page" limpo e legível. Boa coerência.
- **Rodapé da home:** links "Termos de Uso", "Política de Privacidade", "Contato" apontam para **`#`** — quebrados/inertes (deveriam ir a `/termos`, `/privacidade`).
- Texto dos termos difere entre local (2026, mais robusto) e o que está **no ar** (2025, mais curto) → **deploy defasado**; o usuário vê a versão antiga.

### 2.9 Psicologia do preço (PRO R$ 9,90)
- **Convence parcialmente.** Boa comparação "93% mais barato que contador" e anchor "de R$149,90".
- **Faltam** elementos clássicos de conversão:
  - Garantia (ex.: "7 dias de garantia ou seu dinheiro de volta");
  - Urgência/escassez (não há nada de tempo/limite);
  - Prova social/avaliações/testemunhais;
  - Opção anual (R$9,90×12 vs "pague R$99/ano" melhora percepção de economia);
  - O card "Contador R$150+" como 3ª coluna enfraquece o anchor do hero (R$149,90 vs R$150+).
- A promessa "Comece Grátis, pague só se precisar" é boa, mas não é acompanhada de um gatilho claro pós-teste.

### 2.10 Nota sobre deploy
Recomendações abaixo assumem re-deploy. Alguns itens já corrigidos no código local (ex.: termos robustos, checkout nome+e-mail) ainda não estão no ar — sinal de que a **contagem de conversão deve ser validada após o deploy mais recente**.

---

## 3. Melhorias priorizadas (impacto × esforço)

### P0 — Bloqueadores (alta prioridade)

| # | Melhoria | Justificativa |
|---|---|---|
| P0-1 | **Adicionar menu hambúrguer no mobile e reexpor "Entrar/Criar conta"** | Hoje `.nav-links` some em <768px sem substituto e os botões de auth ficam invisíveis. MEIs móveis não logam. UX bloqueante de receita. |
| P0-2 | **Corrigir rodapé da home:** links reais para `/termos` e `/privacidade` (hoje `#`) | Infra de trust/legal quebrada; indica descuido e afeta conversão (confiança) e conformidade LGPD. |
| P0-3 | **Mover a seção "Meus Ganhos" (suite completa) para fora da landing** (ex.: página/dashboard pós-login) e deixar a calculadora DAS como foco | Landing inchada com dashboard complexo no meio desvia do objetivo de conversão e empurra o recurso grátis (calculadora) para baixo. |

### P1 — Alto impacto, esforço moderado

| # | Melhoria | Justificativa |
|---|---|---|
| P1-1 | **Substituir `alert()` por feedback inline/toast** em cadastro, login, produtos, vendas, despesas, clientes e checkout | `alert()` nativo é bloqueante e destoa da estética; quebra a continuidade do fluxo. |
| P1-2 | **Carregar `html5-qrcode` de forma assíncrona (defer) e só quando necessário** | Lib pesada (~200KB) baixa em toda visita; atrasa a percepção no celular. |
| P1-3 | **Adicionar gatilhos de preço:** garantia de 7 dias + selo de "pagamento seguro"; considerar opção anual | Urgência/garantia são os maiores alavancas de conversão ausentes na seção PRO. |
| P1-4 | **Permitir checkout PRO sem exigir login/cadastro completo primeiro** (manter apenas e-mail), e pedir cadastro depois do pagamento | Elimina fricção no ponto decisivo; login pode virar reforço pós-conversão. |
| P1-5 | **Ajustar o H1** para uma **única promessa** com sub-linha de apoio, e remover a contradição "Grátis × R$9,90/mês" do hero | Clareza em 3s = maior retenção; hoje o head de conversão está ambiguo. |
| P1-6 | **Mobile: reexibir o phone-mockup** (ou resumo visual) em telas médias | Mantém a história/conexão emocional que hoje desaparece no mobile. |

### P2 — Qualidade, baixo esforço

| # | Melhoria | Justificativa |
|---|---|---|
| P2-1 | Adicionar `for`/`id` nos labels e `aria-label` em botões "X"; `role="dialog"`, `aria-modal`, focus-trap e ESC nos modais | Eleva acessibilidade por teclado/leitor de tela. |
| P2-2 | Reduzir contraste do cinza (usar `--gray-500` só em texto grande; `#4b5563` abaixo disso) | Conformidade WCAG AA. |
| P2-3 | Servir ícones semânticos (SVG) no lugar de `! $ > @ # *` | Semântica + consistência visual em todas as densidades. |
| P2-4 | Revisar a 3ª coluna de preços ("Contador R$150+") para não canibalizar o anchor do hero | Evita precificação confusa na mesma tela. |
| P2-5 | Dividir a seção de educação "Na lei"/tabela para uma subpágina ou colapso opcional | Landing mais leve e focada na ação. |
| P2-6 | Sincronizar deploy (termos/privacidade/checkout locais × o que está no ar) | Evita divergência de conteúdo legal e de UX percebida pelos usuários. |

---

## 4. As 5 mudanças de maior ganho imediato de conversão

1. **Restaurar o acesso a login/cadastro no mobile (hambúrguer)** — destrava o funil inteiro no dispositivo mais usado pelas MEIs. *(P0-1)*
2. **Mover o dashboard "Meus Ganhos" para fora da landing** e promover a Calculadora DAS gratuita como protagonista, com CTA imediato. *(P0-3)*
3. **Desbloquear o checkout PRO com apenas o e-mail** (sem exigir conta completa antes), adicionando **garantia de 7 dias + selo de segurança**. *(P1-3 + P1-4)*
4. **Trocar `alert()` por feedback inline** nos formulários e **deferir o html5-qrcode** — fluxos contínuos + carregamento rápido no mobile. *(P1-1 + P1-2)*
5. **Reescrever o H1 para uma única promessa e corrigir a contradição Grátis × R$ 9,90/mês** — clareza no primeiro frame reduz abandono e eleva o clique no CTA. *(P1-5)*

> Ordem sugerida de execução: P0-1 → P0-3 → P1-4/P1-3 → P1-1/P1-2 → P1-5, revalidando conversão A/B a cada etapa após o deploy correto.
