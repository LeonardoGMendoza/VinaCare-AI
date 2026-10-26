// VinaCare · exercícios: conta repetições ao vivo (ângulos do MediaPipe Pose) e pede a avaliação
// ao modelo treinado no OCI Data Science, publicado no Model Deployment, através do back-end.
import { FilesetResolver, PoseLandmarker, DrawingUtils } from '@mediapipe/tasks-vision';

const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm';
const MODELO = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task';
const SEGUNDOS = 5;            // mesmo tamanho das gravações usadas no treino

// Cada exercício: qual medida acompanhar e os limites para contar uma repetição (vai até "cima" e volta a "baixo").
const EXERCICIOS = {
  levantar_bracos: { nome: 'Levantar os braços', instr: 'Levante os dois braços pela frente até o alto e desça devagar.',
    medida: (p) => (ang(p[23], p[11], p[13]) + ang(p[24], p[12], p[14])) / 2, cima: 140, baixo: 60, maior: true },
  abrir_bracos: { nome: 'Abrir os braços', instr: 'Abra os braços para os lados até a altura dos ombros e volte.',
    medida: (p) => (ang(p[23], p[11], p[13]) + ang(p[24], p[12], p[14])) / 2, cima: 75, baixo: 35, maior: true },
  sentar_levantar: { nome: 'Sentar e levantar', instr: 'Com uma cadeira atrás, sente e levante devagar.',
    medida: (p) => (ang(p[11], p[23], p[25]) + ang(p[12], p[24], p[26])) / 2, cima: 160, baixo: 120, maior: true },
  marcha_parado: { nome: 'Marchar parado', instr: 'Marche no lugar, levantando os joelhos alternadamente.',
    medida: (p) => Math.min(ang(p[11], p[23], p[25]), ang(p[12], p[24], p[26])), cima: 140, baixo: 160, maior: false },
};

const $ = (id) => document.getElementById(id);
const status = (t) => { $('status').textContent = t; };
let landmarker = null, desenho = null, ultimoTempo = -1, gravando = false, quadros = [];
let reps = 0, emCima = false, audioCtx = null, ocupado = false;

function ang(a, b, c){
  const ab = [a.x - b.x, a.y - b.y], cb = [c.x - b.x, c.y - b.y];
  const cos = (ab[0] * cb[0] + ab[1] * cb[1]) / (Math.hypot(...ab) * Math.hypot(...cb) || 1);
  return Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
}

for (const [id, e] of Object.entries(EXERCICIOS)){
  const o = document.createElement('option'); o.value = id; o.textContent = e.nome; $('exercicio').appendChild(o);
}
const atual = () => EXERCICIOS[$('exercicio').value];
const mostrarInstr = () => { $('instr').textContent = atual().instr; };
$('exercicio').addEventListener('change', mostrarInstr); mostrarInstr();

// Voz: a mesma voz neural da Clara (Azure) pelo back-end; se falhar, a voz do aparelho.
function decodificar(ctx, dados){ return new Promise((ok, erro) => ctx.decodeAudioData(dados, ok, erro)); }
async function falar(texto){
  try {
    if (!API || !audioCtx) throw new Error('sem nuvem');
    const r = await fetch(API + '/api/voz', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto, assistente: 'Clara' }) });
    if (!r.ok) throw new Error('voz ' + r.status);
    const fonte = audioCtx.createBufferSource();
    fonte.buffer = await decodificar(audioCtx, await r.arrayBuffer());
    fonte.connect(audioCtx.destination); fonte.start();
  } catch {
    if ('speechSynthesis' in window){ const u = new SpeechSynthesisUtterance(texto); u.lang = 'pt-BR'; u.rate = 0.92; speechSynthesis.speak(u); }
  }
}

