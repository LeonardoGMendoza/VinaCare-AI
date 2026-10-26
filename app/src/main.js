import { TalkingHead } from './talkinghead/talkinghead.mjs';
import { LipsyncPt_br } from './talkinghead/lipsync-pt_br.mjs';
window.__vinaStarted = true;

const AVATARS = {
  avaturn: { url: './avatars/avaturn.glb', body: 'F', avatarMood: 'happy', lipsyncLang: 'pt_br',
    retarget: { Hips:{y:0.03}, Spine:{y:0.02}, Spine1:{y:0.02,z:0.01}, Spine2:{y:0.02,z:0.01}, Neck:{z:0.02,y:0.01}, Head:{z:0.02}, LeftShoulder:{rx:-0.5}, RightShoulder:{rx:-0.5}, scaleToHipsLevel:1.0 },
    baseline: { headRotateX:-0.05, eyeBlinkLeft:0.15, eyeBlinkRight:0.15 } },
  avatarsdk: { url: './avatars/avatarsdk.glb', body: 'M', avatarMood: 'happy', lipsyncLang: 'pt_br',
    retarget: { Neck:{z:-0.01,rx:-0.15}, Neck1:{z:-0.01,rx:-0.15}, Neck2:{z:-0.01,rx:-0.15}, LeftShoulder:{rz:-0.3}, RightShoulder:{rz:0.3}, scaleToEyesLevel:1.0, origin:{y:-0.1} },
    baseline: { headRotateX:-0.04, eyeBlinkLeft:0.05, eyeBlinkRight:0.05 } }
};

const $ = id => document.getElementById(id);
const status = (t) => { $('status').hidden = !t; if (t) $('status').textContent = t; };
let head = null, current = 'avaturn', loading = false;
const NOMES = { avaturn: 'Clara', avatarsdk: 'Rafael' };
const assistente = () => NOMES[current] || 'Clara';

