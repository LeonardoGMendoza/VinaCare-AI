# VinaCare API (back-end)

A Clara conversa com o idoso usando a IA da Oracle Cloud (OCI Generative AI, Cohere Command A), com memória do que a pessoa contou e alerta para a família.

## Rodar no computador (Git Bash)

```bash
cd ~/Documents/Automacao/VinaCare-AI/backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env      # preencha com os mesmos valores OCI_* do Omni
uvicorn app.main:app --reload --port 8001
```

Teste: abra http://localhost:8001/api/saude → deve mostrar `"ia": true`.

## Rotas

| Rota | O que faz |
|---|---|
| `GET /api/saude` | Mostra se a IA da Oracle está configurada |
| `POST /api/conversa` | `{ "idoso": "demo", "nome": "Etelvina", "texto": "dormi mal" }` → resposta da Clara |
| `GET /api/memoria/{idoso}` | Fatos que a Clara lembra da pessoa |
| `DELETE /api/memoria/{idoso}` | Apaga a memória da pessoa (LGPD) |
| `GET /api/alertas/{idoso}` | Alertas gerados para a família |

## Testes

```bash
python -m unittest discover -s tests -t .
```

O arquivo `.env` tem as chaves da Oracle e **nunca** vai para o GitHub (está no `.gitignore`).
