// VinaCare · coleta do dataset de exercícios (MediaPipe Pose no navegador -> back-end -> OCI Data Science)
import { FilesetResolver, PoseLandmarker, DrawingUtils } from '@mediapipe/tasks-vision';

const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm';
const MODELO = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task';
const INSTRUCOES = {
  levantar_bracos: 'De pé ou sentado, levante os dois braços pela frente até o alto e desça devagar. Faça 2 ou 3 vezes durante a gravação.',
  abrir_bracos: 'Abra os dois braços para os lados até a altura dos ombros e volte. 2 ou 3 vezes.',
  sentar_levantar: 'Com uma cadeira atrás, sente e levante devagar. 1 ou 2 vezes.',
  marcha_parado: 'Marche no lugar, levantando os joelhos alternadamente.'
};
const SEGUNDOS = 5;

const $ = (id) => document.getElementById(id);
const guarda = { get(k){ try { return localStorage.getItem(k); } catch { return null; } }, set(k, v){ try { localStorage.setItem(k, v); } catch {} } };
const status = (t) => { $('status').textContent = t; };

let landmarker = null, desenho = null, ultimoTempo = -1, gravando = false, quadros = [], qualidade = 'certo';

$('codigo').value = guarda.get('vina-coleta-codigo') || '';
$('pessoa').value = guarda.get('vina-coleta-pessoa') || '';
$('codigo').addEventListener('change', () => guarda.set('vina-coleta-codigo', $('codigo').value.trim()));
$('pessoa').addEventListener('change', () => guarda.set('vina-coleta-pessoa', $('pessoa').value.trim()));

for (const [id, nome] of Object.entries({ levantar_bracos: 'Levantar os braços', abrir_bracos: 'Abrir os braços', sentar_levantar: 'Sentar e levantar da cadeira', marcha_parado: 'Marchar parado' })){
  const o = document.createElement('option'); o.value = id; o.textContent = nome; $('exercicio').appendChild(o);
}
const mostrarInstr = () => { $('instr').textContent = INSTRUCOES[$('exercicio').value]; };
$('exercicio').addEventListener('change', mostrarInstr); mostrarInstr();

function escolherQualidade(q){
  qualidade = q;
  $('q-certo').setAttribute('aria-pressed', String(q === 'certo'));
  $('q-errado').setAttribute('aria-pressed', String(q === 'errado'));
}
$('q-certo').addEventListener('click', () => escolherQualidade('certo'));
$('q-errado').addEventListener('click', () => escolherQualidade('errado'));

// Ângulo no ombro (quadril - ombro - cotovelo), em graus: ~20° braço abaixado, ~170° braço no alto
function angulo(a, b, c){
  const ab = [a.x - b.x, a.y - b.y], cb = [c.x - b.x, c.y - b.y];
  const cos = (ab[0] * cb[0] + ab[1] * cb[1]) / (Math.hypot(...ab) * Math.hypot(...cb) || 1);
  return Math.round(Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI);
}

async function ligar(){
  $('ligar').disabled = true;
  try {
    status('Carregando o modelo de pose…');
    const vision = await FilesetResolver.forVisionTasks(WASM);
    const opcoes = (delegate) => ({ baseOptions: { modelAssetPath: MODELO, delegate }, runningMode: 'VIDEO', numPoses: 1 });
    try { landmarker = await PoseLandmarker.createFromOptions(vision, opcoes('GPU')); }
    catch { landmarker = await PoseLandmarker.createFromOptions(vision, opcoes('CPU')); }
    status('Abrindo a câmera…');
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 }, audio: false });
    const v = $('video'); v.srcObject = stream; await v.play();
    const c = $('tela'); c.width = v.videoWidth; c.height = v.videoHeight;
    desenho = new DrawingUtils(c.getContext('2d'));
    $('gravar').disabled = false;
    status('Câmera ligada. Fique de corpo inteiro na imagem.');
    requestAnimationFrame(loop);
  } catch (e) {
    console.error(e);
    $('ligar').disabled = false;
    status('Não consegui ligar a câmera: ' + (e && e.message ? e.message : e) + '. Permita a câmera e tente de novo.');
  }
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
      $('medidor').textContent = 'Ângulo do braço esquerdo: ' + angulo(p[23], p[11], p[13]) + '° · direito: ' + angulo(p[24], p[12], p[14]) + '°';
      if (gravando) quadros.push(p.flatMap(k => [k.x, k.y, k.z, k.visibility ?? 0]));
    } else if (gravando) {
      status('Não estou vendo o corpo inteiro. Afaste-se um pouco.');
    }
  }
  requestAnimationFrame(loop);
}

const espera = (ms) => new Promise(r => setTimeout(r, ms));
async function gravar(){
  const codigo = $('codigo').value.trim();
  if (!codigo){ status('Preencha o código de coleta antes de gravar.'); $('codigo').focus(); return; }
  if (!API){ status('O endereço do servidor não está configurado (VITE_API_URL).'); return; }
  $('gravar').disabled = true;
  for (const n of [3, 2, 1]){ $('contagem').textContent = n; await espera(1000); }
  $('contagem').textContent = '●';
  quadros = []; gravando = true; const inicio = performance.now();
  status('Gravando… faça o exercício.');
  await espera(SEGUNDOS * 1000);
  gravando = false; $('contagem').textContent = '';
  const fps = Math.round(quadros.length / ((performance.now() - inicio) / 1000));
  if (quadros.length < 10){ status('Poucos quadros com o corpo visível. Afaste-se e tente de novo.'); $('gravar').disabled = false; return; }
  status('Enviando ' + quadros.length + ' quadros…');
  try {
    const r = await fetch(API + '/api/dataset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-coleta-codigo': codigo },
      body: JSON.stringify({ exercicio: $('exercicio').value, qualidade, pessoa: $('pessoa').value.trim() || 'anonimo', fps, quadros: quadros.slice(0, 180) })
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
    status('Gravação salva! Pode gravar a próxima.');
    mostrarResumo(d.resumo);
  } catch (e) {
    status('Não consegui salvar: ' + e.message);
  }
  $('gravar').disabled = false;
}

function mostrarResumo(r){
  if (!r) return;
  $('resumo').innerHTML = '';
  for (const v of Object.values(r)){
    const tr = document.createElement('tr');
    tr.innerHTML = '<td></td><td class="n"></td><td class="n"></td>';
    tr.children[0].textContent = v.nome; tr.children[1].textContent = v.certo; tr.children[2].textContent = v.errado;
    $('resumo').appendChild(tr);
  }
}
async function carregarResumo(){
  if (!API){ $('resumo').innerHTML = '<tr><td colspan="3">Servidor não configurado.</td></tr>'; return; }
  try { mostrarResumo(await (await fetch(API + '/api/dataset/resumo')).json()); }
  catch { $('resumo').innerHTML = '<tr><td colspan="3">Servidor indisponível.</td></tr>'; }
}

$('ligar').addEventListener('click', ligar);
$('gravar').addEventListener('click', gravar);
carregarResumo();
