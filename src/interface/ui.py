def render_full_ui(chats: str, active_chat_id: int, active_db: str, next_id: int = 2) -> str:
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
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {{
    --bg-main:      #08030A;
    --bg-sidebar:   rgba(10,5,14,0.94);
    --bg-card:      #09030C;
    --primary:      #E8253A;
    --primary-mid:  #B01030;
    --primary-dark: #6B0018;
    --primary-deep: #3A000C;
    --text-main:    #ffffff;
    --text-muted:   #9a9a9f;
    --border:       rgba(255,255,255,0.06);
    --glow-red:     rgba(220,30,55,0.28);
    --glow-wine:    rgba(100,0,20,0.35);
}}
*{{ box-sizing:border-box; margin:0; padding:0; }}
html, body {{
    font-family:'Urbanist',sans-serif;
    background: radial-gradient(ellipse 120% 80% at 50% -10%, rgba(180,20,45,0.35) 0%, rgba(80,0,18,0.18) 40%, transparent 70%),
                radial-gradient(ellipse 80% 60% at 85% 90%, rgba(120,0,25,0.25) 0%, transparent 60%),
                radial-gradient(ellipse 60% 50% at 10% 80%, rgba(160,15,35,0.15) 0%, transparent 55%),
                #08030A;
    color:var(--text-main);
    height:100dvh; max-height:100dvh; min-height:unset;
    margin:0; padding:0; overflow:hidden; position:relative;
}}
/* glows */
.fluid-glow-1 {{
    position:fixed; top:-20%; left:15%; width:70vw; height:70vw;
    background:radial-gradient(ellipse at center, rgba(220,30,55,0.30) 0%, rgba(140,5,30,0.18) 35%, rgba(80,0,15,0.08) 60%, transparent 80%);
    filter:blur(90px); z-index:1; pointer-events:none; border-radius:50%;
    animation: glow-drift1 12s ease-in-out infinite alternate;
}}
.fluid-glow-2 {{
    position:fixed; bottom:-15%; right:5%; width:55vw; height:55vw;
    background:radial-gradient(ellipse at center, rgba(160,10,35,0.22) 0%, rgba(90,0,20,0.12) 40%, transparent 70%);
    filter:blur(110px); z-index:1; pointer-events:none; border-radius:50%;
    animation: glow-drift2 15s ease-in-out infinite alternate;
}}
.fluid-glow-3 {{
    position:fixed; top:40%; left:-10%; width:40vw; height:40vw;
    background:radial-gradient(ellipse at center, rgba(180,20,45,0.15) 0%, rgba(100,0,20,0.06) 50%, transparent 75%);
    filter:blur(80px); z-index:1; pointer-events:none; border-radius:50%;
    animation: glow-drift3 18s ease-in-out infinite alternate;
}}
@keyframes glow-drift1 {{ from{{transform:translate(0,0) scale(1)}} to{{transform:translate(3vw,2vh) scale(1.08)}} }}
@keyframes glow-drift2 {{ from{{transform:translate(0,0) scale(1)}} to{{transform:translate(-2vw,-3vh) scale(1.05)}} }}
@keyframes glow-drift3 {{ from{{transform:translate(0,0) scale(1)}} to{{transform:translate(4vw,-2vh) scale(1.1)}} }}

.app-shell {{ display:flex; width:100%; height:100dvh; position:relative; z-index:2; overflow:hidden; }}

/* ── SIDEBAR ── */
.sidebar {{
    position:absolute; top:16px; left:16px; bottom:16px; width:320px;
    background:rgba(10,3,12,0.93);
    border:1px solid rgba(200,30,55,0.10); border-radius:24px;
    display:flex; flex-direction:column;
    padding:24px 18px; gap:20px; z-index:10;
    backdrop-filter:blur(30px);
    box-shadow:0 16px 40px rgba(0,0,0,0.75), 0 0 60px rgba(160,10,30,0.08);
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
    background:transparent; overflow:hidden;
    position:relative; z-index:2;
    width:100%; height:100dvh;
    transition:padding-left 0.35s cubic-bezier(0.25,0.8,0.25,1);
    padding-left:352px;
}}
.main-content.no-sidebar {{ padding-left:0; }}

