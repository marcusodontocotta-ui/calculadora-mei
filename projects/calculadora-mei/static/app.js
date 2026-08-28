/* Calculadora MEI - JavaScript Completo */
const TOKEN_KEY = 'mei_token';
let userState = {
    token: localStorage.getItem(TOKEN_KEY) || null,
    usuario: null,
    autenticado: false
};
let pollPlanoTimer = null;
let cupomAtivo = null;

function mostrarToast(msg, tipo) {
    const tipoClasse = tipo === 'erro' ? 'toast-erro' : (tipo === 'sucesso' ? 'toast-sucesso' : 'toast-info');
    const toast = document.createElement('div');
    toast.className = 'toast ' + tipoClasse;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('mostrar'));
    setTimeout(() => {
        toast.classList.remove('mostrar');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function toggleMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');
    if (!toggle || !menu) return;
    const aberto = menu.classList.toggle('ativo');
    toggle.classList.toggle('ativo', aberto);
    toggle.setAttribute('aria-expanded', aberto ? 'true' : 'false');
}

function fecharMenu() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');
    if (!toggle || !menu) return;
    menu.classList.remove('ativo');
    toggle.classList.remove('ativo');
    toggle.setAttribute('aria-expanded', 'false');
}

document.addEventListener('DOMContentLoaded', () => {
    const agora = new Date();
    document.getElementById('mes').value = agora.getMonth() + 1;
    document.getElementById('ano').value = agora.getFullYear();

    // Data padrao para venda = hoje
    const venData = document.getElementById('venData');
    if (venData) venData.value = agora.toISOString().split('T')[0];

    carregarDashboard();
    carregarProdutos();
    carregarResumoMes();
    carregarDespesas();
    carregarLimiteAnual();
    carregarClientes();
    carregarClientesSelect();
    carregarAniversariantes();
    tratarRetornoPagamento();
    verificarSessao();

    // Cliente Form
    const formCliente = document.getElementById('formCliente');
    if (formCliente) {
        formCliente.addEventListener('submit', async (e) => {
            e.preventDefault();
            await cadastrarCliente();
        });
    }

    // Tab navigation principal
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
        });
    });

    // Menu hamburguer mobile
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    if (navToggle) navToggle.addEventListener('click', toggleMenu);
    if (navMenu) {
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', fecharMenu);
        });
    }

    // Earnings tabs
    document.querySelectorAll('.earnings-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.earnings-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.earnings-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`earningstab-${tab.dataset.earningstab}`).classList.add('active');
        });
    });

    // DAS Form
    document.getElementById('formDAS').addEventListener('submit', async (e) => {
        e.preventDefault();
        await calcularDAS();
    });

    // Simular button
    document.getElementById('btnSimular').addEventListener('click', simularCenarios);

    // Produto Form
    const formProduto = document.getElementById('formProduto');
    if (formProduto) {
        formProduto.addEventListener('submit', async (e) => {
            e.preventDefault();
            await cadastrarProduto();
        });
    }

    // Venda Form
    const formVenda = document.getElementById('formVenda');
    if (formVenda) {
        formVenda.addEventListener('submit', async (e) => {
            e.preventDefault();
            await registrarVenda();
        });
    }

    // Despesa Form
    const formDespesa = document.getElementById('formDespesa');
    if (formDespesa) {
        formDespesa.addEventListener('submit', async (e) => {
            e.preventDefault();
            await registrarDespesa();
        });
        // Data padrao = hoje
        const despData = document.getElementById('despData');
        if (despData) despData.value = agora.toISOString().split('T')[0];
        // Mes de filtro = mes atual
        const filtroMes = document.getElementById('filtroDespesaMes');
        if (filtroMes) filtroMes.value = agora.getMonth() + 1;
    }

    // Atualizar total da venda ao mudar valor ou quantidade
    const venValor = document.getElementById('venValor');
    const venQtd = document.getElementById('venQuantidade');
    if (venValor) venValor.addEventListener('input', atualizarTotalVenda);
    if (venQtd) venQtd.addEventListener('input', atualizarTotalVenda);

    // Quando selecionar produto, preencher valor
    const venProduto = document.getElementById('venProduto');
    if (venProduto) {
        venProduto.addEventListener('change', (e) => {
            const option = e.target.options[e.target.selectedIndex];
            const preco = option.dataset.preco;
            if (preco) {
                document.getElementById('venValor').value = preco;
                atualizarTotalVenda();
            }
        });
    }

    // Efficiency gauge
    const btnEff = document.getElementById('btnEfficiency');
    if (btnEff) btnEff.addEventListener('click', calcularEficiencia);

    // Autenticacao
    const btnAbrirLogin = document.getElementById('btnAbrirLogin');
    const btnAbrirCadastro = document.getElementById('btnAbrirCadastro');
    const btnCloseAuth = document.getElementById('btnCloseAuth');
    const btnSair = document.getElementById('btnSair');
    const authLoginForm = document.getElementById('authLoginForm');
    const authCadastroForm = document.getElementById('authCadastroForm');
    const authModal = document.getElementById('authModal');

    if (btnAbrirLogin) btnAbrirLogin.addEventListener('click', () => abrirModalAuth('login'));
    if (btnAbrirCadastro) btnAbrirCadastro.addEventListener('click', () => abrirModalAuth('cadastro'));
    if (btnCloseAuth) btnCloseAuth.addEventListener('click', fecharModalAuth);
    if (btnSair) btnSair.addEventListener('click', logout);
    if (authLoginForm) authLoginForm.addEventListener('submit', async (e) => { e.preventDefault(); await login(); });
    if (authCadastroForm) authCadastroForm.addEventListener('submit', async (e) => { e.preventDefault(); await cadastro(); });

    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => switchAuthTab(tab.dataset.authtab));
    });

    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target === authModal) fecharModalAuth();
        });
    }
});

// ═══════════════════════════════════════════════════════════════════════════
// AUTENTICACAO
// ═══════════════════════════════════════════════════════════════════════════

const HTML_BLOQUEIO_LOGIN = '<div class="empty-state">Entre na sua conta para acessar seus dados.<br><button type="button" class="btn btn-primary btn-sm" onclick="abrirModalAuth(\'login\')">Entrar / Criar conta</button></div>';

async function apiFetch(url, options) {
    const opts = options || {};
    const headers = Object.assign({}, opts.headers || {});
    if (userState.token) {
        headers['Authorization'] = 'Bearer ' + userState.token;
    }
    const resp = await fetch(url, Object.assign({}, opts, { headers }));
    if (resp.status === 401) {
        const tinhaSessao = !!(userState.token || userState.usuario);
        setUserDeslogado();
        const ehEndpointConta = url.indexOf('/api/auth/') === 0 || url === '/api/plano';
        const metodo = (opts.method || 'GET').toUpperCase();
        if (!ehEndpointConta && (tinhaSessao || metodo !== 'GET')) {
            mostrarToast('Faça login para continuar', 'info');
            abrirModalAuth('login');
        }
    }
    return resp;
}

