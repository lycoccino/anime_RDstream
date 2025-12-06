# 🌸 Futaba Streamer v5.0 ~ Binge Mode 🌸

> *Um streamer de animes minimalista, rápido e direto ao ponto!* ✨

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-pink?style=flat-square)
![Author](https://img.shields.io/badge/Author-Lycoccino-purple?style=flat-square)

## 🎀 O que é?

**Futaba Streamer** é um cliente CLI para buscar e assistir animes diretamente via torrent, usando:
- 🔍 **Nyaa.si** para buscar torrents de anime
- ⚡ **Real-Debrid** para cache instantâneo (sem delay!)
- 🎬 **MPV** como player
- 🔄 **Binge Mode** para assistir sequências completas

Sem ads, sem bloat, puro anime! 💕

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.8+
- MPV instalado no sistema
- Conta no [Real-Debrid](https://real-debrid.com) (Premium recomendado)

### Setup

```bash
# Clone o projeto
git clone https://github.com/Lycoccino/futaba_stream.git
cd futaba_stream

# Instale as dependências
pip install -r requirements.txt

# Execute e configure (automático!)
python main.py
```

### 🎯 Configuração Automática do Token

Na primeira execução, o app vai:
1. Detectar que você é novo
2. Mostrar um painel bonito com instruções
3. Pedir seu token do Real-Debrid
4. Validar automaticamente
5. Salvar em `.env` (seguro!)

**Onde pegar o token?**
- Acesse: https://real-debrid.com/apitoken
- Copie o "Token Private" (aquele código gigante)
- Cole no prompt - pronto! ✅

## 📖 Como Usar

```bash
python main.py
```

Fluxo de uso:

```
1️⃣  Digite o nome do anime (ex: "Jujutsu Kaisen")
2️⃣  Veja os resultados com grupo, tamanho e qualidade
3️⃣  Selecione o resultado que quer
4️⃣  Se for batch (temporada completa):
    - Escolha por qual episódio começar
    - Assistir todos em sequência
    - Menu pós-ep: [N]ext | [S]elecionar | [M]enu Principal
5️⃣  Se for single: Toca e volta pro menu
```

## 🎯 Features Novas (v5.0)

✨ **Binge Mode Pro** - Assista temporadas inteiras sem parar  
✨ **Menu Pós-Episódio** - Escolha: próximo | pular | voltar  
✨ **Setup Automático** - Token extraído e validado na primeira vez  
✨ **Batch Detection** - Detecta automaticamente temporadas  
✨ **Cache Hunter** - Verifica se está cacheado antes de tocar  
✨ **Mapeamento Inteligente** - Links corretos pro episódio certo  
✨ **Rich UI** - Interface colorida e kawaii  
✨ **DDoS-Guard Bypass** - Usa cloudscraper pra evitar blockers  

## 📦 Dependências

| Pacote | Versão | Propósito |
|--------|--------|----------|
| `requests` | ≥2.31.0 | HTTP requests |
| `python-dotenv` | ≥1.0.0 | Gerencia .env |
| `rich` | ≥13.0.0 | UI no terminal |
| `cloudscraper` | ≥1.2.60 | Bypass anti-bot |
| `beautifulsoup4` | ≥4.12.2 | Parse HTML |
| `urllib3` | ≥1.26.0 | HTTP utilities |

## ⚙️ Configuração Avançada

### Mudar player padrão

No método `play_mpv()`:
```python
# Troque "mpv" por qualquer player que suporte URL
subprocess.run(["vlc", url])  # VLC
subprocess.run(["ffplay", url])  # FFplay
```

### Customizar domínios Nyaa

Em `search_nyaa()`:
```python
domains = ["https://nyaa.iss.one", "https://nyaa.si"]
# Adicione mais mirrors conforme necessário
```

### Aumentar limit de episódios exibidos

Em `prompt_episode_selection()`:
```python
limit = 30  # Mude pra 50, 100, etc
```

## 🎬 Exemplos de Uso

### Buscar single episode
```
O que vamos assistir hoje? Hunter x Hunter Episode 50
→ Resultado único
→ Toca direto
```

### Binge uma temporada
```
O que vamos assistir hoje? Demon Slayer Season 2
→ Detecta 12 episódios
→ Pergunta por qual começar
→ Toca sequencialmente com menu entre eps
```

### Pular episódios
```
Episódio 5 encerrado!
Opções: [N] Próximo | [S] Selecionar | [M] Menu Principal
→ Digita "s"
→ Escolhe episódio 8
→ Toca direto
```

## 🔒 Segurança

⚠️ **NUNCA commite seu `.env`** com o token!

O arquivo `.gitignore` já o ignora.

Se acidentalmente expuser o token:
1. Acesse https://real-debrid.com/apitoken
2. Gere um novo token
3. Atualize no `.env`
4. O antigo morre automaticamente

## 🐛 Troubleshooting

| Erro | Solução |
|------|---------|
| `Token inválido` | Delete `.env` e rode de novo pra configurar |
| `Acesso Negado (401)` | Seu token expirou. Gere um novo em real-debrid.com |
| `Nenhum vídeo encontrado` | Tente um nome mais específico ou diferente grupo |
| `DDoS-Guard detectado` | Tenta automaticamente o próximo domínio |
| `Cache miss` | RD está baixando. Tente em alguns minutos |
| `MPV não encontrado` | Instale: `sudo apt install mpv` (Linux) |

## 📊 Estrutura do Projeto

```
futaba_stream/
├── main.py              # Aplicação principal (v5.0)
├── requirements.txt     # Dependências
├── .env                 # Token RD (gerado automaticamente)
├── .gitignore          # Git ignore
├── README.md           # Este arquivo
└── LICENSE             # MIT
```

## 🌟 Como Funciona (Por Trás das Cortinas)

```
USER INPUT
    ↓
search_nyaa()          🔍 Busca e scrapa Nyaa
    ↓
display_results()      📋 Mostra tabela de resultados
    ↓
process_magnet()       🧲 Processa torrent no RD
    ↓
extract_videos()       🎬 Extrai vídeos em ordem
    ↓
prompt_episode()       🎯 Menu de seleção
    ↓
get_stream_link()      🔗 Mapeia e unrestrict link
    ↓
play_mpv()             ▶️  Toca no player
    ↓
Menu Pós-Ep            🔄 Próx/Pular/Menu
```

## 💡 Tips & Tricks

🎯 **Batch == Cache**: Se buscar uma temporada completa, TODOS os eps são cacheados  
🎯 **Grupos famosos**: HorribleSubs, SubsPlease, Erai-raws geralmente têm cache rápido  
🎯 **Hora do pico**: Madrugada = cache mais rápido (menos concorrência)  
🎯 **Qualidade**: Use flags do MPV (`--profile=high-quality`)  
🎯 **Legenda**: MPV auto-detecta `.srt` se estiverem juntos  

## 🔗 Links Úteis

- [Real-Debrid API Token](https://real-debrid.com/apitoken)
- [Documentação Real-Debrid](https://api.real-debrid.com)
- [Nyaa.si](https://nyaa.si)
- [MPV Player](https://mpv.io)

## 📝 Changelog

### v5.0 - Binge Mode
- ✨ Loop contínuo de episódios
- ✨ Menu pós-episódio interativo
- ✨ Mapeamento inteligente de links
- ✨ Setup automático do token
- ✨ Melhorias na UI

### v4.0
- Initial stable release

## 🙏 Créditos

- **Autor**: [Lycoccino](https://github.com/Lycoccino)
- Nyaa por existir ❤️
- Real-Debrid por ser OP ⚡
- MPV pelo melhor player 🎬
- Comunidade anime 💕

## 📜 Licença

MIT License - Faça o que quiser com isso!

```
Copyright (c) 2025 Lycoccino

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

## 🤝 Contribuições

Encontrou um bug? Tem sugestão? Abra uma issue! PR's são bem-vindas! 🎉

---

**Made with ❤️ and anime by Lycoccino** ✨