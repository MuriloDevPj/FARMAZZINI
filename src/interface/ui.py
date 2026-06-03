def render_full_ui(chats: str, active_chat_id: int, active_db: str) -> str:
    db_label = {"todas": "Todas", "ponte": "FarmaPonte", "veracruz": "Vera Cruz"}.get(active_db, "Todas")
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root {{
    --bg-main:      #060608;
    --bg-sidebar:   rgba(12,12,16,0.92);
    --bg-card:      #0b0b0d;
    --primary:      #E63946;
    --primary-dark: #8B0000;
    --text-main:    #ffffff;
    --text-muted:   #9a9a9f;
    --border:       rgba(255,255,255,0.06);
    --glow-red:     rgba(230,57,70,0.22);
}}
*{{ box-sizing:border-box; margin:0; padding:0; }}
html, body {{
    font-family:'Urbanist',sans-serif;
    background:var(--bg-main);
    color:var(--text-main);
    height:100dvh;
    max-height:100dvh;
    min-height:unset;
    margin:0;
    padding:0;
    overflow:hidden;
    position:relative;
}}
.fluid-glow-1 {{
    position:fixed; top:-15%; left:20%;
    width:60vw; height:60vw;
    background:radial-gradient(circle,var(--glow-red) 0%,rgba(139,0,0,0.05) 50%,transparent 75%);
    filter:blur(100px); z-index:1; pointer-events:none; border-radius:50%;
}}
.fluid-glow-2 {{
    position:fixed; bottom:-10%; right:10%;
    width:50vw; height:50vw;
    background:radial-gradient(circle,rgba(230,57,70,0.15) 0%,rgba(139,0,0,0.03) 60%,transparent 80%);
    filter:blur(100px); z-index:1; pointer-events:none; border-radius:50%;
}}
.app-shell {{ display:flex; width:100%; height:100dvh; position:relative; z-index:2; overflow:hidden; }}

/* ── SIDEBAR ── */
.sidebar {{
    position:absolute; top:16px; left:16px; bottom:16px; width:320px;
    background:var(--bg-sidebar);
    border:1px solid var(--border); border-radius:24px;
    display:flex; flex-direction:column;
    padding:24px 18px; gap:20px; z-index:10;
    backdrop-filter:blur(25px);
    box-shadow:0 16px 40px rgba(0,0,0,0.7);
    transition:transform 0.35s cubic-bezier(0.25,0.8,0.25,1),opacity 0.35s ease;
    max-height:calc(100dvh - 32px);
}}
.sidebar.collapsed {{ transform:translateX(-352px); opacity:0; pointer-events:none; }}
.sidebar-header {{ display:flex; align-items:center; justify-content:space-between; }}
.sidebar-title {{ font-size:13px; text-transform:uppercase; letter-spacing:2.5px; color:var(--primary); font-weight:700; }}

/* db pills */
.db-selector-container {{
    display:flex; flex-direction:column; gap:8px;
    background:rgba(255,255,255,0.03); padding:12px;
    border-radius:16px; border:1px solid var(--border);
}}
.db-selector-title {{ font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700; letter-spacing:1px; }}
.db-pills {{
    display:flex; background:rgba(0,0,0,0.4);
    border-radius:10px; padding:3px;
    border:1px solid rgba(255,255,255,0.05);
}}
.db-pill {{
    flex:1; padding:8px; text-align:center;
    font-size:12px; font-weight:600; color:var(--text-muted);
    cursor:pointer; border-radius:8px; transition:all 0.2s ease;
    user-select:none;
}}
.db-pill.active {{
    background:var(--primary); color:white;
    box-shadow:0 4px 12px rgba(230,57,70,0.3);
}}

/* busca */
.search-chat-container {{ position:relative; width:100%; }}
.search-chat-container i {{
    position:absolute; left:14px; top:50%;
    transform:translateY(-50%); color:var(--text-muted); font-size:13px;
}}
.search-chat-container input {{
    width:100%; height:42px;
    background:rgba(255,255,255,0.04);
    border:1px solid var(--border); border-radius:14px;
    padding-left:38px; padding-right:15px;
    color:var(--text-main); font-family:'Urbanist',sans-serif;
    font-size:14px; outline:none; transition:border-color 0.2s;
}}
.search-chat-container input:focus {{ border-color:rgba(230,57,70,0.4); }}