async function load(key){
  if (loading) return;
  loading = true; current = key;
  document.querySelectorAll('[data-av]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.av === key)));
  const t = document.getElementById('convTitulo'); if (t) t.textContent = 'Converse com ' + (key === 'avatarsdk' ? 'ele' : 'ela');
  status('Carregando o avatar… 0%');
  try {
    await head.showAvatar(AVATARS[key], ev => {
      if (ev.lengthComputable) status('Carregando o avatar… ' + Math.round(ev.loaded / ev.total * 100) + '%');
      else if (ev.loaded) status('Carregando o avatar… ' + (ev.loaded / 1e6).toFixed(1) + ' MB');
    });
    head.setView('upper');
    status('');
  } catch (e) {
    console.error(e);
    status('Não consegui carregar o avatar. Atualize a página e tente de novo.');
  }
  loading = false;
}

// Vozes em português do aparelho
function vozNota(v){
  // Prefere vozes de alta qualidade em português do Brasil
  const n = (v.name + ' ' + (v.voiceURI || '')).toLowerCase();
  let p = 0;
  if (/^pt[-_]br/i.test(v.lang)) p += 100; else if (/^pt/i.test(v.lang)) p += 10;
  if (/premium/.test(n)) p += 50;
  if (/enhanced|aprimorad|natural|neural|online/.test(n)) p += 40;
  if (/luciana|francisca|thalita|google portugu/.test(n)) p += 15;
  if (/compact|eloquence|novelty/.test(n)) p -= 30;
  return p;
}
function fillVoices(){
  const vs = (speechSynthesis.getVoices() || []).filter(v => /^pt/i.test(v.lang));
  const sel = $('voice'); const prev = sel.value; sel.innerHTML = '';
  if (!vs.length){ const o = document.createElement('option'); o.textContent = 'Padrão do aparelho'; o.value = ''; sel.appendChild(o); return; }
  vs.sort((a,b) => vozNota(b) - vozNota(a));
  vs.forEach(v => { const o = document.createElement('option'); o.value = v.name; o.textContent = v.name.replace(/Microsoft |Google /,'') + ' (' + v.lang + ')'; sel.appendChild(o); });
  if (prev && vs.some(v => v.name === prev)) sel.value = prev;
}
if ('speechSynthesis' in window){ fillVoices(); speechSynthesis.onvoiceschanged = fillVoices; }

// Tempo estimado de cada palavra (ms) para a boca acompanhar a voz
function timings(text){
  const words = text.trim().split(/\s+/).filter(Boolean);
  const wtimes = [], wdurations = []; let t = 120;
  for (const w of words){
    const letters = w.replace(/[^\p{L}\p{N}]/gu,'').length || 1;
    const d = Math.max(170, letters * 72);
    wtimes.push(t); wdurations.push(d);
    t += d + (/[.,!?;:]$/.test(w) ? 260 : 50);
  }
  return { words, wtimes, wdurations, total: t + 200 };
}

// Voz da nuvem (Oracle): áudio de verdade, igual em qualquer celular, com a boca sincronizada.
function decodificar(ctx, dados){
  return new Promise((ok, erro) => { try { const p = ctx.decodeAudioData(dados, ok, erro); if (p && p.then) p.then(ok, erro); } catch (e) { erro(e); } });
}
async function sayNuvem(text){
  const r = await fetch(API + '/api/voz', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto: text, assistente: assistente() }) });
  if (!r.ok) throw new Error('voz HTTP ' + r.status);
  const buf = await decodificar(head.audioCtx, await r.arrayBuffer());
  const tm = timings(text);
  const k = (buf.duration * 1000) / tm.total;   // ajusta o tempo das palavras ao áudio real
  head.speakAudio({ audio: buf, words: tm.words, wtimes: tm.wtimes.map(t => t * k), wdurations: tm.wdurations.map(t => t * k) }, { lipsyncLang: 'pt_br' });
  setTimeout(() => { $('sub').textContent = ''; }, buf.duration * 1000 + 600);
}
let nuvemFalhou = false;
// iPhone/iPad: o Safari só libera vozes robóticas para sites, então usa a voz da nuvem.
// Android e computador: usam a voz do aparelho quando ela é boa (economiza a cota da nuvem).
const ehIOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
function precisaNuvem(){
  if (ehIOS) return true;
  if (!('speechSynthesis' in window)) return true;
  const vs = (speechSynthesis.getVoices() || []).filter(v => /^pt/i.test(v.lang));
  const melhor = vs.reduce((m, v) => Math.max(m, vozNota(v)), -999);
  return melhor < 100;
}
async function say(text){
  text = (text || '').trim();
  if (!text || !head || loading) return;
  try { head.audioCtx.resume(); } catch {}
  if (API && !nuvemFalhou && precisaNuvem()){
    try { head.stopSpeaking(); } catch {}
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    $('sub').textContent = text;
    try { await sayNuvem(text); return; }
    catch (e) { console.warn('Voz da nuvem indisponível, usando a voz do aparelho', e); nuvemFalhou = true; setTimeout(() => { nuvemFalhou = false; }, 60000); }
  }
  sayAparelho(text);
}
function sayAparelho(text){
  try { head.audioCtx.resume(); } catch {}
  try { head.stopSpeaking(); } catch {}
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  $('sub').textContent = text;

  const tm = timings(text);
  const ctx = head.audioCtx;
  const silent = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * tm.total / 1000), ctx.sampleRate);
  const startLips = () => head.speakAudio({ audio: silent, words: tm.words, wtimes: tm.wtimes, wdurations: tm.wdurations }, { lipsyncLang: 'pt_br' });

  if ('speechSynthesis' in window){
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'pt-BR'; u.rate = 0.92; u.volume = 1; u.pitch = 1;
    const v = speechSynthesis.getVoices().find(x => x.name === $('voice').value);
    if (v) u.voice = v;
    let started = false;
    u.onstart = () => { if (!started){ started = true; startLips(); } };
    setTimeout(() => { if (!started){ started = true; startLips(); } }, 700);
    u.onend = () => setTimeout(() => { $('sub').textContent = ''; }, 600);
    speechSynthesis.speak(u);
  } else {
    startLips();
    setTimeout(() => { $('sub').textContent = ''; }, tm.total + 600);
  }
}