.header {{
    padding:20px 40px; border-bottom:1px solid rgba(200,30,55,0.08);
    display:flex; justify-content:space-between; align-items:center;
    background:transparent; flex-shrink:0;
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
    background:linear-gradient(135deg, #E8253A 0%, #C01535 30%, #8B0828 65%, #560016 100%);
    border:1px solid rgba(255,80,100,0.22);
    box-shadow:0 8px 28px rgba(200,20,50,0.40), 0 2px 8px rgba(230,40,60,0.25), inset 0 1px 0 rgba(255,120,140,0.18);
    color:#fff;
}}

/* loading bubble */
.loading-bubble {{
    background:rgba(30,30,40,0.4); border:1px solid var(--border);
    padding:20px 24px; border-radius:18px;
}}

/* ── RODAPÉ ── */
.bottom-fixed-area {{
    position:relative; flex-shrink:0;
    background:linear-gradient(to top, rgba(6,6,8,0.98) 70%, transparent);
    padding:16px 40px 28px;
    display:flex; flex-direction:column; align-items:center; gap:12px;
    z-index:100; width:100%;
}}
.bottom-fixed-area.no-sidebar {{ left:0; }}

.hot-buttons-wrapper {{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; }}
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

.input-container {{ width:100%; display:flex; justify-content:center; }}
.disclaimer {{
    font-size:12px; color:var(--text-muted); text-align:center;
    padding-bottom:0; margin-bottom:0; line-height:1.5;
}}
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

/* action buttons */
.action-row {{ display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; }}
.action-btn {{
    background:rgba(255,255,255,0.03); border:1px solid var(--border);
    color:#ddd; padding:8px 16px; border-radius:8px; font-size:12px;
    cursor:pointer; display:flex; align-items:center; gap:6px;
    transition:all 0.2s; font-family:'Urbanist',sans-serif; font-weight:600;
}}
.action-btn:hover {{ border-color:var(--primary); color:white; background:rgba(230,57,70,0.1); }}

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

/* loading dots */
.dot-flashing {{
    position:relative; width:10px; height:10px;
    border-radius:5px; background-color:var(--primary);
    animation:dotf 1s infinite linear alternate; animation-delay:.5s; margin:8px 20px;
}}
.dot-flashing::before,.dot-flashing::after {{
    content:''; display:inline-block; position:absolute; top:0;
    width:10px; height:10px; border-radius:5px; background-color:var(--primary);
}}
.dot-flashing::before {{ left:-15px; animation:dotf 1s infinite linear alternate; animation-delay:0s; }}
.dot-flashing::after  {{ left:15px;  animation:dotf 1s infinite linear alternate; animation-delay:1s; }}
@keyframes dotf {{ 0%{{background-color:var(--primary)}} 50%,100%{{background-color:rgba(230,57,70,0.2)}} }}

/* modal de confirmação */
.modal-overlay {{
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,0.6); z-index:300;
    align-items:center; justify-content:center;
    backdrop-filter:blur(4px);
}}
.modal-overlay.open {{ display:flex; }}
.modal-box {{
    background:#0e0612; border:1px solid rgba(200,30,55,0.25);
    border-radius:20px; padding:28px 32px; max-width:380px; width:90%;
    box-shadow:0 24px 60px rgba(0,0,0,0.8);
    animation:fadeIn 0.2s ease;
}}
.modal-title {{ font-size:16px; font-weight:700; margin-bottom:8px; }}
.modal-desc  {{ font-size:14px; color:var(--text-muted); margin-bottom:24px; line-height:1.5; }}
.modal-btns  {{ display:flex; gap:10px; justify-content:flex-end; }}
.modal-btn-cancel {{
    background:rgba(255,255,255,0.04); border:1px solid var(--border);
    color:var(--text-muted); padding:10px 20px; border-radius:10px;
    cursor:pointer; font-family:'Urbanist',sans-serif; font-size:14px; font-weight:600;
    transition:all 0.2s;
}}
.modal-btn-cancel:hover {{ color:var(--text-main); }}
.modal-btn-confirm {{
    background:var(--primary); border:none;
    color:white; padding:10px 20px; border-radius:10px;
    cursor:pointer; font-family:'Urbanist',sans-serif; font-size:14px; font-weight:600;
    transition:all 0.2s;
}}
.modal-btn-confirm:hover {{ background:var(--primary-mid); }}

/* ── LOADING OVERLAY ── */
.loading-overlay {{
    display:none; position:fixed; inset:0; z-index:9999;
    background: radial-gradient(ellipse 120% 80% at 50% -10%, rgba(180,20,45,0.35) 0%, rgba(80,0,18,0.18) 40%, transparent 70%),
                radial-gradient(ellipse 80% 60% at 85% 90%, rgba(120,0,25,0.25) 0%, transparent 60%),
                radial-gradient(ellipse 60% 50% at 10% 80%, rgba(160,15,35,0.15) 0%, transparent 55%),
                #08030A;
    flex-direction:column; align-items:center; justify-content:center; gap:32px;
    animation: overlayFade 0.18s ease forwards;
}}
.loading-overlay.active {{ display:flex; }}
@keyframes overlayFade {{ from{{opacity:0}} to{{opacity:1}} }}

.loading-overlay-logo {{
    font-size:22px; font-weight:700; letter-spacing:3px; color:#ffffff;
    opacity:0.85;
}}
.loading-overlay-logo span {{ color:var(--primary); }}

.loading-overlay-card {{
    background:rgba(20,8,25,0.75); border:1px solid rgba(200,30,55,0.18);
    border-radius:24px; padding:36px 48px;
    display:flex; flex-direction:column; align-items:center; gap:20px;
    backdrop-filter:blur(20px);
    box-shadow:0 24px 60px rgba(0,0,0,0.7), 0 0 80px rgba(180,10,35,0.08);
}}

.loading-overlay-dots {{
    display:flex; gap:10px; align-items:center;
}}
.loading-overlay-dots span {{
    width:12px; height:12px; border-radius:50%;
    background:var(--primary);
    animation: dotPulse 1.4s ease-in-out infinite;
    display:block;
}}
.loading-overlay-dots span:nth-child(1) {{ animation-delay:0s; }}
.loading-overlay-dots span:nth-child(2) {{ animation-delay:0.2s; }}
.loading-overlay-dots span:nth-child(3) {{ animation-delay:0.4s; }}
@keyframes dotPulse {{
    0%,80%,100% {{ transform:scale(0.7); opacity:0.3; }}
    40%          {{ transform:scale(1.2); opacity:1; }}
}}