function setUserDeslogado() {
    userState.token = null;
    userState.usuario = null;
    userState.autenticado = false;
    localStorage.removeItem(TOKEN_KEY);
    atualizarNavbar();
}

function exigirLogin() {
    abrirModalAuth('login');
    mostrarToast('Faça login para continuar', 'info');
    return false;
}

function atualizarNavbar() {
    const navDeslogado = document.getElementById('navDeslogado');
    const navAutenticado = document.getElementById('navAutenticado');
    const nomeEl = document.getElementById('navUserName');
    if (!navDeslogado || !navAutenticado) return;

    if (userState.autenticado && userState.usuario) {
        navDeslogado.style.display = 'none';
        navAutenticado.style.display = 'flex';
        if (nomeEl) nomeEl.textContent = userState.usuario.nome || userState.usuario.email || '';
    } else {
        navDeslogado.style.display = 'flex';
        navAutenticado.style.display = 'none';
        if (nomeEl) nomeEl.textContent = '';
    }
}

function preencherCheckout() {
    const inputEmail = document.getElementById('proEmail');
    if (inputEmail && userState.usuario && userState.usuario.email && !inputEmail.value) {
        inputEmail.value = userState.usuario.email;
    }
}

function atualizarUI() {
    atualizarNavbar();
    preencherCheckout();
    verificarPlano();
}

function pintarBloqueioLoginTudo() {
    ['listaProdutos', 'listaVendas', 'listaDespesas', 'listaClientes', 'listaAniversarios'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = HTML_BLOQUEIO_LOGIN;
    });
    const selectProd = document.getElementById('venProduto');
    if (selectProd) selectProd.innerHTML = '<option value="">Faça login para ver produtos</option>';
    const selectCli = document.getElementById('venCliente');
    if (selectCli) selectCli.innerHTML = '<option value="">Cliente nao cadastrado</option>';
}

function carregarDadosAutenticados() {
    carregarDashboard();
    carregarProdutos();
    carregarVendasMes();
    carregarResumoMes();
    carregarDespesas();
    carregarLimiteAnual();
    carregarClientes();
    carregarClientesSelect();
    carregarAniversariantes();
}

async function verificarSessao() {
    if (!userState.token) {
        atualizarNavbar();
        verificarPlano();
        return;
    }
    try {
        const resp = await apiFetch('/api/auth/me');
        if (resp.status === 401) {
            verificarPlano();
            return;
        }
        const data = await resp.json();
        if (data.autenticado && data.usuario) {
            userState.usuario = data.usuario;
            userState.autenticado = true;
            atualizarNavbar();
        }
        verificarPlano();
    } catch (error) {
        console.error('Erro ao verificar sessao:', error);
        verificarPlano();
    }
}

function abrirModalAuth(tab, mensagem) {
    const modal = document.getElementById('authModal');
    if (!modal) return;
    if (tab) switchAuthTab(tab);
    if (mensagem) setAuthMessage(mensagem, 'info');
    modal.style.display = 'flex';
}

function fecharModalAuth() {
    const modal = document.getElementById('authModal');
    if (modal) modal.style.display = 'none';
    setAuthMessage('', '');
}

function switchAuthTab(tab) {
    const isLogin = tab === 'login';
    const loginForm = document.getElementById('authLoginForm');
    const cadForm = document.getElementById('authCadastroForm');
    if (loginForm) loginForm.style.display = isLogin ? 'block' : 'none';
    if (cadForm) cadForm.style.display = isLogin ? 'none' : 'block';
    document.querySelectorAll('.auth-tab').forEach(b => {
        b.classList.toggle('active', b.dataset.authtab === tab);
    });
    const title = document.getElementById('authModalTitle');
    if (title) title.textContent = isLogin ? 'Acesse sua conta' : 'Crie sua conta';
    setAuthMessage('', '');
}

function setAuthMessage(msg, tipo) {
    const el = document.getElementById('authMessage');
    if (!el) return;
    if (msg) {
        el.textContent = msg;
        el.className = 'auth-message ' + (tipo === 'erro' ? 'erro' : 'info');
        el.style.display = 'block';
    } else {
        el.textContent = '';
        el.style.display = 'none';
    }
}

async function cadastro() {
    const nome = document.getElementById('authCadNome').value.trim();
    const email = document.getElementById('authCadEmail').value.trim();
    const senha = document.getElementById('authCadSenha').value;

    if (!nome || !email || !senha) {
        setAuthMessage('Preencha todos os campos.', 'erro');
        return;
    }
    if (senha.length < 6) {
        setAuthMessage('A senha deve ter pelo menos 6 caracteres.', 'erro');
        return;
    }

    try {
        const resp = await fetch('/api/auth/cadastro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, senha })
        });
        const data = await resp.json();
        if (resp.ok && data.token) {
            localStorage.setItem(TOKEN_KEY, data.token);
            userState.token = data.token;
            userState.usuario = data.usuario || null;
            userState.autenticado = true;
            fecharModalAuth();
            atualizarUI();
            carregarDadosAutenticados();
            mostrarToast('Conta criada com sucesso. Bem-vindo(a)!', 'sucesso');
        } else {
            setAuthMessage(data.detail || data.motivo || data.mensagem || 'Erro ao criar conta. Tente novamente.', 'erro');
        }
    } catch (error) {
        console.error('Erro no cadastro:', error);
        setAuthMessage('Erro de conexao. Tente novamente.', 'erro');
    }
}

async function login() {
    const email = document.getElementById('authLoginEmail').value.trim();
    const senha = document.getElementById('authLoginSenha').value;

    if (!email || !senha) {
        setAuthMessage('Preencha e-mail e senha.', 'erro');
        return;
    }

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, senha })
        });
        const data = await resp.json();
        if (resp.ok && data.token) {
            localStorage.setItem(TOKEN_KEY, data.token);
            userState.token = data.token;
            userState.usuario = data.usuario || null;
            userState.autenticado = true;
            fecharModalAuth();
            atualizarUI();
            carregarDadosAutenticados();
            mostrarToast('Login realizado com sucesso. Bem-vindo(a)!', 'sucesso');
        } else {
            setAuthMessage(data.detail || data.motivo || data.mensagem || 'E-mail ou senha incorretos.', 'erro');
        }
    } catch (error) {
        console.error('Erro no login:', error);
        setAuthMessage('Erro de conexao. Tente novamente.', 'erro');
    }
}