// ---------- Conversa ----------
function addMsg(who, text){
  const d = document.createElement('div');
  d.className = 'msg ' + who; d.textContent = text;
  $('log').appendChild(d); $('log').scrollTop = $('log').scrollHeight;
}
function falaEla(text){ addMsg('ela', text); say(text); }

// Respostas simples (modo demonstração). No próximo passo: IA da nuvem.
const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
function responder(fala){
  const t = norm(fala);
  if (/(sozinh|solidao|ninguem|saudade|abandon)/.test(t)) return 'Sinto muito que a senhora esteja se sentindo assim. Quer que eu mande uma mensagem para a sua família pedindo uma ligação hoje?';
  if (/(\bdor\b|\bdores\b|doendo|tontura|tonta|passando mal|\bcai\b|\bcaiu\b|queda)/.test(t)) return 'Isso é importante. Vou avisar a sua família agora. Se a dor for forte, ligue para o 192. A senhora está sozinha em casa?';
  if (/(remedio|tomei|comprimido)/.test(t)) return /(nao|esqueci)/.test(t) ? 'Tudo bem. Vamos tomar agora? Pegue o comprimido das oito com um copo de água, eu espero.' : 'Muito bem! Anotei que a senhora tomou o remédio. Sua família vai ficar tranquila.';
  if (/(exercicio|braco|cansad)/.test(t)) return 'Vamos devagar, no seu ritmo. Levante os dois braços bem alto e conte comigo: um, dois, três.';
  if (/(dormi|dormiu|sono|noite)/.test(t)) return /(mal|pouco|nao)/.test(t) ? 'Que pena. Quer me contar o que atrapalhou o sono? Hoje à tarde podemos descansar um pouco.' : 'Que bom! Dormir bem faz toda a diferença. E o café da manhã, já tomou?';
  if (/(sim|quero|pode|claro|isso)/.test(t)) return 'Combinado! Já estou avisando. Enquanto isso, me conta: o que a senhora gostaria de fazer hoje?';
  if (/(nao|agora nao)/.test(t)) return 'Tudo bem, a senhora que manda. Estou aqui se precisar.';
  if (/(bem|otimo|feliz|alegre|bom)/.test(t)) return 'Que alegria ouvir isso! O que deixou o seu dia bom?';
  if (/(triste|chorei|chorando|desanim)/.test(t)) return 'Obrigada por me contar. Quer conversar um pouco sobre isso, ou prefere que eu chame alguém da família?';
  if (/(comi|almoco|almocei|jantar|cafe)/.test(t)) return 'Hum, que delícia! Comer bem dá energia. Já bebeu água hoje?';
  return 'Entendi. Me conta um pouco mais sobre isso?';
}
// IA da Oracle pelo back-end do VinaCare (se configurado). Sem back-end: respostas de demonstração.
const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
// Cada celular tem a sua pessoa: um código próprio e o nome que ela escolher (guardados só no aparelho)
const guarda = { get(k){ try { return localStorage.getItem(k); } catch { return null; } },
                 set(k, v){ try { localStorage.setItem(k, v); } catch {} } };