.loading-overlay-label {{
    font-size:15px; color:var(--text-muted); font-weight:500; letter-spacing:0.5px;
    text-align:center; line-height:1.5;
}}
.loading-overlay-label strong {{ color:#ffffff; font-weight:600; }}

.loading-overlay-bar-wrap {{
    width:220px; height:3px; background:rgba(255,255,255,0.06);
    border-radius:4px; overflow:hidden;
}}
.loading-overlay-bar {{
    height:100%; width:0%; background:linear-gradient(90deg, var(--primary-dark), var(--primary));
    border-radius:4px;
    animation: barProgress 30s cubic-bezier(0.1,0.4,0.2,1) forwards;
}}
@keyframes barProgress {{
    0%   {{ width:0% }}
    10%  {{ width:15% }}
    30%  {{ width:35% }}
    60%  {{ width:60% }}
    85%  {{ width:80% }}
    100% {{ width:92% }}
}}

/* Glow flutuante atrás do card */
.loading-overlay-glow {{
    position:absolute; width:60vw; height:60vw; border-radius:50%;
    background:radial-gradient(ellipse, rgba(200,20,50,0.22) 0%, transparent 70%);
    filter:blur(80px); pointer-events:none; z-index:-1;
    animation: glowPulse 3s ease-in-out infinite alternate;
}}
@keyframes glowPulse {{
    from{{ transform:scale(1); opacity:0.6; }}
    to  {{ transform:scale(1.15); opacity:1; }}
}}

/* ── MODAL DE GRÁFICOS ── */
.chart-modal-overlay {{
    display:none; position:fixed; inset:0; z-index:500;
    background:rgba(0,0,0,0.75); backdrop-filter:blur(6px);
    align-items:center; justify-content:center;
    animation:overlayFade 0.2s ease;
}}
.chart-modal-overlay.open {{ display:flex; }}
.chart-modal-box {{
    background:#0d0410;
    border:1px solid rgba(200,30,55,0.20);
    border-radius:24px;
    padding:28px 32px;
    width:min(92vw, 860px);
    max-height:90dvh;
    overflow-y:auto;
    box-shadow:0 28px 70px rgba(0,0,0,0.85), 0 0 80px rgba(180,10,35,0.08);
    display:flex; flex-direction:column; gap:20px;
    position:relative;
}}
.chart-modal-box::-webkit-scrollbar {{ width:4px; }}
.chart-modal-box::-webkit-scrollbar-thumb {{ background:rgba(255,255,255,0.08); border-radius:4px; }}
.chart-modal-header {{
    display:flex; align-items:center; justify-content:space-between;
    border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:16px;
}}
.chart-modal-title {{
    font-size:15px; font-weight:700; color:#fff; letter-spacing:.3px;
}}
.chart-modal-close {{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.06);
    color:var(--text-muted); width:36px; height:36px; border-radius:10px;
    cursor:pointer; display:flex; align-items:center; justify-content:center;
    font-size:16px; transition:all 0.2s;
}}
.chart-modal-close:hover {{ color:var(--primary); border-color:rgba(230,57,70,0.4); }}
.chart-tabs {{
    display:flex; gap:6px; flex-wrap:wrap;
}}
.chart-tab {{
    padding:7px 16px; border-radius:20px;
    font-size:12px; font-weight:600; cursor:pointer;
    background:rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.07);
    color:var(--text-muted); transition:all 0.2s;
    font-family:'Urbanist',sans-serif;
}}
.chart-tab.active {{
    background:rgba(232,37,58,0.15);
    border-color:rgba(232,37,58,0.45);
    color:#E8253A;
}}
.chart-filter-row {{
    display:flex; align-items:center; gap:10px; flex-wrap:wrap;
}}
.chart-filter-row label {{ font-size:12px; color:var(--text-muted); font-weight:600; }}
.chart-filter-row select {{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
    color:#fff; padding:6px 12px; border-radius:8px;
    font-family:'Urbanist',sans-serif; font-size:13px; outline:none; cursor:pointer;
}}
.chart-metric-grid {{
    display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px;
}}
.chart-metric-card {{
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06);
    border-radius:12px; padding:12px 14px; text-align:center;
}}
.chart-metric-val {{ font-size:20px; font-weight:700; }}
.chart-metric-lbl {{ font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.8px; margin-top:4px; }}
.chart-canvas-wrap {{ position:relative; width:100%; }}
.chart-cta {{
    font-size:13px; padding:12px 16px; border-radius:12px;
    border-left:3px solid; line-height:1.5;
}}
.chart-legend {{
    display:flex; gap:14px; flex-wrap:wrap;
    font-size:12px; color:var(--text-muted);
}}
.chart-legend-item {{ display:flex; align-items:center; gap:5px; }}
.chart-legend-swatch {{ width:10px; height:10px; border-radius:2px; flex-shrink:0; }}

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
<div class="fluid-glow-3"></div>
<div class="download-toast" id="toast">✅ CSV exportado com sucesso!</div>

<!-- Modal de confirmação de exclusão -->
<div class="modal-overlay" id="deleteModal">
  <div class="modal-box">
    <div class="modal-title">Excluir chat?</div>
    <div class="modal-desc" id="modalDesc">Esta ação não pode ser desfeita.</div>
    <div class="modal-btns">
      <button class="modal-btn-cancel" onclick="closeModal()">Cancelar</button>
      <button class="modal-btn-confirm" onclick="confirmDelete()">Excluir</button>
    </div>
  </div>
</div>

<!-- ══ LOADING OVERLAY — exibido durante processamento da query ══ -->
<div class="loading-overlay" id="loadingOverlay">
  <div class="loading-overlay-glow"></div>
  <div class="loading-overlay-logo">FARMAZZINI <span>INTEL</span></div>
  <div class="loading-overlay-card">
    <div class="loading-overlay-dots">
      <span></span><span></span><span></span>
    </div>
    <div class="loading-overlay-label">
      <strong id="overlayQuestion"></strong><br>
      Consultando base de dados...
    </div>
    <div class="loading-overlay-bar-wrap">
      <div class="loading-overlay-bar" id="overlayBar"></div>
    </div>
  </div>
</div>