async function logout() {
    try {
        if (userState.token) {
            await apiFetch('/api/auth/logout', { method: 'POST' });
        }
    } catch (error) {
        console.error('Erro ao sair:', error);
    }
    setUserDeslogado();
    pintarBloqueioLoginTudo();
    atualizarUI();
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════

async function carregarDashboard() {
    try {
        const resp = await apiFetch('/api/dashboard');
        const data = await resp.json();

        if (resp.status === 401) return;

        if (data.sucesso) {
            const alerta = data.alerta;
            const cardAlerta = document.getElementById('cardAlerta');

            document.getElementById('alertaValor').textContent =
                alerta.dias_restantes > 0 ? `${alerta.dias_restantes} dias` : 'VENCIDO!';
            document.getElementById('alertaSub').textContent = alerta.mensagem;

            if (alerta.nivel === 'critico' || alerta.nivel === 'vencido') {
                const headerAlert = document.getElementById('headerAlert');
                if (headerAlert) {
                    headerAlert.style.display = 'block';
                    document.getElementById('headerAlertIcon').textContent =
                        alerta.nivel === 'vencido' ? '!' : '!!';
                    document.getElementById('headerAlertText').textContent = alerta.mensagem;
                }
                cardAlerta.classList.add(alerta.nivel === 'vencido' ? 'danger' : 'warning');
            }
        }
    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// CALCULAR DAS
// ═══════════════════════════════════════════════════════════════════════════

async function calcularDAS() {
    const mes = parseInt(document.getElementById('mes').value);
    const ano = parseInt(document.getElementById('ano').value);
    const faturamento = parseFloat(document.getElementById('faturamento').value);
    const tipoAtividade = document.getElementById('tipoAtividade').value;

    try {
        const resp = await apiFetch('/api/calcular-das', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mes, ano, faturamento, tipo_atividade: tipoAtividade })
        });

        const data = await resp.json();

        if (data.sucesso) {
            const r = data.resultado;
            document.getElementById('resINSS').textContent = `R$ ${r.componentes.inss.toFixed(2).replace('.', ',')}`;
            document.getElementById('resTotal').textContent = r.total_formatado;
            document.getElementById('resVencimento').textContent = `dia ${r.data_vencimento.split('/')[0]}`;
            document.getElementById('resDias').textContent =
                r.dias_ate_vencer > 0 ? `${r.dias_ate_vencer} dias` : 'VENCIDO!';
            document.getElementById('resTeto').textContent = r.dentro_do_teto ? 'SIM' : 'NAO';
            document.getElementById('resTeto').className = `value ${r.dentro_do_teto ? 'status-dentro' : 'status-fora'}`;
            document.getElementById('resNFE').textContent = r.pode_emitir_nfe ? 'SIM' : 'NAO';

            const lblICMS = document.getElementById('lblICMS_ISS');
            const valICMS = document.getElementById('resICMS_ISS');
            if (tipoAtividade === 'comercio') {
                lblICMS.textContent = 'ICMS';
                valICMS.textContent = `R$ ${r.componentes.icms.toFixed(2).replace('.', ',')}`;
            } else if (tipoAtividade === 'servico') {
                lblICMS.textContent = 'ISS';
                valICMS.textContent = `R$ ${r.componentes.iss.toFixed(2).replace('.', ',')}`;
            } else {
                lblICMS.textContent = 'ICMS + ISS';
                valICMS.textContent = `R$ ${(r.componentes.icms + r.componentes.iss).toFixed(2).replace('.', ',')}`;
            }

            const alertaBox = document.getElementById('alertaCalculo');
            const alerta = r.alerta;
            alertaBox.style.display = 'flex';
            alertaBox.className = `alert-box ${alerta.nivel}`;
            document.getElementById('alertaCalculoIcon').textContent =
                alerta.nivel === 'ok' ? 'OK' :
                alerta.nivel === 'info' ? 'i' :
                alerta.nivel === 'alerta' ? '!' :
                alerta.nivel === 'critico' ? '!!' : 'X';
            document.getElementById('alertaCalculoText').textContent = alerta.mensagem;

            document.getElementById('resultadoDAS').style.display = 'block';
        }
    } catch (error) {
        console.error('Erro ao calcular DAS:', error);
        mostrarToast('Erro ao calcular. Verifique os dados e tente novamente.', 'erro');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SIMULAR CENARIOS
// ═══════════════════════════════════════════════════════════════════════════

async function simularCenarios() {
    const cards = document.querySelectorAll('.cenario-card');
    const cenarios = [];

    cards.forEach((card) => {
        cenarios.push({
            nome: card.querySelector('h3').textContent,
            faturamento_mensal: parseFloat(card.querySelector('.cenario-fat').value) || 0,
            custos_fixos: parseFloat(card.querySelector('.cenario-fixos').value) || 0,
            custos_variaveis_pct: parseFloat(card.querySelector('.cenario-var').value) || 0,
            meses: 12
        });
    });

    try {
        const resp = await apiFetch('/api/simular', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cenarios })
        });

        const data = await resp.json();

        if (data.sucesso) {
            const tbody = document.getElementById('tabelaResultados');
            tbody.innerHTML = '';

            data.resultados.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${r.nome}</strong></td>
                    <td>${r.faturamento_anual_fmt}</td>
                    <td>${r.das_anual_fmt}</td>
                    <td><strong>${r.lucro_liquido_fmt}</strong></td>
                    <td>${r.margem}%</td>
                    <td>${r.roi_meses !== null ? r.roi_meses + ' meses' : 'N/A'}</td>
                    <td class="${r.dentro_teto ? 'status-dentro' : 'status-fora'}">
                        ${r.dentro_teto ? 'Dentro do teto' : 'Fora do teto!'}
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('resultadoSimulacao').style.display = 'block';
        }
    } catch (error) {
        console.error('Erro na simulacao:', error);
        mostrarToast('Erro ao simular. Verifique os dados.', 'erro');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EFICIENCIA
// ═══════════════════════════════════════════════════════════════════════════

function calcularEficiencia() {
    const fat = parseFloat(document.getElementById('effFat').value) || 0;
    const fixos = parseFloat(document.getElementById('effFixos').value) || 0;
    const das = 86.05;
    const variaveis = fat * 0.2;
    const lucro = fat - fixos - das - variaveis;
    const margem = fat > 0 ? (lucro / fat * 100) : 0;
    const eficiencia = Math.min(100, Math.max(0, margem * 2.5));

    document.getElementById('effFatVal').textContent = `R$ ${fat.toLocaleString('pt-BR')}`;
    document.getElementById('effFixVal').textContent = `R$ ${fixos.toLocaleString('pt-BR')}`;
    document.getElementById('effDasVal').textContent = `R$ ${das}`;
    document.getElementById('effLucroVal').textContent = `R$ ${lucro.toLocaleString('pt-BR')}`;
    document.getElementById('gaugeValue').textContent = `${eficiencia.toFixed(0)}%`;

    let verdict = '';
    if (eficiencia >= 60) verdict = '<span style="color:#22c55e">Excelente! Seu MEI esta muito lucrativo.</span>';
    else if (eficiencia >= 40) verdict = '<span style="color:#22c55e">Bom! Mas ha espaco para melhorar.</span>';
    else if (eficiencia >= 20) verdict = '<span style="color:#f59e0b">Regular. Revise seus custos.</span>';
    else verdict = '<span style="color:#dc2626">Atencao! Lucro muito baixo.</span>';

    document.getElementById('effVerdict').innerHTML = verdict;
    document.getElementById('effResult').style.display = 'grid';
}

// ═══════════════════════════════════════════════════════════════════════════
// PRODUTOS
// ═══════════════════════════════════════════════════════════════════════════

async function cadastrarProduto() {
    if (!userState.token) return exigirLogin();

    const nome = document.getElementById('prodNome').value;
    const preco = parseFloat(document.getElementById('prodPreco').value);
    const categoria = document.getElementById('prodCategoria').value;
    const unidade = document.getElementById('prodUnidade').value;
    const data_fabricacao = document.getElementById('prodFabricacao').value || null;
    const data_validade = document.getElementById('prodValidade').value || null;
    const codigo_barras = document.getElementById('prodCodigo').value || null;
    const estoque = parseInt(document.getElementById('prodEstoque').value) || 0;
    const foto_url = document.getElementById('prodFoto').value || null;
    const descricao = document.getElementById('prodDescricao').value;

    try {
        const resp = await apiFetch('/api/produtos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome, preco, categoria, unidade, data_fabricacao,
                data_validade, codigo_barras, estoque, foto_url, descricao
            })
        });
        const data = await resp.json();

        if (data.sucesso) {
            document.getElementById('formProduto').reset();
            carregarProdutos();
            mostrarToast('Produto cadastrado com sucesso!', 'sucesso');
        }
    } catch (error) {
        console.error('Erro ao cadastrar produto:', error);
    }
}