let idoso = guarda.get('vina-id');
if (!idoso){ idoso = 'p' + Math.random().toString(36).slice(2, 12); guarda.set('vina-id', idoso); }
$('nome').value = guarda.get('vina-nome') || '';
$('nome').addEventListener('change', () => guarda.set('vina-nome', $('nome').value.trim()));
async function voceDisse(text){
  text = (text || '').trim(); if (!text) return;
  addMsg('voce', text);
  if (!API){ setTimeout(() => falaEla(responder(text)), 400); return; }
  $('micinfo').textContent = 'A Clara está pensando…';
  try {
    const r = await fetch(API + '/api/conversa', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idoso, nome: $('nome').value.trim(), texto: text, assistente: assistente() })
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    falaEla(d.resposta);
    if (d.alerta) addMsg('alerta', 'Aviso para a família: ' + d.alerta);
  } catch (e) {
    console.warn('API indisponível, usando respostas de demonstração', e);
    falaEla(responder(text));
  } finally {
    $('micinfo').textContent = 'Toque, fale e espere ela responder.';
  }
}

// Reconhecimento de voz do navegador (Chrome e Safari)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, ouvindo = false;
if (!SR){
  $('mic').disabled = true;
  $('micinfo').textContent = 'Este navegador não ouve a voz. Use o Chrome ou o Safari, ou responda escrevendo.';
} else {
  rec = new SR(); rec.lang = 'pt-BR'; rec.interimResults = true; rec.continuous = false;
  rec.onresult = (e) => {
    let txt = '', final = false;
    for (const r of e.results){ txt += r[0].transcript; if (r.isFinal) final = true; }
    $('micinfo').textContent = '“' + txt + '”';
    if (final){ pararMic(); voceDisse(txt); $('micinfo').textContent = 'Toque, fale e espere ela responder.'; }
  };
  rec.onerror = (e) => {
    pararMic();
    $('micinfo').textContent = e.error === 'not-allowed' ? 'O microfone foi bloqueado. Libere o microfone no cadeado da barra de endereço.' : 'Não entendi. Toque e fale de novo, mais perto do microfone.';
  };
  rec.onend = () => { if (ouvindo) pararMic(); };
}
function pararMic(){ ouvindo = false; $('mic').setAttribute('aria-pressed','false'); $('mic').textContent = 'Responder falando'; }
$('mic').addEventListener('click', () => {
  if (!rec) return;
  if (ouvindo){ try { rec.stop(); } catch {} pararMic(); return; }
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  try { head && head.stopSpeaking(); } catch {}
  try { rec.start(); ouvindo = true; $('mic').setAttribute('aria-pressed','true'); $('mic').textContent = 'Ouvindo… toque para parar'; $('micinfo').textContent = 'Pode falar.'; }
  catch { $('micinfo').textContent = 'Espere um segundo e toque de novo.'; }
});
$('send').addEventListener('click', () => { voceDisse($('reply').value); $('reply').value = ''; });
$('reply').addEventListener('keydown', e => { if (e.key === 'Enter'){ voceDisse($('reply').value); $('reply').value = ''; } });

['touchend','click'].forEach(ev => document.addEventListener(ev, () => { try { head && head.audioCtx.resume(); } catch {} }, { passive: true }));
document.querySelectorAll('.phr').forEach(b => b.addEventListener('click', () => falaEla(b.textContent)));
$('speak').addEventListener('click', () => falaEla($('txt').value));
document.querySelectorAll('[data-av]').forEach(b => b.addEventListener('click', () => { if (b.dataset.av !== current) load(b.dataset.av); }));

try {
  head = new TalkingHead($('avatar'), {
    lipsyncModules: [], lipsyncLang: 'pt_br',
    cameraView: 'upper', avatarMood: 'happy', modelFPS: 30,
    mixerGainSpeech: 2.5   // volume mais alto da voz (iPhone toca baixo)
  });
  head.lipsync['pt_br'] = new LipsyncPt_br(); // português do Brasil, carregado direto (sem import dinâmico)
  load('avaturn');
} catch (e) {
  console.error(e);
  status('Este navegador não abriu o 3D. Tente no Chrome ou no Safari atualizado.');
}