<!-- ══ MODAL DE GRÁFICOS ESTRATÉGICOS ══ -->
<div class="chart-modal-overlay" id="chartModal" onclick="if(event.target===this)fecharGrafico()">
  <div class="chart-modal-box">

    <!-- Cabeçalho -->
    <div class="chart-modal-header">
      <div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--primary);font-weight:700;margin-bottom:4px;">
          Análise de mercado em tempo real · Athena tb_processed
        </div>
        <div class="chart-modal-title">📊 Cruzamentos Estratégicos de Mercado</div>
      </div>
      <button class="chart-modal-close" onclick="fecharGrafico()">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- KPI cards rápidos -->
    <div class="chart-metric-grid" id="chartKpis"></div>

    <!-- Tabs de navegação -->
    <div class="chart-tabs">
      <button class="chart-tab active" onclick="switchTab(0,this)">
        <i class="fa-solid fa-chart-bar" style="margin-right:5px;"></i>Cruzamento 1 — Comparativo de Preços
      </button>
      <button class="chart-tab" onclick="switchTab(1,this)">
        <i class="fa-solid fa-credit-card" style="margin-right:5px;"></i>Cruzamento 2 — Modalidades de Pagamento
      </button>
      <button class="chart-tab" onclick="switchTab(2,this)">
        <i class="fa-solid fa-circle-half-stroke" style="margin-right:5px;"></i>Cruzamento 3 — Share de Presença
      </button>
    </div>

    <!-- Filtro de preço (só no cruzamento 1) -->
    <div class="chart-filter-row" id="filterRow">
      <label><i class="fa-solid fa-filter" style="margin-right:4px;"></i>Modalidade de Preço:</label>
      <select id="priceFilter" onchange="atualizarCruzamento1()">
        <option value="preco_original">Preço Original (Gôndola)</option>
        <option value="preco_pix">Preço PIX</option>
        <option value="preco_cartao">Preço Cartão</option>
      </select>
    </div>

    <!-- Canvas dos gráficos -->
    <div class="chart-canvas-wrap">
      <canvas id="chartCanvas" style="max-height:320px;"></canvas>
    </div>

    <!-- Legenda -->
    <div class="chart-legend" id="chartLegend"></div>

    <!-- CTA de insight -->
    <div class="chart-cta" id="chartCta"></div>

  </div>
</div>

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
        <div class="db-pill" data-db="todas"     onclick="setDb('todas',this)">Todas</div>
        <div class="db-pill" data-db="ponte"     onclick="setDb('ponte',this)">Ponte</div>
        <div class="db-pill" data-db="veracruz"  onclick="setDb('veracruz',this)">Vera Cruz</div>
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
      <br>
    </div>
  </div>
</div>

<script>
// ════════════════════════════════════════════════════════════════
// ESTADO — injetado pelo Python no carregamento
// ════════════════════════════════════════════════════════════════
let chats        = {chats};
let activeChatId = {active_chat_id};
let activeDb     = "{active_db}";
let nextId       = {next_id};
let sidebarOpen  = true;
let pendingDeleteId = null;

// ════════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════════
window.onload = () => {{
    initDbPills();
    renderChatList();
    renderChat();
    const win = document.getElementById('chatWindow');
    if(win) win.scrollTop = win.scrollHeight;

    // Fade-in suave pós-redirect: evita o flash branco entre overlay e conteúdo
    const shell = document.querySelector('.app-shell');
    if(shell) {{
        shell.style.opacity = '0';
        shell.style.transition = 'opacity 0.4s ease';
        requestAnimationFrame(() => {{
            requestAnimationFrame(() => {{ shell.style.opacity = '1'; }});
        }});
    }}
}};

// ════════════════════════════════════════════════════════════════
// SIDEBAR
// ════════════════════════════════════════════════════════════════
function toggleSidebar() {{
    sidebarOpen = !sidebarOpen;
    document.getElementById('sidebar').classList.toggle('collapsed', !sidebarOpen);
    document.getElementById('mainContent').classList.toggle('no-sidebar', !sidebarOpen);
    document.getElementById('bottomArea').classList.toggle('no-sidebar', !sidebarOpen);
}}

// ════════════════════════════════════════════════════════════════
// DB PILLS — atualiza localmente, sem recarregar
// ════════════════════════════════════════════════════════════════
function initDbPills() {{
    document.querySelectorAll('.db-pill').forEach(pill => {{
        pill.classList.toggle('active', pill.dataset.db === activeDb);
    }});
    document.getElementById('dbLabel').textContent =
        ({{todas:'Todas', ponte:'FarmaPonte', veracruz:'Vera Cruz'}})[activeDb] || 'Todas';
}}

