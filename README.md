# VinaCare AI

Aplicativo de cuidado de idosos com inteligência artificial. Um avatar 3D conversa com o idoso, acompanha exercícios pela câmera, lembra dos remédios e avisa a família ou a casa de repouso quando algo muda.

O nome é uma homenagem à minha avó, **Etelvina**.

## Protótipo atual

**Avatar que conversa:** um avatar 3D realista fala português com a boca sincronizada, ouve a resposta do idoso pelo microfone e responde.

▶️ Teste no navegador (Chrome ou Safari): https://leonardogmendoza.github.io/VinaCare-AI/prototipos/avatar/

> As respostas desta versão são de demonstração (palavras-chave). A próxima etapa liga a IA na nuvem.

## Roadmap

- [x] Avatar 3D que fala e ouve em português
- [ ] Conversa com IA generativa e memória do idoso (OCI Generative AI + RAG)
- [ ] Câmera que acompanha e avalia exercícios (MediaPipe + modelo treinado no OCI Data Science)
- [ ] Back-end em Python (FastAPI) na Oracle Cloud
- [ ] Alertas para a família por WhatsApp
- [ ] App para Android e iOS (Capacitor)

## Tecnologias

- Front-end: HTML, JavaScript, three.js
- Avatar e lip-sync: [TalkingHead](https://github.com/met4citizen/TalkingHead) (licença MIT, © Mika Suominen)
- Voz: Web Speech API (reconhecimento e síntese de voz do navegador)
- Planejado: Python FastAPI, Oracle Cloud (Generative AI, Speech, Data Science, Model Deployment), Capacitor

## Créditos e licenças

- **TalkingHead** (`talkinghead.mjs`, `dynamicbones.mjs`, `retargeter.mjs`, `lipsync-pt_br.mjs`, `playback-worklet.js`): MIT License, Copyright (c) 2023-2024 Mika Suominen.
- **Avatares de exemplo** (`avaturn.glb`, criado no [Avaturn](https://avaturn.me); `avatarsdk.glb`, criado no [Avatar SDK / MetaPerson](https://avatarsdk.com)): exemplos do projeto TalkingHead, **somente para uso não comercial**. Serão substituídos por avatares com licença comercial na versão do app.

## Autor

Leonardo Mendoza · Pós-graduação em IA, FIAP