async function carregarProdutos() {
    try {
        const resp = await apiFetch('/api/produtos');
        const data = await resp.json();

        const grid = document.getElementById('listaProdutos');
        const select = document.getElementById('venProduto');

        if (resp.status === 401) {
            if (grid) grid.innerHTML = HTML_BLOQUEIO_LOGIN;
            if (select) select.innerHTML = '<option value="">Faça login para ver produtos</option>';
            return;
        }

        if (data.produtos.length === 0) {
            grid.innerHTML = '<p class="empty-state">Nenhum produto cadastrado ainda.</p>';
            select.innerHTML = '<option value="">Nenhum produto cadastrado...</option>';
            return;
        }

        grid.innerHTML = '';
        select.innerHTML = '<option value="">Selecione um produto...</option>';

        data.produtos.forEach(p => {
            // Badge de validade
            let validadeBadge = '';
            if (p.status_validade) {
                validadeBadge = `<span class="badge-validade" style="background:${p.status_validade.cor}">${p.status_validade.mensagem}</span>`;
            }

            // Foto do produto
            let fotoHtml = '';
            if (p.foto_url) {
                fotoHtml = `<img src="${p.foto_url}" alt="${p.nome}" class="product-photo" onerror="this.style.display='none'">`;
            } else {
                fotoHtml = `<div class="product-photo-placeholder">${p.nome.charAt(0).toUpperCase()}</div>`;
            }

            // Codigo de barras
            let barcodeHtml = '';
            if (p.codigo_barras) {
                barcodeHtml = `<span class="product-barcode">||| ${p.codigo_barras} |||</span>`;
            }

            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <div class="product-photo-container">
                    ${fotoHtml}
                </div>
                <div class="product-details">
                    <div class="product-header">
                        <span class="product-category cat-${p.categoria}">${p.categoria === 'servico' ? 'S' : p.categoria === 'insumo' ? 'I' : 'P'}</span>
                        <strong class="product-name">${p.nome}</strong>
                    </div>
                    <div class="product-meta">
                        <span class="product-price">${p.preco_formatado}/${p.unidade || 'un'}</span>
                        ${p.estoque > 0 ? `<span class="product-estoque">Estoque: ${p.estoque}</span>` : ''}
                    </div>
                    ${p.descricao ? `<span class="product-desc">${p.descricao}</span>` : ''}
                    <div class="product-dates">
                        ${p.data_fabricacao ? `<span class="date-fab">Fabricado: ${p.data_fabricacao}</span>` : ''}
                        ${p.data_validade ? `<span class="date-val">Validade: ${p.data_validade}</span>` : ''}
                        ${validadeBadge}
                    </div>
                    ${barcodeHtml}
                </div>
                <button class="btn-delete" onclick="excluirProduto(${p.id})">X</button>
            `;
            grid.appendChild(card);

            // Option no select
            const option = document.createElement('option');
            option.value = p.id;
            option.textContent = `${p.nome} - ${p.preco_formatado}`;
            option.dataset.preco = p.preco;
            option.dataset.unidade = p.unidade || 'un';
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
    }
}

async function excluirProduto(id) {
    if (!userState.token) return exigirLogin();
    if (!confirm('Excluir este produto?')) return;

    try {
        await apiFetch(`/api/produtos/${id}`, { method: 'DELETE' });
        carregarProdutos();
    } catch (error) {
        console.error('Erro ao excluir produto:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// VENDAS
// ═══════════════════════════════════════════════════════════════════════════

function atualizarTotalVenda() {
    const valor = parseFloat(document.getElementById('venValor').value) || 0;
    const qtd = parseInt(document.getElementById('venQuantidade').value) || 1;
    const total = valor * qtd;
    document.getElementById('venTotal').value = `R$ ${total.toFixed(2).replace('.', ',')}`;
}

async function registrarVenda() {
    if (!userState.token) return exigirLogin();

    const produtoId = document.getElementById('venProduto').value || null;
    const descricao = document.getElementById('venDescricao').value;
    const valor = parseFloat(document.getElementById('venValor').value);
    const quantidade = parseInt(document.getElementById('venQuantidade').value) || 1;
    const data = document.getElementById('venData').value;
    const clienteId = document.getElementById('venCliente').value || null;

    try {
        const resp = await apiFetch('/api/vendas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                produto_id: produtoId ? parseInt(produtoId) : null,
                descricao, valor, quantidade, data,
                cliente_id: clienteId ? parseInt(clienteId) : null
            })
        });
        const dataResp = await resp.json();

        if (dataResp.sucesso) {
            document.getElementById('formVenda').reset();
            document.getElementById('venData').value = new Date().toISOString().split('T')[0];
            document.getElementById('venTotal').value = 'R$ 0,00';
            carregarVendasMes();
            carregarResumoMes();
            mostrarToast(`Venda registrada: ${dataResp.venda.valor_formatado}`, 'sucesso');
        }
    } catch (error) {
        console.error('Erro ao registrar venda:', error);
    }
}

async function carregarVendasMes() {
    const mes = parseInt(document.getElementById('mes').value) || new Date().getMonth() + 1;
    const ano = parseInt(document.getElementById('ano').value) || new Date().getFullYear();

    try {
        const resp = await apiFetch(`/api/vendas?mes=${mes}&ano=${ano}`);
        const data = await resp.json();

        const container = document.getElementById('listaVendas');

        if (resp.status === 401) {
            if (container) container.innerHTML = HTML_BLOQUEIO_LOGIN;
            return;
        }

        if (data.vendas.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma venda registrada este mes.</p>';
            return;
        }

        container.innerHTML = '';
        data.vendas.forEach(v => {
            const item = document.createElement('div');
            item.className = 'venda-item';
            item.innerHTML = `
                <div class="venda-info">
                    <strong>${v.descricao}</strong>
                    <span class="venda-data">${v.data}</span>
                    ${v.cliente ? `<span class="venda-cliente">${v.cliente}</span>` : ''}
                    <span class="venda-qtd">${v.quantidade}x R$ ${v.valor_unitario.toFixed(2).replace('.', ',')}</span>
                </div>
                <div class="venda-right">
                    <span class="venda-valor">${v.valor_formatado}</span>
                    <button class="btn-delete-sm" onclick="excluirVenda(${v.id})">X</button>
                </div>
            `;
            container.appendChild(item);
        });

        // Total
        const totalDiv = document.createElement('div');
        totalDiv.className = 'venda-total';
        totalDiv.innerHTML = `<strong>Total: ${data.total_formatado}</strong>`;
        container.appendChild(totalDiv);
    } catch (error) {
        console.error('Erro ao carregar vendas:', error);
    }
}

async function excluirVenda(id) {
    if (!userState.token) return exigirLogin();
    if (!confirm('Excluir esta venda?')) return;

    try {
        await apiFetch(`/api/vendas/${id}`, { method: 'DELETE' });
        carregarVendasMes();
        carregarResumoMes();
    } catch (error) {
        console.error('Erro ao excluir venda:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// RESUMO MENSAL
// ═══════════════════════════════════════════════════════════════════════════

async function carregarResumoMes() {
    const mes = parseInt(document.getElementById('mes').value) || new Date().getMonth() + 1;
    const ano = parseInt(document.getElementById('ano').value) || new Date().getFullYear();

    try {
        const resp = await apiFetch(`/api/resumo-mensal?mes=${mes}&ano=${ano}`);
        const data = await resp.json();

        if (resp.status === 401) return;

        if (data.sucesso) {
            document.getElementById('resVendas').textContent = data.vendas.total_formatado;
            document.getElementById('resQtdVendas').textContent = `${data.vendas.quantidade} vendas`;
            document.getElementById('resDespesas').textContent = data.despesas.total_formatado;
            document.getElementById('resDas').textContent = data.das.valor_formatado;
            document.getElementById('resDasVenc').textContent = `Vence ${data.das.data_vencimento}`;
            document.getElementById('resLucroBruto').textContent = data.lucro.bruto_formatado;
            document.getElementById('resLucroLiquido').textContent = data.lucro.liquido_formatado;
            document.getElementById('resMargem').textContent = `${data.lucro.margem}%`;
            document.getElementById('resEficiencia').textContent = `${data.eficiencia.percentual}%`;

            const statusBox = document.getElementById('resStatus');
            statusBox.style.display = 'flex';
            statusBox.className = `alert-box ${data.eficiencia.status === 'otimo' || data.eficiencia.status === 'bom' ? 'ok' : data.eficiencia.status === 'medio' ? 'warning' : 'danger'}`;
            document.getElementById('resStatusIcon').textContent = data.eficiencia.status === 'otimo' ? '!' : data.eficiencia.status === 'bom' ? 'i' : '!!';
            document.getElementById('resStatusText').textContent = data.eficiencia.mensagem;
        }
    } catch (error) {
        console.error('Erro ao carregar resumo:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// DESPESAS
// ═══════════════════════════════════════════════════════════════════════════

async function registrarDespesa() {
    if (!userState.token) return exigirLogin();

    const descricao = document.getElementById('despDescricao').value;
    const valor = parseFloat(document.getElementById('despValor').value);
    const data = document.getElementById('despData').value || null;
    const categoria = document.getElementById('despCategoria').value;

    try {
        const resp = await apiFetch('/api/despesas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ descricao, valor, data, categoria })
        });
        const result = await resp.json();

        if (result.sucesso) {
            document.getElementById('formDespesa').reset();
            document.getElementById('despData').value = new Date().toISOString().split('T')[0];
            carregarDespesas();
            carregarResumoMes();
            mostrarToast('Despesa registrada!', 'sucesso');
        }
    } catch (error) {
        console.error('Erro ao registrar despesa:', error);
    }
}

async function carregarDespesas() {
    const mes = parseInt(document.getElementById('filtroDespesaMes').value);
    const ano = new Date().getFullYear();

    try {
        const resp = await apiFetch(`/api/despesas?mes=${mes}&ano=${ano}`);
        const data = await resp.json();

        const lista = document.getElementById('listaDespesas');
        const totalSpan = document.getElementById('totalDespesasMes');

        if (resp.status === 401) {
            if (lista) lista.innerHTML = HTML_BLOQUEIO_LOGIN;
            if (totalSpan) totalSpan.textContent = 'R$ 0,00';
            return;
        }

        totalSpan.textContent = data.total_formatado;

        if (data.despesas.length === 0) {
            lista.innerHTML = '<p class="empty-state">Nenhuma despesa registrada este mes.</p>';
            return;
        }

        lista.innerHTML = '';
        data.despesas.forEach(d => {
            const item = document.createElement('div');
            item.className = 'despesa-item';
            item.innerHTML = `
                <div class="despesa-info">
                    <span class="despesa-categoria cat-${d.categoria}">${d.categoria}</span>
                    <span class="despesa-desc">${d.descricao}</span>
                    <span class="despesa-data">${d.data}</span>
                </div>
                <div class="despesa-right">
                    <span class="despesa-valor">${formatarMoedaLocal(d.valor)}</span>
                    <button class="btn-delete-sm" onclick="excluirDespesa(${d.id})">X</button>
                </div>
            `;
            lista.appendChild(item);
        });
    } catch (error) {
        console.error('Erro ao carregar despesas:', error);
    }
}

async function excluirDespesa(id) {
    if (!userState.token) return exigirLogin();
    try {
        await apiFetch(`/api/despesas/${id}`, { method: 'DELETE' });
        carregarDespesas();
        carregarResumoMes();
    } catch (error) {
        console.error('Erro ao excluir despesa:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// LIMITE ANUAL
// ═══════════════════════════════════════════════════════════════════════════

async function carregarLimiteAnual() {
    const ano = new Date().getFullYear();
    const TETO_ANUAL = 81000;

    try {
        const resp = await apiFetch(`/api/faturamento-anual?ano=${ano}`);
        const data = await resp.json();

        if (resp.status === 401) return;

        if (data.sucesso) {
            const faturamento = data.total;
            const restante = Math.max(0, TETO_ANUAL - faturamento);
            const porcentagem = Math.min(100, (faturamento / TETO_ANUAL) * 100);

            document.getElementById('faturamentoAnual').textContent = formatarMoedaLocal(faturamento);
            document.getElementById('restanteAnual').textContent = formatarMoedaLocal(restante);
            document.getElementById('porcentagemAnual').textContent = `${porcentagem.toFixed(1)}%`;

            // Barra de progresso
            const barra = document.getElementById('barraAnual');
            barra.style.width = `${porcentagem}%`;
            barra.className = 'limite-barra-preenchida';
            if (porcentagem >= 90) barra.classList.add('critico');
            else if (porcentagem >= 70) barra.classList.add('alerta');
            else barra.classList.add('ok');

            // Alertas
            const alertas = document.getElementById('alertasAnual');
            alertas.innerHTML = '';
            if (porcentagem >= 90) {
                alertas.innerHTML = '<div class="limite-alerta critico">! ALERTA: Faturamento acima de 90% do limite! Risco de perder isencao do Simples Nacional.</div>';
            } else if (porcentagem >= 70) {
                alertas.innerHTML = '<div class="limite-alerta alerta">Atencao: Ja utilizou mais de 70% do limite anual. Comece a planejar.</div>';
            }

            // Historico mensal
            const historico = document.getElementById('historicoMensal');
            historico.innerHTML = '';
            const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
            for (let m = 1; m <= 12; m++) {
                const valorMes = data.por_mes[m] || 0;
                const barraMes = Math.min(100, (valorMes / (TETO_ANUAL/12)) * 100);
                historico.innerHTML += `
                    <div class="historico-item">
                        <span class="historico-mes">${meses[m-1]}</span>
                        <div class="historico-barra">
                            <div class="historico-barra-preenchida" style="width:${barraMes}%"></div>
                        </div>
                        <span class="historico-valor">${formatarMoedaLocal(valorMes)}</span>
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Erro ao carregar limite anual:', error);
    }
}

function formatarMoedaLocal(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

let cameraStream = null;
let html5QrCode = null;

function initCameraAndScanner() {
    const btnTakePhoto = document.getElementById('btnTakePhoto');
    const btnScanBarcode = document.getElementById('btnScanBarcode');
    const btnCloseCamera = document.getElementById('btnCloseCamera');
    const btnCancelCamera = document.getElementById('btnCancelCamera');
    const btnCapturePhoto = document.getElementById('btnCapturePhoto');
    const btnCloseScanner = document.getElementById('btnCloseScanner');
    const btnStopScanner = document.getElementById('btnStopScanner');
    const btnRemovePreview = document.getElementById('btnRemovePreview');

    if (btnTakePhoto) btnTakePhoto.addEventListener('click', openCameraModal);
    if (btnScanBarcode) btnScanBarcode.addEventListener('click', openScannerModal);
    if (btnCloseCamera) btnCloseCamera.addEventListener('click', closeCameraModal);
    if (btnCancelCamera) btnCancelCamera.addEventListener('click', closeCameraModal);
    if (btnCapturePhoto) btnCapturePhoto.addEventListener('click', capturePhoto);
    if (btnCloseScanner) btnCloseScanner.addEventListener('click', closeScannerModal);
    if (btnStopScanner) btnStopScanner.addEventListener('click', closeScannerModal);
    if (btnRemovePreview) btnRemovePreview.addEventListener('click', removePreview);
}

async function openCameraModal() {
    const modal = document.getElementById('cameraModal');
    const video = document.getElementById('cameraVideo');
    modal.style.display = 'flex';

    try {
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 960 }
            }
        };
        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = cameraStream;
    } catch (err) {
        alert('Nao foi possivel acessar a camera. Verifique as permissoes do navegador.');
        closeCameraModal();
    }
}