/* lista de chats */
.chat-list {{
    display:flex; flex-direction:column; gap:8px;
    overflow-y:auto; flex-grow:1; padding-right:2px;
}}
.chat-list::-webkit-scrollbar {{ width:4px; }}
.chat-list::-webkit-scrollbar-thumb {{ background:rgba(255,255,255,0.08); border-radius:4px; }}
.chat-item {{
    padding:12px 14px; border-radius:12px;
    background:rgba(255,255,255,0.01);
    border:1px solid transparent;
    font-size:14px; color:var(--text-muted);
    cursor:pointer; display:flex; align-items:center; justify-content:space-between;
    transition:all 0.2s ease;
}}
.chat-item:hover {{ border-color:rgba(230,57,70,0.2); color:var(--text-main); background:rgba(255,255,255,0.03); }}
.chat-item.active {{ border-color:var(--primary); color:var(--text-main); background:rgba(230,57,70,0.08); }}
.chat-item-left {{ display:flex; align-items:center; gap:10px; overflow:hidden; flex:1; min-width:0; }}
.chat-title-span {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.rename-input {{
    background:transparent; border:none; border-bottom:1px solid var(--primary);
    color:var(--text-main); font-family:'Urbanist',sans-serif;
    font-size:14px; outline:none; width:100%;
}}
.chat-item-actions {{ display:flex; gap:8px; opacity:0; transition:opacity 0.2s; flex-shrink:0; }}
.chat-item:hover .chat-item-actions {{ opacity:0.8; }}
.action-icon {{ color:var(--text-muted); font-size:11px; cursor:pointer; transition:color 0.2s; }}
.action-icon:hover {{ color:var(--primary); }}

.btn-new-chat {{
    background:transparent; border:1px dashed var(--primary);
    color:var(--primary); padding:14px; border-radius:16px;
    cursor:pointer; font-weight:600;
    display:flex; align-items:center; justify-content:center; gap:10px;
    transition:all 0.2s; font-family:'Urbanist',sans-serif;
}}
.btn-new-chat:hover {{ background:rgba(230,57,70,0.08); box-shadow:0 4px 12px rgba(230,57,70,0.15); }}

/* ── MAIN ── */
.main-content {{
    flex-grow:1; display:flex; flex-direction:column;
    background:var(--bg-card); overflow:hidden;
    position:relative; z-index:2;
    width:100%; height:100dvh;
    transition:padding-left 0.35s cubic-bezier(0.25,0.8,0.25,1);
    padding-left:352px;
}}
.main-content.no-sidebar {{ padding-left:0; }}

.header {{
    padding:20px 40px; border-bottom:1px solid var(--border);
    display:flex; justify-content:space-between; align-items:center;
    background:rgba(11,11,13,0.8); backdrop-filter:blur(10px);
    flex-shrink:0;
}}
.header-left {{ display:flex; align-items:center; gap:20px; }}
.menu-toggle {{
    background:rgba(255,255,255,0.03); border:1px solid var(--border);
    color:var(--text-main); width:40px; height:40px; border-radius:12px;
    cursor:pointer; transition:all 0.2s;
    display:flex; align-items:center; justify-content:center;
}}
.menu-toggle:hover {{ color:var(--primary); border-color:rgba(230,57,70,0.4); background:rgba(230,57,70,0.05); }}
.logo-placeholder {{ font-size:20px; font-weight:700; letter-spacing:3px; color:var(--text-main); }}
.logo-placeholder span {{ color:var(--primary); }}
.tag-badge {{
    background:rgba(16,185,129,0.15); border:1px solid #10b981; color:#10b981;
    padding:3px 10px; border-radius:4px; font-size:10px; font-weight:700; text-transform:uppercase;
}}

/* ── CHAT SCROLLER ── */
.chat-scroller {{
    flex:1; overflow-y:auto; padding:40px;
    padding-bottom:24px;
    display:flex; flex-direction:column; gap:24px;
    min-height:0;
}}
.chat-scroller::-webkit-scrollbar {{ width:4px; }}
.chat-scroller::-webkit-scrollbar-thumb {{ background:rgba(255,255,255,0.08); border-radius:4px; }}

/* mensagens */
.message {{ display:flex; gap:15px; max-width:75%; animation:fadeIn 0.3s cubic-bezier(0.16,1,0.3,1); }}
@keyframes fadeIn {{ from{{opacity:0;transform:translateY(12px)}} to{{opacity:1;transform:translateY(0)}} }}
.message.user {{ align-self:flex-end; flex-direction:row-reverse; }}
.avatar {{
    width:38px; height:38px; border-radius:10px;
    display:flex; align-items:center; justify-content:center;
    font-weight:700; font-size:13px; flex-shrink:0;
    box-shadow:0 4px 10px rgba(0,0,0,0.3);
}}
.message.user .avatar {{ background:var(--primary); color:white; }}
.message.bot .avatar {{ background:#121215; border:1px solid var(--primary); color:var(--primary); }}
.msg-bubble {{
    background:rgba(30,30,40,0.4); border:1px solid var(--border);
    padding:16px 20px; border-radius:18px; font-size:15px; line-height:1.6; width:100%;
}}
.message.user .msg-bubble {{
    background:linear-gradient(135deg,#E63946 0%,#B81D24 50%,#820D13 100%);
    border:1px solid rgba(255,255,255,0.18);
    box-shadow:0 8px 24px rgba(230,57,70,0.3); color:#fff;
}}

/* ── ÁREA FIXA NO RODAPÉ — sticky dentro do flex, acompanha zoom igual ao Claude ── */
.bottom-fixed-area {{
    position:relative;
    flex-shrink:0;
    background:linear-gradient(to top, rgba(6,6,8,0.98) 70%, transparent);
    padding:16px 40px 20px;
    display:flex; flex-direction:column; align-items:center; gap:12px;
    z-index:100;
    width:100%;
}}
.bottom-fixed-area.no-sidebar {{ left:0; }}

/* hot buttons */
.hot-buttons-wrapper {{
    display:flex; gap:12px; justify-content:center;
    flex-wrap:wrap;
}}
.hot-btn {{
    background:linear-gradient(135deg,var(--primary),var(--primary-dark));
    color:white; border:1px solid rgba(255,255,255,0.1);
    padding:12px 22px; border-radius:24px;
    font-weight:600; font-size:13px; cursor:pointer;
    display:flex; align-items:center; gap:8px;
    box-shadow:0 4px 15px rgba(230,57,70,0.2);
    transition:all 0.25s cubic-bezier(0.4,0,0.2,1);
    font-family:'Urbanist',sans-serif;
}}
.hot-btn:hover {{ transform:translateY(-3px); box-shadow:0 8px 25px rgba(230,57,70,0.4); }}

/* input */
.input-container {{
    width:100%; display:flex; justify-content:center;
}}
.disclaimer {{
    font-size:12px; color:var(--text-muted);
    text-align:center; padding-bottom:8px;
    line-height:1.5;
}}
.disclaimer a {{
    color:var(--text-muted); text-decoration:underline;
    text-underline-offset:3px; transition:color 0.2s;
}}
.disclaimer a:hover {{ color:var(--primary); }}
.input-box {{
    width:100%; max-width:800px;
    background:rgba(14,14,18,0.9); border:1px solid var(--border);
    height:56px; border-radius:28px;
    display:flex; align-items:center; padding:0 20px; gap:15px;
    box-shadow:0 10px 30px rgba(0,0,0,0.5); transition:border-color 0.2s;
}}
.input-box:focus-within {{ border-color:rgba(230,57,70,0.4); }}
.input-box input {{
    flex-grow:1; background:transparent; border:none;
    color:white; font-size:15px; outline:none; font-family:'Urbanist',sans-serif;
}}
.btn-send {{ background:none; border:none; color:var(--primary); font-size:18px; cursor:pointer; transition:all 0.2s; }}
.btn-send:hover {{ color:var(--text-main); transform:scale(1.1); }}

/* tabelas */
.table-container {{ overflow-x:auto; margin-top:12px; border-radius:12px; border:1px solid var(--border); }}
table {{ width:100%; border-collapse:collapse; background:rgba(10,10,12,0.6); }}
th {{ text-align:left; color:var(--primary); padding:14px; border-bottom:2px solid var(--border); font-size:12px; text-transform:uppercase; letter-spacing:1px; }}
td {{ padding:14px; border-bottom:1px solid var(--border); font-size:14px; color:#eee; }}
tr:last-child td {{ border-bottom:none; }}

/* action buttons dentro das mensagens */
.action-row {{ display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }}
.action-btn {{
    background:rgba(255,255,255,0.03); border:1px solid var(--border);
    color:#ddd; padding:8px 16px; border-radius:8px; font-size:12px;
    cursor:pointer; display:flex; align-items:center; gap:6px;
    transition:all 0.2s; font-family:'Urbanist',sans-serif; font-weight:600;
}}
.action-btn:hover {{ border-color:var(--primary); color:white; background:rgba(230,57,70,0.1); }}

/* gráfico */
.chart-mock {{
    margin-top:15px; background:rgba(10,10,12,0.85);
    border:1px solid var(--border); border-radius:16px;
    padding:24px; display:flex; flex-direction:column; gap:18px;
    animation:fadeIn 0.4s ease-out;
}}
.bar-container {{
    display:flex; align-items:flex-end; justify-content:space-around;
    gap:20px; height:140px; padding-top:15px;
    border-bottom:1px solid rgba(255,255,255,0.1);
}}
.bar {{
    width:48px;
    background:linear-gradient(to top,var(--primary-dark),var(--primary));
    border-radius:8px 8px 0 0;
    animation:growUp 0.8s cubic-bezier(0.16,1,0.3,1) forwards;
    min-height:5px; position:relative;
    box-shadow:0 4px 15px rgba(230,57,70,0.3);
}}
.bar-value {{ position:absolute; top:-24px; left:50%; transform:translateX(-50%); font-size:12px; font-weight:700; color:var(--primary); }}
@keyframes growUp {{ from{{height:0}} to{{height:var(--h)}} }}
.bar-labels {{ display:flex; justify-content:space-around; font-size:11px; color:var(--text-muted); font-weight:600; }}

/* toast */
.download-toast {{
    position:fixed; top:20px; right:20px;
    background:#0d2818; border:1px solid #1e5e2f; color:#4ade80;
    padding:12px 24px; border-radius:12px; font-size:14px;
    display:none; z-index:200;
    box-shadow:0 10px 25px rgba(0,0,0,0.5); font-weight:600;
    animation:slideIn 0.3s cubic-bezier(0.16,1,0.3,1);
}}
@keyframes slideIn {{ from{{transform:translateY(-20px);opacity:0}} to{{transform:translateY(0);opacity:1}} }}

/* loading */
.dot-flashing {{
    position:relative; width:10px; height:10px;
    border-radius:5px; background-color:var(--primary);
    animation:dotf 1s infinite linear alternate; animation-delay:.5s; margin:10px 20px;
}}
.dot-flashing::before,.dot-flashing::after {{
    content:''; display:inline-block; position:absolute; top:0;
    width:10px; height:10px; border-radius:5px; background-color:var(--primary);
}}
.dot-flashing::before {{ left:-15px; animation:dotf 1s infinite linear alternate; animation-delay:0s; }}
.dot-flashing::after  {{ left:15px;  animation:dotf 1s infinite linear alternate; animation-delay:1s; }}
@keyframes dotf {{ 0%{{background-color:var(--primary)}} 50%,100%{{background-color:rgba(230,57,70,0.2)}} }}

@media(max-width:768px){{
    .sidebar {{ top:76px; left:8px; right:8px; width:calc(100% - 16px); }}
    .main-content {{ padding-left:0 !important; }}
    .header {{ padding:15px 20px; }}
    .chat-scroller {{ padding:20px; }}
    .message {{ max-width:90%; }}
    .hot-buttons-wrapper,.input-container {{ padding-left:20px; padding-right:20px; }}
}}
</style>
</head>
<body>

<div class="fluid-glow-1"></div>
<div class="fluid-glow-2"></div>
<div class="download-toast" id="toast">✅ Dados exportados em CSV!</div>

<div class="app-shell">

  <!-- ══ SIDEBAR ══ -->
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-title">Chats & Consultas</div>
      <i class="fa-solid fa-clock-rotate-left" style="opacity:0.5"></i>
    </div>

    <!-- Seletor de base -->
    <div class="db-selector-container">
      <div class="db-selector-title">Base de Dados Ativa</div>
      <div class="db-pills" id="dbPills">
        <div class="db-pill {'active' if active_db=='todas' else ''}" data-db="todas" onclick="setDb('todas',this)">Todas</div>
        <div class="db-pill {'active' if active_db=='ponte' else ''}" data-db="ponte" onclick="setDb('ponte',this)">Ponte</div>
        <div class="db-pill {'active' if active_db=='veracruz' else ''}" data-db="veracruz" onclick="setDb('veracruz',this)">Vera Cruz</div>
      </div>
    </div>

    <!-- Busca -->
    <div class="search-chat-container">
      <i class="fa-solid fa-magnifying-glass"></i>
      <input type="text" id="searchInput" placeholder="Buscar chats..." oninput="renderChatList()">
    </div>

    <!-- Lista de chats -->
    <div class="chat-list" id="chatList"></div>

    <button class="btn-new-chat" onclick="newChat()">
      <i class="fa-solid fa-plus"></i> Novo Chat
    </button>
  </div>

  <!-- ══ MAIN ══ -->
  <div class="main-content" id="mainContent">

    <div class="header">
      <div class="header-left">
        <button class="menu-toggle" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
        <div class="logo-placeholder">FARMAZZINI <span>INTEL</span></div>
      </div>
      <div style="font-size:13px;color:var(--text-muted);display:flex;align-items:center;gap:8px;">
        <span class="tag-badge">✨ Pipeline Ativo</span>
        <i class="fa-solid fa-circle" style="color:#10b981;font-size:8px;"></i>
        Base: <span id="dbLabel">{db_label}</span>
      </div>
    </div>

    <div class="chat-scroller" id="chatWindow"></div>

    <!-- Área fixa no rodapé: botões + input sempre visíveis independente de zoom -->
    <div class="bottom-fixed-area" id="bottomArea">
      <div class="hot-buttons-wrapper">
        <button class="hot-btn" onclick="hotTrigger('estoque')"><i class="fa-solid fa-boxes-stacked"></i> Estoque Crítico</button>
        <button class="hot-btn" onclick="hotTrigger('preco')"><i class="fa-solid fa-tags"></i> Achar Mais Barato</button>
        <button class="hot-btn" onclick="hotTrigger('promos')"><i class="fa-solid fa-fire"></i> Maiores Promoções</button>
      </div>
      <div class="input-container">
        <div class="input-box">
          <input type="text" id="userInput" placeholder="Faça uma consulta estratégica..."
                 onkeypress="if(event.key==='Enter')sendMsg()">
          <button class="btn-send" onclick="sendMsg()"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
      </div>
      <p class="disclaimer">
        Farmazzini Intel pode cometer erros. Verifique informações importantes antes de tomar decisões estratégicas.
      </p>
    </div>
  </div>
</div>

<script>
// ── Estado inicial injetado pelo Python ──────────────────────
let chats       = {chats};
let activeChatId = {active_chat_id};
let activeDb     = "{active_db}";
let sidebarOpen  = true;

// ── Bridge para o Python (via query_params) ──────────────────
function toPython(action, params={{}}) {{
  const url = new URL(window.location.href);
  url.searchParams.set('action', action);
  for(const [k,v] of Object.entries(params)) url.searchParams.set(k,v);
  window.location.href = url.toString();
}}

// ── Init ─────────────────────────────────────────────────────
window.onload = () => {{ renderChatList(); renderChat(); }};

// ── Sidebar ──────────────────────────────────────────────────
function toggleSidebar() {{
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('collapsed', !sidebarOpen);
  document.getElementById('mainContent').classList.toggle('no-sidebar', !sidebarOpen);
  document.getElementById('bottomArea').classList.toggle('no-sidebar', !sidebarOpen);
}}

// ── DB Pills ─────────────────────────────────────────────────
// Muda localmente e envia ao Python (que salva e recarrega)
function setDb(db, el) {{
  toPython('set_db', {{db}});
}}

// ── Lista de chats ───────────────────────────────────────────
function renderChatList() {{
  const q = (document.getElementById('searchInput').value||'').toLowerCase();
  const list = document.getElementById('chatList');
  list.innerHTML = '';
  chats.filter(c => c.title.toLowerCase().includes(q)).forEach(chat => {{
    const div = document.createElement('div');
    div.className = 'chat-item' + (chat.id===activeChatId?' active':'');
    div.innerHTML = `
      <div class="chat-item-left" onclick="selectChat(${{chat.id}})">
        <i class="fa-regular fa-comment"></i>
        <span class="chat-title-span" id="title-${{chat.id}}"
              ondblclick="startRename(${{chat.id}})">${{chat.title}}</span>
      </div>
      <div class="chat-item-actions">
        <i class="fa-solid fa-pen action-icon" onclick="startRename(${{chat.id}})" title="Renomear"></i>
        <i class="fa-solid fa-trash-can action-icon" onclick="deleteChat(${{chat.id}})" title="Excluir"></i>
      </div>`;
    list.appendChild(div);
  }});
}}

// ── Renomear chat (inline, sem recarregar) ───────────────────
function startRename(id) {{
  const span = document.getElementById('title-'+id);
  if(!span) return;
  const old = span.textContent;
  const input = document.createElement('input');
  input.className = 'rename-input';
  input.value = old;
  span.replaceWith(input);
  input.focus(); input.select();
  const finish = () => {{
    const val = input.value.trim() || old;
    const chat = chats.find(c=>c.id===id);
    if(chat) chat.title = val;
    // Persiste no Python em background
    toPython('rename_chat', {{id, title: val}});
  }};
  input.onblur = finish;
  input.onkeypress = e => {{ if(e.key==='Enter') input.blur(); }};
}}

// ── Selecionar chat ──────────────────────────────────────────
function selectChat(id) {{
  toPython('select_chat', {{id}});
}}

// ── Excluir chat ─────────────────────────────────────────────
function deleteChat(id) {{
  if(chats.length<=1){{ alert('Mantenha ao menos um chat!'); return; }}
  if(confirm('Excluir este chat?')) toPython('delete_chat', {{id}});
}}

// ── Novo chat ─────────────────────────────────────────────────
function newChat() {{ toPython('new_chat'); }}

// ── Renderizar mensagens ─────────────────────────────────────
function renderChat() {{
  const win = document.getElementById('chatWindow');
  win.innerHTML = '';
  const chat = chats.find(c=>c.id===activeChatId);
  if(!chat) return;
  chat.messages.forEach(msg => {{
    const div = document.createElement('div');
    div.className = 'message '+msg.sender;
    div.innerHTML = `<div class="avatar">${{msg.sender==='user'?'PM':'FZ'}}</div>
                     <div class="msg-bubble">${{msg.text}}</div>`;
    win.appendChild(div);
  }});
  win.scrollTop = win.scrollHeight;
}}

// ── Enviar mensagem ───────────────────────────────────────────
function sendMsg() {{
  const inp = document.getElementById('userInput');
  const val = inp.value.trim();
  if(!val) return;
  inp.value = '';
  toPython('send', {{msg: val, db: activeDb}});
}}

// ── Botões quentes ────────────────────────────────────────────
function hotTrigger(type) {{
  const msgs = {{
    estoque: 'Quais itens com estoque crítico? Faça uma tabela comparando com a concorrência.',
    preco:   'Ache o produto mais barato do mercado e mostre a diferença para o preço da Farmazzini.',
    promos:  'Quais as maiores promoções de combos ou descontos progressivos da FarmaPonte ou Vera Cruz?'
  }};
  toPython('send', {{msg: msgs[type], db: activeDb}});
}}

// ── Toast CSV ─────────────────────────────────────────────────
function triggerCSV() {{
  const t = document.getElementById('toast');
  t.style.display='block';
  setTimeout(()=>t.style.display='none', 3500);
}}


</script>
</body>
</html>"""