async function ligarCamera(){
  status('Carregando o detector de corpo…');
  const vision = await FilesetResolver.forVisionTasks(WASM);
  const opcoes = (delegate) => ({ baseOptions: { modelAssetPath: MODELO, delegate }, runningMode: 'VIDEO', numPoses: 1 });
  try { landmarker = await PoseLandmarker.createFromOptions(vision, opcoes('GPU')); }
  catch { landmarker = await PoseLandmarker.createFromOptions(vision, opcoes('CPU')); }
  status('Abrindo a câmera…');
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 }, audio: false });
  const v = $('video'); v.srcObject = stream; await v.play();
  const c = $('tela'); c.width = v.videoWidth; c.height = v.videoHeight;
  desenho = new DrawingUtils(c.getContext('2d'));
  requestAnimationFrame(loop);
}

function contar(p){
  const e = atual(), m = e.medida(p);
  const passouCima = e.maior ? m >= e.cima : m <= e.cima;
  const voltouBaixo = e.maior ? m <= e.baixo : m >= e.baixo;
  if (!emCima && passouCima){ emCima = true; $('fase').textContent = 'subiu…'; }
  else if (emCima && voltouBaixo){ emCima = false; reps += 1; $('reps').textContent = reps; $('fase').textContent = 'boa!'; }
}

function loop(){
  const v = $('video'), c = $('tela'), ctx = c.getContext('2d');
  if (v.currentTime !== ultimoTempo){
    ultimoTempo = v.currentTime;
    const r = landmarker.detectForVideo(v, performance.now());
    ctx.clearRect(0, 0, c.width, c.height);
    const p = r.landmarks && r.landmarks[0];
    if (p){
      desenho.drawConnectors(p, PoseLandmarker.POSE_CONNECTIONS, { color: '#5cbfa8', lineWidth: 3 });
      desenho.drawLandmarks(p, { color: '#e39a72', radius: 3 });
      if (gravando){ contar(p); quadros.push(p.flatMap(k => [k.x, k.y, k.z, k.visibility ?? 0])); }
    }
  }
  requestAnimationFrame(loop);
}

const espera = (ms) => new Promise(r => setTimeout(r, ms));
async function comecar(){
  if (ocupado) return;
  ocupado = true; $('comecar').disabled = true; $('resultado').textContent = ''; $('resultado').className = 'resultado';
  try {
    if (!audioCtx){ const AC = window.AudioContext || window.webkitAudioContext; if (AC) audioCtx = new AC(); }
    if (audioCtx) audioCtx.resume();
    if (!landmarker) await ligarCamera();
    $('video').closest('.cam').scrollIntoView({ behavior: 'smooth', block: 'start' });
    reps = 0; emCima = false; $('reps').textContent = '0'; $('fase').textContent = 'prepare-se';
    for (const n of [3, 2, 1]){ $('contagem').textContent = n; await espera(1000); }
    $('contagem').textContent = '';
    quadros = []; gravando = true; const inicio = performance.now();
    status('Agora! ' + atual().instr);
    await espera(SEGUNDOS * 1000);
    gravando = false;
    $('fase').textContent = reps === 1 ? 'repetição' : 'repetições';
    const fps = Math.round(quadros.length / ((performance.now() - inicio) / 1000));
    if (quadros.length < 10){ status('Não consegui ver seu corpo. Afaste-se um pouco e tente de novo.'); return; }
    status('Avaliando com o modelo da Oracle…');
    const r = await fetch(API + '/api/exercicio/avaliar', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exercicio: $('exercicio').value, fps, quadros: quadros.slice(0, 180) }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
    const frase = (reps ? `Você fez ${reps} ${reps === 1 ? 'repetição' : 'repetições'}. ` : '') + d.mensagem;
    $('resultado').textContent = frase; $('resultado').classList.add(d.qualidade === 'certo' ? 'certo' : 'errado');
    status('Pronto! Toque em "Começar" para fazer de novo.');
    falar(frase);
  } catch (e) {
    console.error(e);
    const msg = 'Contei ' + reps + ' ' + (reps === 1 ? 'repetição' : 'repetições') + '. A avaliação não respondeu agora: ' + (e && e.message ? e.message : e);
    $('resultado').textContent = msg;
    status('Toque em "Começar" para tentar de novo.');
  } finally {
    ocupado = false; $('comecar').disabled = false; $('comecar').textContent = 'Fazer de novo';
  }
}
$('comecar').addEventListener('click', comecar);
