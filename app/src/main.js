import { TalkingHead } from './talkinghead/talkinghead.mjs';
import { LipsyncPt_br } from './talkinghead/lipsync-pt_br.mjs';
window.__vinaStarted = true;

const AVATARS = {
  avaturn: { url: './avatars/avaturn.glb', body: 'F', avatarMood: 'neutral', lipsyncLang: 'pt_br',
    retarget: { Hips:{y:0.03}, Spine:{y:0.02}, Spine1:{y:0.02,z:0.01}, Spine2:{y:0.02,z:0.01}, Neck:{z:0.02,y:0.01}, Head:{z:0.02}, LeftShoulder:{rx:-0.5}, RightShoulder:{rx:-0.5}, scaleToHipsLevel:1.0 },
    baseline: { headRotateX:-0.05, eyeBlinkLeft:0.15, eyeBlinkRight:0.15 } },
  avatarsdk: { url: './avatars/avatarsdk.glb', body: 'M', avatarMood: 'neutral', lipsyncLang: 'pt_br',
    retarget: { Neck:{z:-0.01,rx:-0.15}, Neck1:{z:-0.01,rx:-0.15}, Neck2:{z:-0.01,rx:-0.15}, LeftShoulder:{rz:-0.3}, RightShoulder:{rz:0.3}, scaleToEyesLevel:1.0, origin:{y:-0.1} },
    baseline: { headRotateX:-0.04, eyeBlinkLeft:0.05, eyeBlinkRight:0.05 } }
};
const NOMES = { avaturn: 'Clara', avatarsdk: 'Rafael' };

// Idiomas: reconhecimento de voz, voz do aparelho e frases da tela
const IDIOMAS = {
  pt: { sigla: 'PT', rec: 'pt-BR', voz: /^pt/i, vozPref: /^pt[-_]br/i, html: 'pt-BR', t: {
    tocar: 'Toque e fale', comecar: 'Toque para começar', ola: 'Oi, tudo bem? Como vai?', ouvindo: 'Estou ouvindo…', pensando: 'Pensando…', naoEntendi: 'Não entendi. Toque e fale de novo.',
    micBloqueado: 'Libere o microfone no cadeado da barra de endereço.', semMic: 'Este navegador não ouve a voz. Use o Chrome ou o Safari.',
    carregando: 'Carregando…', erroAvatar: 'Não consegui carregar o avatar. Atualize a página.', erro3d: 'Este navegador não abriu o 3D. Use o Chrome ou o Safari atualizado.',
    semConexao: 'Estou sem conexão agora. Tente de novo daqui a pouco.', exercicios: 'Exercícios', idioma: 'Idioma', avatar: 'Trocar avatar', falar: 'Falar' } },
  es: { sigla: 'ES', rec: 'es-PE', voz: /^es/i, vozPref: /^es[-_](pe|419|us|mx)/i, html: 'es-PE', t: {
    tocar: 'Toque y hable', comecar: 'Toque para empezar', ola: '¡Hola! ¿Cómo estás?', ouvindo: 'Le escucho…', pensando: 'Pensando…', naoEntendi: 'No entendí. Toque y hable otra vez.',
    micBloqueado: 'Permita el micrófono en el candado de la barra de direcciones.', semMic: 'Este navegador no escucha la voz. Use Chrome o Safari.',
    carregando: 'Cargando…', erroAvatar: 'No pude cargar el avatar. Actualice la página.', erro3d: 'Este navegador no abrió el 3D. Use Chrome o Safari actualizado.',
    semConexao: 'Ahora no tengo conexión. Intente de nuevo en un momento.', exercicios: 'Ejercicios', idioma: 'Idioma', avatar: 'Cambiar avatar', falar: 'Hablar' } },
  en: { sigla: 'EN', rec: 'en-US', voz: /^en/i, vozPref: /^en[-_]us/i, html: 'en', t: {
    tocar: 'Tap and speak', comecar: 'Tap to start', ola: 'Hi! How are you?', ouvindo: "I'm listening…", pensando: 'Thinking…', naoEntendi: "I didn't catch that. Tap and speak again.",
    micBloqueado: 'Allow the microphone in the lock icon of the address bar.', semMic: "This browser can't hear voice. Use Chrome or Safari.",
    carregando: 'Loading…', erroAvatar: "I couldn't load the avatar. Refresh the page.", erro3d: "This browser couldn't open 3D. Use an updated Chrome or Safari.",
    semConexao: "I'm offline right now. Please try again in a moment.", exercicios: 'Exercises', idioma: 'Language', avatar: 'Change avatar', falar: 'Speak' } },
};
const ORDEM = ['pt', 'es', 'en'];

const $ = id => document.getElementById(id);
const guarda = { get(k){ try { return localStorage.getItem(k); } catch { return null; } },
                 set(k, v){ try { localStorage.setItem(k, v); } catch {} } };
const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