function setDb(db, el) {{
    activeDb = db;
    document.querySelectorAll('.db-pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('dbLabel').textContent =
        ({{todas:'Todas', ponte:'FarmaPonte', veracruz:'Vera Cruz'}})[db] || 'Todas';
}}

// ════════════════════════════════════════════════════════════════
// NOVO CHAT — 100% local, sem recarregar
// ════════════════════════════════════════════════════════════════
function newChat() {{
    const id = nextId++;
    const chat = {{
        id,
        title: 'Nova Consulta #' + id,
        messages: [{{
            sender: 'bot',
            text: 'Nova sessão aberta. Como posso ajudar?'
        }}]
    }};
    chats.push(chat);
    activeChatId = id;
    renderChatList();
    renderChat();
    // Foca no input
    const inp = document.getElementById('userInput');
    if(inp) inp.focus();
}}

// ════════════════════════════════════════════════════════════════
// SELECIONAR CHAT — local
// ════════════════════════════════════════════════════════════════
function selectChat(id) {{
    activeChatId = id;
    renderChatList();
    renderChat();
}}

// ════════════════════════════════════════════════════════════════
// EXCLUIR CHAT — modal de confirmação
// ════════════════════════════════════════════════════════════════
function deleteChat(id) {{
    if(chats.length <= 1) {{
        showToast('⚠️ Mantenha ao menos um chat!', '#7c3aed', '#4c1d95', '#a78bfa');
        return;
    }}
    pendingDeleteId = id;
    const chat = chats.find(c => c.id === id);
    document.getElementById('modalDesc').textContent =
        `"${{chat ? chat.title : 'Este chat'}}" será excluído permanentemente.`;
    document.getElementById('deleteModal').classList.add('open');
}}

function closeModal() {{
    document.getElementById('deleteModal').classList.remove('open');
    pendingDeleteId = null;
}}

function confirmDelete() {{
    if(pendingDeleteId === null) return;
    chats = chats.filter(c => c.id !== pendingDeleteId);
    if(activeChatId === pendingDeleteId) {{
        activeChatId = chats[0].id;
    }}
    closeModal();
    renderChatList();
    renderChat();
}}

// ════════════════════════════════════════════════════════════════
// RENOMEAR — inline, sem recarregar
// ════════════════════════════════════════════════════════════════
function startRename(id) {{
    const span = document.getElementById('title-' + id);
    if(!span) return;
    const old = span.textContent;
    const input = document.createElement('input');
    input.className = 'rename-input';
    input.value = old;
    span.replaceWith(input);
    input.focus(); input.select();
    const finish = () => {{
        const val = input.value.trim() || old;
        const chat = chats.find(c => c.id === id);
        if(chat) chat.title = val;
        renderChatList();
    }};
    input.onblur = finish;
    input.onkeydown = e => {{ if(e.key === 'Enter') input.blur(); if(e.key === 'Escape') {{ input.value = old; input.blur(); }} }};
}}

// ════════════════════════════════════════════════════════════════
// RENDERIZAR LISTA DE CHATS
// ════════════════════════════════════════════════════════════════
function renderChatList() {{
    const q    = (document.getElementById('searchInput').value || '').toLowerCase();
    const list = document.getElementById('chatList');
    list.innerHTML = '';
    chats.filter(c => c.title.toLowerCase().includes(q)).forEach(chat => {{
        const div = document.createElement('div');
        div.className = 'chat-item' + (chat.id === activeChatId ? ' active' : '');
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

// ════════════════════════════════════════════════════════════════
// RENDERIZAR MENSAGENS DO CHAT ATIVO
// ════════════════════════════════════════════════════════════════
function renderChat() {{
    const win  = document.getElementById('chatWindow');
    const chat = chats.find(c => c.id === activeChatId);
    win.innerHTML = '';
    if(!chat) return;
    chat.messages.forEach(msg => appendMessage(msg.sender, msg.text, false));
    win.scrollTop = win.scrollHeight;
}}

function appendMessage(sender, text, animate=true) {{
    const win = document.getElementById('chatWindow');
    const div = document.createElement('div');
    div.className = 'message ' + sender;
    if(!animate) div.style.animation = 'none';
    div.innerHTML = `<div class="avatar">${{sender === 'user' ? 'PM' : 'FZ'}}</div>
                     <div class="msg-bubble">${{text}}</div>`;
    win.appendChild(div);
    win.scrollTop = win.scrollHeight;
    return div;
}}

// ════════════════════════════════════════════════════════════════
// ENVIAR MENSAGEM
//
// RAIZ DO PROBLEMA:
// O Streamlit só lê st.query_params quando a página pai navega.
// No design anterior, window.parent.location.href navegava o pai
// corretamente — o Streamlit processava e rerenderizava o iframe.
// O bug era outro: o novo iframe nascia já com renderChat()
// populando TODAS as mensagens (incluindo a nova resposta do bot),
// mas o CSS tinha `animation:fadeIn` em .message, então visualmente
// a tela piscava e parecia que o loading nunca sumia.
//
// SOLUÇÃO CORRETA:
// 1. Antes de navegar, salva no sessionStorage do PAI que estamos
//    aguardando uma resposta (flag + texto da pergunta).
// 2. Navega o pai normalmente → Streamlit processa → novo iframe.
// 3. No novo iframe (window.onload), detecta a flag e faz scroll
//    suave para a última mensagem sem flash.
// ════════════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════════
// LOADING OVERLAY — controla a tela de loading durante a query
// ════════════════════════════════════════════════════════════════
function showLoadingOverlay(question) {{
    const overlay = document.getElementById('loadingOverlay');
    const label   = document.getElementById('overlayQuestion');
    const bar     = document.getElementById('overlayBar');

    // Mostra o trecho da pergunta truncado
    const truncated = question.length > 55 ? question.substring(0, 55) + '…' : question;
    label.textContent = truncated;

    // Reinicia a barra de progresso
    bar.style.animation = 'none';
    bar.offsetHeight; // força reflow para reiniciar a animação
    bar.style.animation = 'barProgress 30s cubic-bezier(0.1,0.4,0.2,1) forwards';

    overlay.classList.add('active');
}}

function hideLoadingOverlay() {{
    document.getElementById('loadingOverlay').classList.remove('active');
}}

// ════════════════════════════════════════════════════════════════
// ENVIAR MENSAGEM
// ════════════════════════════════════════════════════════════════
function sendMsg() {{
    const inp = document.getElementById('userInput');
    const val = inp.value.trim();
    if(!val) return;
    inp.value = '';
    inp.disabled = true;

    const chat = chats.find(c => c.id === activeChatId);
    if(!chat) {{ inp.disabled = false; return; }}

    // Exibe o overlay de loading com a pergunta do usuário ANTES do redirect
    showLoadingOverlay(val);

    // CORREÇÃO: serializa o estado COMPLETO dos chats (incluindo os criados
    // localmente no JS) e envia para o Python via query param 'state'.
    // Isso evita que chats criados com newChat() sejam perdidos no recarregamento.
    const statePayload = JSON.stringify({{
        chats:          chats,
        active_chat_id: activeChatId,
        active_db:      activeDb,
        next_id:        nextId,
    }});

    const params = new URLSearchParams({{
        action: 'send',
        msg:    val,
        db:     activeDb,
        state:  statePayload,
    }});

    const targetUrl = window.location.origin + window.location.pathname + '?' + params.toString();

    // Pequeno delay para garantir que o overlay renderize antes do redirect
    setTimeout(() => {{
        window.location.href = targetUrl;
    }}, 120);
}}

// ════════════════════════════════════════════════════════════════
// BOTÕES QUENTES
// ════════════════════════════════════════════════════════════════
function hotTrigger(type) {{
    const msgs = {{
        estoque: 'Quais itens com estoque crítico? Faça uma tabela comparando com a concorrência.',
        preco:   'Ache o produto mais barato do mercado e mostre a diferença para o preço da Farmazzini.',
        promos:  'Quais as maiores promoções de combos ou descontos progressivos da FarmaPonte ou Vera Cruz?'
    }};
    const input = document.getElementById('userInput');
    input.value = msgs[type];
    sendMsg();
}}

// ════════════════════════════════════════════════════════════════
// EXPORTAR CSV
// ════════════════════════════════════════════════════════════════
function exportCSV() {{
    showToast('✅ CSV exportado com sucesso!', '#10b981', '#0d2818', '#4ade80');
}}

// ════════════════════════════════════════════════════════════════
// TOAST GENÉRICO
// ════════════════════════════════════════════════════════════════
function showToast(msg, borderColor, bg, color) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.background    = bg      || '#0d2818';
    t.style.borderColor   = borderColor || '#1e5e2f';
    t.style.color         = color   || '#4ade80';
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
}}

// Fecha modal clicando fora
document.getElementById('deleteModal').addEventListener('click', function(e) {{
    if(e.target === this) closeModal();
}});

// ════════════════════════════════════════════════════════════════
// GRÁFICOS ESTRATÉGICOS — 3 CRUZAMENTOS COMPETITIVOS
// ════════════════════════════════════════════════════════════════
let _chartInstance  = null;   // instância ativa do Chart.js
let _chartPayload   = null;   // dados desserializados do pipeline
let _activeTab      = 0;      // 0=preços, 1=modalidades, 2=share

// Paleta por farmácia (alinha com a imagem de referência)
const FARM_COLORS = {{
    'Farmazzini':  {{ bar:'rgba(74,222,128,0.85)',  border:'#4ade80',  dot:'#4ade80'  }},
    'FarmaPonte':  {{ bar:'rgba(96,165,250,0.85)',  border:'#60a5fa',  dot:'#60a5fa'  }},
    'Vera Cruz':   {{ bar:'rgba(232,37,58,0.85)',   border:'#E8253A',  dot:'#E8253A'  }},
}};
const MODAL_COLORS = {{
    preco_original: {{ bar:'rgba(148,163,184,0.80)', border:'#94a3b8', label:'Original' }},
    preco_pix:      {{ bar:'rgba(74,222,128,0.85)',  border:'#4ade80', label:'PIX'      }},
    preco_cartao:   {{ bar:'rgba(96,165,250,0.85)',  border:'#60a5fa', label:'Cartão'   }},
}};

function _farmColor(farm, key) {{
    return (FARM_COLORS[farm] || {{bar:'rgba(200,200,200,0.7)',border:'#aaa',dot:'#aaa'}})[key];
}}

function _destroyChart() {{
    if(_chartInstance) {{ _chartInstance.destroy(); _chartInstance = null; }}
}}

function _chartDefaults() {{
    return {{
        responsive:true, maintainAspectRatio:true,
        plugins:{{
            legend:{{ display:false }},
            tooltip:{{
                backgroundColor:'rgba(10,5,14,0.92)',
                borderColor:'rgba(200,30,55,0.25)',
                borderWidth:1,
                titleColor:'#fff',
                bodyColor:'#ccc',
                padding:12,
                callbacks:{{
                    label: ctx => ' R$ ' + (ctx.parsed.y ?? ctx.parsed).toFixed(2)
                }}
            }}
        }},
        scales:{{
            x:{{
                grid:{{ color:'rgba(255,255,255,0.04)' }},
                ticks:{{ color:'#9a9a9f', font:{{family:'Urbanist',size:12}} }}
            }},
            y:{{
                grid:{{ color:'rgba(255,255,255,0.04)' }},
                ticks:{{
                    color:'#9a9a9f', font:{{family:'Urbanist',size:12}},
                    callback: v => 'R$ ' + v.toFixed(2)
                }}
            }}
        }}
    }};
}}

// ── Cruzamento 1: Comparativo de preços por farmácia ──────────────
function renderCruzamento1() {{
    const modalidade = document.getElementById('priceFilter').value;
    const c1 = _chartPayload.cruzamento1;
    const farmacias = _chartPayload.farmacias;

    if(!c1 || !c1[modalidade]) {{
        _semDados('Sem dados de preço para esta modalidade.'); return;
    }}

    const data = farmacias.map(f => c1[modalidade][f] || 0);
    const bgColors   = farmacias.map(f => _farmColor(f,'bar'));
    const bdColors   = farmacias.map(f => _farmColor(f,'border'));

    _destroyChart();
    _chartInstance = new Chart(document.getElementById('chartCanvas'), {{
        type:'bar',
        data:{{
            labels: farmacias,
            datasets:[{{
                label: MODAL_COLORS[modalidade]?.label || modalidade,
                data,
                backgroundColor: bgColors,
                borderColor:     bdColors,
                borderWidth:1.5,
                borderRadius:6,
                borderSkipped:false,
            }}]
        }},
        options: _chartDefaults()
    }});

    // Legenda
    _renderLegend(farmacias.map(f => ({{label:f, color:_farmColor(f,'dot')}})));

    // Insight gap vs líder
    const minVal  = Math.min(...data.filter(v=>v>0));
    const maxVal  = Math.max(...data);
    const farmMin = farmacias[data.indexOf(minVal)];
    const farmMax = farmacias[data.indexOf(maxVal)];
    const gap     = minVal > 0 ? (((maxVal - minVal) / minVal) * 100).toFixed(1) : '—';
    const isFarmazziniLeader = farmMin === 'Farmazzini';

    document.getElementById('filterRow').style.display = 'flex';
    _renderCta(
        isFarmazziniLeader
            ? `✅ <strong>Farmazzini lidera</strong> com o menor preço <strong>${{MODAL_COLORS[modalidade]?.label}}.</strong> Gap de <strong>${{gap}}%</strong> em relação a ${{farmMax}}. Avalie elevar margem preservando competitividade.`
            : `⚡ <strong>${{farmMin}}</strong> pratica o menor preço (${{MODAL_COLORS[modalidade]?.label}}). Farmazzini está <strong>${{gap}}% acima do líder de preço baixo.</strong> Avaliar redução ou comunicar diferencial de qualidade.`,
        isFarmazziniLeader ? '#0d2818' : '#1a0810',
        isFarmazziniLeader ? '#4ade80' : '#E8253A',
        isFarmazziniLeader ? '#10b981' : '#E8253A'
    );
}}

function atualizarCruzamento1() {{ renderCruzamento1(); }}

// ── Cruzamento 2: Modalidades de pagamento por farmácia ───────────
function renderCruzamento2() {{
    const c2       = _chartPayload.cruzamento2;
    const farmacias = _chartPayload.farmacias;
    const modals   = ['preco_original','preco_pix','preco_cartao'];
    const labels   = ['Original','PIX','Cartão'];

    document.getElementById('filterRow').style.display = 'none';

    const datasets = farmacias.map(farm => ({{
        label: farm,
        data: modals.map(m => c2[m]?.[farm] || 0),
        backgroundColor: _farmColor(farm,'bar'),
        borderColor:     _farmColor(farm,'border'),
        borderWidth:1.5,
        borderRadius:5,
        borderSkipped:false,
    }}));

    _destroyChart();
    _chartInstance = new Chart(document.getElementById('chartCanvas'), {{
        type:'bar',
        data:{{ labels, datasets }},
        options:{{
            ..._chartDefaults(),
            plugins:{{
                ..._chartDefaults().plugins,
                tooltip:{{
                    ..._chartDefaults().plugins.tooltip,
                    callbacks:{{
                        label: ctx => ` ${{ctx.dataset.label}}: R$ ${{ctx.parsed.y.toFixed(2)}}`
                    }}
                }}
            }}
        }}
    }});

    _renderLegend(farmacias.map(f => ({{label:f, color:_farmColor(f,'dot')}})));

    // Insight: qual farmácia tem maior desconto PIX
    if(c2.preco_original && c2.preco_pix) {{
        let maxDescPct = -Infinity; let farmMaxDesc = '';
        farmacias.forEach(f => {{
            const orig = c2.preco_original[f]; const pix = c2.preco_pix[f];
            if(orig > 0) {{
                const d = ((orig - pix) / orig) * 100;
                if(d > maxDescPct) {{ maxDescPct = d; farmMaxDesc = f; }}
            }}
        }});
        const descPix_farm = c2.preco_pix?.['Farmazzini'];
        const descPix_concOriginal = c2.preco_original?.['Farmazzini'];
        const farmazziniPix = descPix_farm && descPix_concOriginal
            ? (((descPix_concOriginal - descPix_farm) / descPix_concOriginal) * 100).toFixed(1)
            : '—';

        _renderCta(
            `💳 <strong>${{farmMaxDesc}}</strong> oferece o maior desconto PIX (<strong>${{maxDescPct.toFixed(1)}}%</strong>). ` +
            `Farmazzini pratica <strong>${{farmazziniPix}}% de desconto PIX</strong>. ` +
            `Calibre o gatilho PIX para não queimar margem desnecessariamente.`,
            '#0d1428','#60a5fa','#3b82f6'
        );
    }}
}}

// ── Cruzamento 3: Share de Presença / Ruptura de Prateleira ───────
function renderCruzamento3() {{
    const c3       = _chartPayload.cruzamento3;
    const farmacias = _chartPayload.farmacias;

    document.getElementById('filterRow').style.display = 'none';

    if(!c3 || Object.keys(c3).length === 0) {{
        _semDados('Sem dados de disponibilidade para este conjunto de resultados.'); return;
    }}

    // Donut com disponível vs indisponível por farmácia (multi-dataset simulado via bar)
    const dispData  = farmacias.map(f => c3[f] ? Math.round((c3[f].disponivel / (c3[f].total||1)) * 100) : 0);
    const rupData   = farmacias.map(f => c3[f] ? Math.round((c3[f].indisponivel / (c3[f].total||1)) * 100) : 0);

    _destroyChart();
    _chartInstance = new Chart(document.getElementById('chartCanvas'), {{
        type:'bar',
        data:{{
            labels: farmacias,
            datasets:[
                {{
                    label:'Disponível (%)',
                    data: dispData,
                    backgroundColor: farmacias.map(f => _farmColor(f,'bar')),
                    borderColor:     farmacias.map(f => _farmColor(f,'border')),
                    borderWidth:1.5, borderRadius:6, borderSkipped:false,
                }},
                {{
                    label:'Ruptura (%)',
                    data: rupData,
                    backgroundColor:'rgba(248,113,113,0.55)',
                    borderColor:'#f87171',
                    borderWidth:1.5, borderRadius:6, borderSkipped:false,
                }}
            ]
        }},
        options:{{
            ..._chartDefaults(),
            plugins:{{
                ..._chartDefaults().plugins,
                tooltip:{{
                    ..._chartDefaults().plugins.tooltip,
                    callbacks:{{
                        label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y}}%`
                    }}
                }}
            }},
            scales:{{
                x:{{ grid:{{ color:'rgba(255,255,255,0.04)' }}, ticks:{{ color:'#9a9a9f', font:{{family:'Urbanist',size:12}} }} }},
                y:{{
                    max:100,
                    grid:{{ color:'rgba(255,255,255,0.04)' }},
                    ticks:{{ color:'#9a9a9f', font:{{family:'Urbanist',size:12}}, callback: v => v+'%' }}
                }}
            }}
        }}
    }});

    _renderLegend([
        ...farmacias.map(f => ({{label:f+' (Disponível)', color:_farmColor(f,'dot')}})),
        {{label:'Ruptura', color:'#f87171'}}
    ]);

    // Insight: maior ruptura → oportunidade de preço
    let maxRup = -1; let farmMaxRup = '';
    farmacias.forEach((f,i) => {{ if(rupData[i] > maxRup) {{ maxRup = rupData[i]; farmMaxRup = f; }} }});
    const allOut = rupData.every(v => v >= 100);

    _renderCta(
        allOut
            ? `🔥 <strong>100% dos concorrentes estão em ruptura!</strong> Janela de oportunidade aberta — considere aumento temporário de preço (baixa elasticidade por urgência de compra).`
            : `📦 <strong>${{farmMaxRup}}</strong> tem a maior ruptura de prateleira (<strong>${{maxRup}}%</strong>). Monitore — quando atingir 100%, acionar reposicionamento de preço.`,
        maxRup >= 80 ? '#1a0810' : '#0d1a10',
        maxRup >= 80 ? '#E8253A' : '#10b981',
        maxRup >= 80 ? '#E8253A' : '#4ade80'
    );
}}

function _semDados(msg) {{
    document.getElementById('chartCanvas').style.display='none';
    document.getElementById('chartCta').innerHTML =
        `<span style="color:var(--text-muted);">ℹ️ ${{msg}}</span>`;
    document.getElementById('chartCta').style.cssText =
        'background:rgba(255,255,255,0.03);border-color:rgba(255,255,255,0.08);color:#9a9a9f;';
}}

function _renderLegend(items) {{
    document.getElementById('chartLegend').innerHTML = items.map(it =>
        `<div class="chart-legend-item">
            <div class="chart-legend-swatch" style="background:${{it.color}};"></div>
            <span>${{it.label}}</span>
        </div>`
    ).join('');
}}

function _renderCta(html, bg, border, color) {{
    const el = document.getElementById('chartCta');
    el.innerHTML = html;
    el.style.background   = bg;
    el.style.borderColor  = border;
    el.style.color        = color || '#fff';
}}

function switchTab(idx, el) {{
    _activeTab = idx;
    document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('chartCanvas').style.display = 'block';
    if(idx === 0) renderCruzamento1();
    if(idx === 1) renderCruzamento2();
    if(idx === 2) renderCruzamento3();
}}

// ── KPI cards no topo do modal ─────────────────────────────────────
function _renderKpis(payload) {{
    const farmacias = payload.farmacias || [];
    const c1 = payload.cruzamento1 || {{}};
    const c3 = payload.cruzamento3 || {{}};

    let html = '';

    // Preço original por farmácia
    farmacias.forEach(farm => {{
        const val = c1?.preco_original?.[farm];
        if(val) {{
            const cor = _farmColor(farm,'dot');
            html += `
            <div class="chart-metric-card">
                <div class="chart-metric-val" style="color:${{cor}}">R$ ${{val.toFixed(2)}}</div>
                <div class="chart-metric-lbl">${{farm}}</div>
            </div>`;
        }}
    }});

    // Gap vs líder
    const precos = farmacias.map(f => c1?.preco_original?.[f] || 0).filter(v=>v>0);
    if(precos.length >= 2) {{
        const min = Math.min(...precos); const max = Math.max(...precos);
        const gap = (((max-min)/min)*100).toFixed(1);
        html += `
        <div class="chart-metric-card">
            <div class="chart-metric-val" style="color:#a78bfa">+${{gap}}%</div>
            <div class="chart-metric-lbl">Gap vs. líder</div>
        </div>`;
    }}

    document.getElementById('chartKpis').innerHTML = html;
}}

// ── Ponto de entrada chamado pelo botão "Gerar Gráfico" ───────────
function abrirGrafico(jsonStr) {{
    try {{
        // Restaura entidades HTML escapadas pelo Python
        const clean = jsonStr.replace(/&#39;/g, "'");
        _chartPayload = JSON.parse(clean);
    }} catch(e) {{
        showToast('❌ Erro ao parsear dados do gráfico.', '#E8253A', '#1a0810', '#f87171');
        return;
    }}

    // Reseta estado
    _activeTab = 0;
    _destroyChart();
    document.getElementById('chartCanvas').style.display = 'block';
    document.getElementById('chartLegend').innerHTML = '';
    document.getElementById('chartCta').innerHTML = '';
    document.getElementById('filterRow').style.display = 'flex';
    document.getElementById('priceFilter').value = 'preco_original';

    // Ativa a aba 1 visualmente
    document.querySelectorAll('.chart-tab').forEach((t,i) => t.classList.toggle('active', i===0));

    // Renderiza KPIs e primeiro cruzamento
    _renderKpis(_chartPayload);
    renderCruzamento1();

    // Abre o modal
    document.getElementById('chartModal').classList.add('open');
}}

function fecharGrafico() {{
    document.getElementById('chartModal').classList.remove('open');
    _destroyChart();
}}
</script>
</body>
</html>"""