function closeCameraModal() {
    const modal = document.getElementById('cameraModal');
    const video = document.getElementById('cameraVideo');
    if (cameraStream) {
        cameraStream.getTracks().forEach(t => t.stop());
        cameraStream = null;
    }
    video.srcObject = null;
    modal.style.display = 'none';
}

function capturePhoto() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);

    document.getElementById('prodFoto').value = dataUrl;
    document.getElementById('fotoPreview').src = dataUrl;
    document.getElementById('fotoPreviewContainer').style.display = 'block';

    closeCameraModal();
}

function removePreview() {
    document.getElementById('prodFoto').value = '';
    document.getElementById('fotoPreview').src = '';
    document.getElementById('fotoPreviewContainer').style.display = 'none';
}

async function openScannerModal() {
    const modal = document.getElementById('scannerModal');
    const feedback = document.getElementById('scannerFeedback');
    feedback.style.display = 'none';
    modal.style.display = 'flex';

    html5QrCode = new Html5Qrcode('scannerReader');

    try {
        await html5QrCode.start(
            { facingMode: 'environment' },
            {
                fps: 10,
                qrbox: { width: 280, height: 150 },
                aspectRatio: 1.5
            },
            onScanSuccess,
            () => {}
        );
    } catch (err) {
        alert('Nao foi possivel acessar a camera para escanear. Verifique as permissoes.');
        closeScannerModal();
    }
}