let head = null, current = guarda.get('vina-avatar') === 'avatarsdk' ? 'avatarsdk' : 'avaturn', loading = false;
let idioma = IDIOMAS[guarda.get('vina-idioma')] ? guarda.get('vina-idioma') : 'pt';
let rec = null, ouvindo = false, ouvido = '', cumprimentou = false;
const T = () => IDIOMAS[idioma].t;
const assistente = () => NOMES[current] || 'Clara';
let idoso = guarda.get('vina-id');
if (!idoso){ idoso = 'p' + Math.random().toString(36).slice(2, 12); guarda.set('vina-id', idoso); }

const status = (t) => { $('status').hidden = !t; if (t) $('status').textContent = t; };
function estado(e){                       // pronto | ouvindo | pensando | falando
  $('mic').dataset.estado = e;
  $('dica').textContent = e === 'ouvindo' ? T().ouvindo : e === 'pensando' ? T().pensando : e === 'pronto' ? (cumprimentou ? T().tocar : T().comecar) : '';
}
function aplicarIdioma(){
  document.documentElement.lang = IDIOMAS[idioma].html;
  $('trocaIdioma').textContent = IDIOMAS[idioma].sigla;
  $('trocaIdioma').setAttribute('aria-label', T().idioma + ': ' + IDIOMAS[idioma].sigla);
  $('trocaAvatar').setAttribute('aria-label', T().avatar);
  $('linkExercicio').setAttribute('aria-label', T().exercicios);
  $('mic').setAttribute('aria-label', T().falar);
  $('palco').setAttribute('aria-label', T().tocar);
  if (rec) rec.lang = IDIOMAS[idioma].rec;
  if ($('mic').dataset.estado === 'pronto') estado('pronto');
}

// ---------- Avatar ----------
async function load(key){
  if (loading) return;
  loading = true; current = key; guarda.set('vina-avatar', key);
  $('trocaAvatar').textContent = NOMES[key];
  status(T().carregando + ' 0%');
  try {
    await head.showAvatar(AVATARS[key], ev => {
      if (ev.lengthComputable) status(T().carregando + ' ' + Math.round(ev.loaded / ev.total * 100) + '%');
    });
    head.setView('upper');
    status('');
    estado('pronto');
    if (cumprimentou) cumprimentar();   // trocou de avatar: o novo também diz oi
  } catch (e) {
    console.error(e);
    status(T().erroAvatar);
  }
  loading = false;
}
// Expressão do rosto conforme o tom da resposta (a IA demonstra empatia; ela não sente)
const HUMOR = { feliz: 'happy', carinho: 'love', triste: 'sad', neutro: 'neutral' };
function humor(h){ try { head && head.setMood(HUMOR[h] || 'neutral'); } catch {} }

// ---------- Voz ----------
function vozNota(v){
  const n = (v.name + ' ' + (v.voiceURI || '')).toLowerCase(), I = IDIOMAS[idioma];
  let p = 0;
  if (I.vozPref.test(v.lang)) p += 100; else if (I.voz.test(v.lang)) p += 10;
  if (/premium/.test(n)) p += 50;
  if (/enhanced|aprimorad|natural|neural|online/.test(n)) p += 40;
  if (/compact|eloquence|novelty/.test(n)) p -= 30;
  return p;
}
function melhorVoz(){
  const vs = ('speechSynthesis' in window ? speechSynthesis.getVoices() : []).filter(v => IDIOMAS[idioma].voz.test(v.lang));
  return vs.sort((a, b) => vozNota(b) - vozNota(a))[0] || null;
}
if ('speechSynthesis' in window) speechSynthesis.getVoices();

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
function decodificar(ctx, dados){
  return new Promise((ok, erro) => { try { const p = ctx.decodeAudioData(dados, ok, erro); if (p && p.then) p.then(ok, erro); } catch (e) { erro(e); } });
}
const espera = (ms) => new Promise(r => setTimeout(r, ms));