function onScanSuccess(decodedText) {
    document.getElementById('prodCodigo').value = decodedText;

    const feedback = document.getElementById('scannerFeedback');
    const feedbackText = document.getElementById('scannerFeedbackText');
    feedbackText.textContent = `Codigo detectado: ${decodedText}`;
    feedback.style.display = 'flex';

    setTimeout(() => closeScannerModal(), 1500);
}

async function closeScannerModal() {
    const modal = document.getElementById('scannerModal');
    if (html5QrCode) {
        try {
            const state = html5QrCode.getState();
            if (state === 2) {
                await html5QrCode.stop();
            }
        } catch (e) {}
        html5QrCode = null;
    }
    const reader = document.getElementById('scannerReader');
    reader.innerHTML = '';
    modal.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', initCameraAndScanner);

// ═══════════════════════════════════════════════════════════════════════════
// CLIENTES (CRM)
// ═══════════════════════════════════════════════════════════════════════════

async function cadastrarCliente() {
    if (!userState.token) return exigirLogin();

    const nome = document.getElementById('cliNome').value;
    const telefone = document.getElementById('cliTelefone').value;
    const email = document.getElementById('cliEmail').value;
    const data_aniversario = document.getElementById('cliAniversario').value || null;
    const produto_preferido = document.getElementById('cliProduto').value;
    const periodicidade = document.getElementById('cliPeriodicidade').value || null;
    const endereco = document.getElementById('cliEndereco').value;
    const observacoes = document.getElementById('cliObservacoes').value;

    try {
        const resp = await apiFetch('/api/clientes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome, telefone, email, data_aniversario,
                produto_preferido, periodicidade, endereco, observacoes
            })
        });
        const data = await resp.json();
        if (data.sucesso) {
            document.getElementById('formCliente').reset();
            carregarClientes();
            carregarAniversariantes();
            mostrarToast('Cliente salvo!', 'sucesso');
        }
    } catch (error) {
        console.error('Erro ao cadastrar cliente:', error);
    }
}

async function carregarClientes(busca = '') {
    try {
        const url = busca ? `/api/clientes?q=${encodeURIComponent(busca)}` : '/api/clientes';
        const resp = await apiFetch(url);
        const data = await resp.json();
        const lista = document.getElementById('listaClientes');

        if (resp.status === 401) {
            if (lista) lista.innerHTML = HTML_BLOQUEIO_LOGIN;
            return;
        }

        if (data.clientes.length === 0) {
            lista.innerHTML = '<p class="empty-state">Nenhum cliente encontrado.</p>';
            return;
        }

        lista.innerHTML = '';
        data.clientes.forEach(c => {
            let idade = '';
            if (c.data_aniversario) {
                const parts = c.data_aniversario.split('-');
                const aniversario = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                const hoje = new Date();
                let anos = hoje.getFullYear() - aniversario.getFullYear();
                if (hoje.getMonth() < aniversario.getMonth() ||
                    (hoje.getMonth() === aniversario.getMonth() && hoje.getDate() < aniversario.getDate())) {
                    anos--;
                }
                idade = ` | ${anos} anos`;
            }

            let periodicidadeBadge = '';
            if (c.periodicidade) {
                periodicidadeBadge = `<span class="cli-periodicidade">${c.periodicidade}</span>`;
            }

            let aniversarioInfo = '';
            if (c.data_aniversario) {
                const parts = c.data_aniversario.split('-');
                const aniv = new Date(new Date().getFullYear(), parseInt(parts[1]) - 1, parseInt(parts[2]));
                if (aniv < new Date()) aniv.setFullYear(aniv.getFullYear() + 1);
                const dias = Math.ceil((aniv - new Date()) / (1000 * 60 * 60 * 24));
                if (dias <= 30) {
                    aniversarioInfo = `<span class="cli-aniversario-proximo">Aniversario em ${dias} dias!</span>`;
                }
            }

            const card = document.createElement('div');
            card.className = 'cliente-card';
            card.innerHTML = `
                <div class="cliente-info">
                    <strong class="cliente-nome">${c.nome}</strong>
                    <span class="cliente-detalhes">
                        ${c.telefone ? `Tel: ${c.telefone}` : ''}
                        ${c.email ? ` | ${c.email}` : ''}
                        ${idade}
                    </span>
                    <div class="cliente-tags">
                        ${periodicidadeBadge}
                        ${c.produto_preferido ? `<span class="cli-produto">${c.produto_preferido}</span>` : ''}
                        ${aniversarioInfo}
                    </div>
                    ${c.observacoes ? `<span class="cli-obs">${c.observacoes}</span>` : ''}
                </div>
                <div class="cliente-actions">
                    <button class="btn-delete-sm" onclick="excluirCliente(${c.id})">X</button>
                </div>
            `;
            lista.appendChild(card);
        });
    } catch (error) {
        console.error('Erro ao carregar clientes:', error);
    }
}

function buscarClientes() {
    const busca = document.getElementById('buscaCliente').value;
    carregarClientes(busca);
}

async function excluirCliente(id) {
    if (!userState.token) return exigirLogin();
    if (!confirm('Excluir este cliente?')) return;
    try {
        await apiFetch(`/api/clientes/${id}`, { method: 'DELETE' });
        carregarClientes();
        carregarAniversariantes();
    } catch (error) {
        console.error('Erro ao excluir cliente:', error);
    }
}

async function carregarAniversariantes() {
    try {
        const resp = await apiFetch('/api/clientes/aniversarios');
        const data = await resp.json();
        const card = document.getElementById('cardAniversarios');
        const lista = document.getElementById('listaAniversarios');

        if (resp.status === 401) {
            if (card) card.style.display = 'none';
            return;
        }

        if (data.clientes && data.clientes.length > 0) {
            card.style.display = 'block';
            lista.innerHTML = '';
            data.clientes.forEach(c => {
                const item = document.createElement('div');
                item.className = 'aniversariante-item';
                item.innerHTML = `
                    <span class="aniv-icone">!</span>
                    <div>
                        <strong>${c.nome}</strong>
                        <span>${c.data_aniversario_formatado || c.data_aniversario}</span>
                        ${c.telefone ? `<a href="https://wa.me/55${c.telefone.replace(/\D/g, '')}" target="_blank" class="aniv-whatsapp">Enviar WhatsApp</a>` : ''}
                    </div>
                `;
                lista.appendChild(item);
            });
        } else {
            card.style.display = 'none';
        }
    } catch (error) {
        console.error('Erro ao carregar aniversariantes:', error);
    }
}