// Voz neural da nuvem (Azure pelo back-end): igual em qualquer celular, com a boca sincronizada.
async function sayNuvem(text){
  const r = await fetch(API + '/api/voz', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto: text, assistente: assistente(), idioma }) });
  if (!r.ok) throw new Error('voz HTTP ' + r.status);
  const buf = await decodificar(head.audioCtx, await r.arrayBuffer());
  const tm = timings(text);
  const k = (buf.duration * 1000) / tm.total;
  head.speakAudio({ audio: buf, words: tm.words, wtimes: tm.wtimes.map(t => t * k), wdurations: tm.wdurations.map(t => t * k) }, { lipsyncLang: 'pt_br' });
  return buf.duration * 1000;
}
let nuvemFalhou = false;
const ehIOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
function precisaNuvem(){
  if (ehIOS || !('speechSynthesis' in window)) return true;
  const v = melhorVoz();
  return !v || vozNota(v) < 100;
}
function sayAparelho(text){
  const tm = timings(text);
  const ctx = head.audioCtx;
  const silent = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * tm.total / 1000), ctx.sampleRate);
  const startLips = () => head.speakAudio({ audio: silent, words: tm.words, wtimes: tm.wtimes, wdurations: tm.wdurations }, { lipsyncLang: 'pt_br' });
  if ('speechSynthesis' in window){
    const u = new SpeechSynthesisUtterance(text);
    u.lang = IDIOMAS[idioma].rec; u.rate = 0.92;
    const v = melhorVoz(); if (v) u.voice = v;
    let started = false;
    u.onstart = () => { if (!started){ started = true; startLips(); } };
    setTimeout(() => { if (!started){ started = true; startLips(); } }, 700);
    speechSynthesis.speak(u);
  } else startLips();
  return tm.total;
}
async function say(text){
  text = (text || '').trim();
  if (!text || !head || loading) return;
  try { head.audioCtx.resume(); } catch {}
  try { head.stopSpeaking(); } catch {}
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  estado('falando');
  let duracao;
  if (API && !nuvemFalhou && precisaNuvem()){
    try { duracao = await sayNuvem(text); }
    catch (e) { console.warn('Voz da nuvem indisponível', e); nuvemFalhou = true; setTimeout(() => { nuvemFalhou = false; }, 60000); }
  }
  if (duracao === undefined) duracao = sayAparelho(text);
  await espera(duracao + 300);
  if ($('mic').dataset.estado === 'falando') estado('pronto');
}

// ---------- Conversa: a pessoa sempre fala primeiro ----------
async function voceDisse(text){
  text = (text || '').trim(); if (!text) { estado('pronto'); return; }
  estado('pensando');
  try {
    if (!API) throw new Error('sem API');
    const r = await fetch(API + '/api/conversa', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idoso, nome: '', texto: text, assistente: assistente(), idioma }) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    humor(d.humor);
    await say(d.resposta);
  } catch (e) {
    console.warn('Conversa indisponível', e);
    humor('neutro');
    await say(T().semConexao);
  }
}

// Reconhecimento de voz do navegador (Chrome e Safari)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR){
  rec = new SR(); rec.lang = IDIOMAS[idioma].rec; rec.interimResults = true; rec.continuous = false;
  rec.onresult = (e) => {
    let txt = '', final = false;
    for (const r of e.results){ txt += r[0].transcript; if (r.isFinal) final = true; }
    ouvido = txt;
    if (final){ ouvindo = false; const t = ouvido; ouvido = ''; voceDisse(t); }
  };
  rec.onerror = (e) => {
    ouvindo = false; ouvido = ''; estado('pronto');
    $('dica').textContent = e.error === 'not-allowed' ? T().micBloqueado : e.error === 'no-speech' ? T().tocar : T().naoEntendi;
  };
  rec.onend = () => {
    if (!ouvindo) return;
    ouvindo = false;
    if (ouvido){ const t = ouvido; ouvido = ''; voceDisse(t); } else estado('pronto');
  };
}
// A Clara abre a conversa com um "oi" neutro (o navegador só libera o som depois do primeiro toque)
async function cumprimentar(){
  cumprimentou = true;
  humor('feliz');
  await say(T().ola);
}
function tocarParaFalar(){
  try { head && head.audioCtx.resume(); } catch {}
  if (!cumprimentou){ if (!loading && head) cumprimentar(); return; }
  if (!rec){ $('dica').textContent = T().semMic; return; }
  if ($('mic').dataset.estado === 'pensando' || loading) return;
  if (ouvindo){ try { rec.stop(); } catch {} return; }
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  try { head && head.stopSpeaking(); } catch {}
  try { ouvido = ''; rec.lang = IDIOMAS[idioma].rec; rec.start(); ouvindo = true; estado('ouvindo'); }
  catch { $('dica').textContent = T().naoEntendi; }
}

// Toque em qualquer lugar da tela (menos nos botões do topo) para falar
$('palco').addEventListener('click', (ev) => { if (!ev.target.closest('.topo')) tocarParaFalar(); });
$('trocaIdioma').addEventListener('click', () => {
  idioma = ORDEM[(ORDEM.indexOf(idioma) + 1) % ORDEM.length];
  guarda.set('vina-idioma', idioma); aplicarIdioma();
  if (cumprimentou && !ouvindo) cumprimentar();   // cumprimenta de novo no idioma novo
});
$('trocaAvatar').addEventListener('click', () => { if (!loading) load(current === 'avaturn' ? 'avatarsdk' : 'avaturn'); });

aplicarIdioma();
try {
  head = new TalkingHead($('avatar'), {
    lipsyncModules: [], lipsyncLang: 'pt_br',
    cameraView: 'upper', avatarMood: 'neutral', modelFPS: 30,
    mixerGainSpeech: 2.5   // volume mais alto da voz (iPhone toca baixo)
  });
  head.lipsync['pt_br'] = new LipsyncPt_br();
  load(current);
} catch (e) {
  console.error(e);
  status(T().erro3d);
}