async function carregarClientesSelect() {
    try {
        const resp = await apiFetch('/api/clientes');
        const data = await resp.json();
        const select = document.getElementById('venCliente');
        if (!select) return;

        select.innerHTML = '<option value="">Cliente nao cadastrado</option>';

        if (resp.status === 401) return;

        if (data.clientes) {
            data.clientes.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.nome + (c.telefone ? ` (${c.telefone})` : '');
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar select de clientes:', error);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PLANO PRO
// ═══════════════════════════════════════════════════════════════════════════

function assinarPro() {
    if (!userState.token || !userState.autenticado) {
        abrirModalAuth('login', 'Entre ou crie sua conta para assinar.');
        return;
    }
    location.hash = '#plano-pro';
}

async function aplicarCupom() {
    const input = document.getElementById('cupomInput');
    const status = document.getElementById('cupomStatus');
    if (!input || !status) return;

    const codigo = input.value.trim();
    if (!codigo) {
        cupomAtivo = null;
        status.textContent = '';
        return;
    }
    if (!userState.token || !userState.autenticado) {
        status.textContent = 'Entre na sua conta para usar um cupom.';
        return;
    }

    status.textContent = 'Validando cupom...';
    try {
        const resp = await apiFetch('/api/cupom/validar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo })
        });
        const data = await resp.json();
        if (data.valido) {
            cupomAtivo = data.codigo;
            status.textContent = 'Cupom aplicado: -' + data.percentual + '% = R$ ' + data.valor_final.toFixed(2).replace('.', ',');
        } else {
            cupomAtivo = null;
            status.textContent = data.motivo === 'inativo' ? 'Cupom inativo.' : 'Cupom invalido.';
        }
    } catch (error) {
        console.error('Erro ao validar cupom:', error);
        cupomAtivo = null;
        status.textContent = 'Erro ao validar cupom. Tente novamente.';
    }
}

async function iniciarAssinatura() {
    if (!userState.token || !userState.autenticado) {
        abrirModalAuth('login', 'Entre ou crie sua conta para assinar.');
        return;
    }

    const email = document.getElementById('proEmail').value.trim();
    if (!email) {
        mostrarToast('Informe seu e-mail para o pagamento.', 'info');
        return;
    }

    const btn = document.getElementById('btnAssinar');

    try {
        const valResp = await fetch('/api/validar-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const valData = await valResp.json();
        if (valData && valData.valido === false) {
            mostrarToast(valData.motivo || 'E-mail invalido. Verifique e tente novamente.', 'erro');
            return;
        }
    } catch (error) {
        console.error('Erro ao validar e-mail:', error);
    }

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Gerando pagamento...';
    }

    try {
        const body = { email: email };
        const cupomCodigo = cupomAtivo || document.getElementById('cupomInput').value.trim();
        if (cupomCodigo) body.cupom = cupomCodigo;

        const resp = await apiFetch('/api/assinatura/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (resp.status === 401) {
            mostrarToast('Faça login para continuar', 'info');
            abrirModalAuth('login');
            return;
        }

        const data = await resp.json();
        if (data.sucesso && data.checkout_url) {
            if (data.valor_final !== undefined) {
                const proStatusEl = document.getElementById('proStatus');
                if (proStatusEl) {
                    const pct = data.valor_original ? Math.round(data.desconto / data.valor_original * 100) : 0;
                    proStatusEl.innerHTML = '<div class="pro-status-ativo"><span class="pro-check">!</span><span>Cupom aplicado: -' + pct + '% = R$ ' + data.valor_final.toFixed(2).replace('.', ',') + '</span></div>';
                }
            }
            window.location.href = data.checkout_url;
        } else {
            mostrarToast(data.detail || data.mensagem || 'Erro ao iniciar pagamento. Tente novamente.', 'erro');
        }
    } catch (error) {
        console.error('Erro ao criar checkout:', error);
        mostrarToast('Erro ao iniciar pagamento. Tente novamente.', 'erro');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Assinar agora - R$ 9,90/mes';
        }
    }
}

async function verificarPlano() {
    const checkoutForm = document.getElementById('proCheckoutForm');
    const proStatus = document.getElementById('proStatus');
    if (!checkoutForm || !proStatus) return;

    if (!userState.token) {
        checkoutForm.style.display = 'block';
        proStatus.style.display = 'none';
        return;
    }

    try {
        const resp = await apiFetch('/api/plano');
        if (resp.status === 401) {
            checkoutForm.style.display = 'block';
            proStatus.style.display = 'none';
            return;
        }
        const data = await resp.json();
        if (data.ativo) {
            checkoutForm.style.display = 'none';
            proStatus.style.display = 'block';
        } else {
            checkoutForm.style.display = 'block';
            proStatus.style.display = 'none';
        }
    } catch (error) {
        console.error('Erro ao verificar plano:', error);
    }
}

function tratarRetornoPagamento() {
    const params = new URLSearchParams(window.location.search);
    const pagamento = params.get('pagamento');
    const banner = document.getElementById('pagamentoBanner');
    if (!banner || !pagamento) return;

    if (pagamento === 'sucesso') {
        banner.style.display = 'block';
        banner.innerHTML = '<div class="pagamento-aviso sucesso">Pagamento realizado! Ativando seu plano...</div>';
        verificarPlanoRealtime();
    } else if (pagamento === 'pendente') {
        banner.style.display = 'block';
        banner.innerHTML = '<div class="pagamento-aviso pendente">Pagamento pendente. Assim que for confirmado, seu plano PRO sera ativado.</div>';
    } else if (pagamento === 'erro') {
        banner.style.display = 'block';
        banner.innerHTML = '<div class="pagamento-aviso erro">Nao foi possivel concluir o pagamento. Tente novamente.<br><button type="button" class="btn btn-primary btn-sm" onclick="window.history.back()">Voltar</button></div>';
    }
}

function verificarPlanoRealtime() {
    clearInterval(pollPlanoTimer);
    const inicio = Date.now();
    const duracaoMax = 90000;
    const banner = document.getElementById('pagamentoBanner');

    pollPlanoTimer = setInterval(async () => {
        if (Date.now() - inicio > duracaoMax) {
            clearInterval(pollPlanoTimer);
            if (banner) {
                banner.innerHTML = '<div class="pagamento-aviso pendente">Ainda nao recebemos a confirmacao do pagamento. Seu PRO sera ativado automaticamente assim que confirmado.</div>';
            }
            return;
        }
        try {
            const resp = await apiFetch('/api/plano');
            if (resp.status === 401) {
                return;
            }
            const data = await resp.json();
            if (data.ativo) {
                clearInterval(pollPlanoTimer);
                if (banner) {
                    banner.innerHTML = '<div class="pagamento-aviso sucesso">Seu plano PRO esta ativo! ✅</div>';
                }
                verificarPlano();
            }
        } catch (error) {
            console.error('Erro ao verificar plano em tempo real:', error);
        }
    }, 4000);
}
