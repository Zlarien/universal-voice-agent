# Universal Voice Agent v3.0 🤖🎭

> **Agent vocal hybride avec clonage de voix** - Incarne n'importe quel personnage avec une voix réaliste

## 🌟 Features

### Architecture Hybride
- **⚡ Mode Realtime** : OpenAI Realtime natif (ultra rapide, 150ms latence)
- **🔧 Mode Pipeline** : Deepgram STT → GPT-4o-mini → ElevenLabs TTS (clonage de voix)

### Clonage de Voix
- Recherche automatique de samples vocaux
- Clonage avec ElevenLabs Instant Voice Cloning
- Supporte toutes les voix (personnes réelles, fictives)

### Personnages Illimités
- Intégration GPT-4o-mini pour la création de prompts
- Prosodie et marqueurs émotionnels
- 7 ambiances sonores immersives

## 🚀 Quick Start

### 1. Installation

```bash
# Cloner le repo
git clone https://github.com/votre-repo/universal-voice-agent.git
cd universal-voice-agent

# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env avec tes clés API
```

**Fichier .env requis :**
```env
# REQUIRED FOR ALL MODES
OPENAI_API_KEY=sk-xxx
DAILY_ROOM_URL=https://ton-domaine.daily.co/room-name

# REQUIRED FOR PIPELINE MODE ONLY
DEEPGRAM_API_KEY=xxx
ELEVENLABS_API_KEY=xxx
```

### 3. Configuration Daily.co

1. Va sur https://dashboard.daily.co/rooms
2. Crée une room nommée `voice-agent` (ou autre)
3. **IMPORTANT** : Dans les paramètres → Privacy → **Public** ✅
4. Copie l'URL dans `DAILY_ROOM_URL`

### 4. Lancer l'Agent

```bash
python universal_agent_v3.py
```

## 🎮 Modes d'Utilisation

### Mode 1 : ⚡ Realtime (Recommandé pour débuter)

**Avantages :**
- Ultra rapide (150ms de latence)
- Simple à configurer
- Stable et fiable

**Limitations :**
- 8 voix prédéfinies uniquement
- Pas de clonage de voix

**Parfait pour :** Tests rapides, prototypes, voix génériques

### Mode 2 : 🔧 Pipeline (Clonage de voix)

**Avantages :**
- Clonage de voix illimité
- Voix réalistes de personnes célèbres
- Contrôle total sur la voix

**Limitations :**
- Latence plus élevée (500-800ms)
- Nécessite plus de clés API
- Coût ElevenLabs supplémentaire

**Parfait pour :** Personnages spécifiques, expériences immersives

## 🎭 Utilisation

### Exemple d'Interaction

```
>> Qui veux-tu incarner ?
> Emmanuel Macron

Choisis ton mode:
1. ⚡ Realtime (8 voix prédéfinies)
2. 🔧 Pipeline (clonage ElevenLabs)

> 2

[Recherche de samples vocaux...]
[Clonage de la voix...]

🎭 Agent prêt! Rejoins la room Daily.co pour parler avec Macron.
```

### Exemples de Personnages

**Personnes réelles :**
- "Emmanuel Macron"
- "Donald Trump" 
- "Morgan Freeman"
- "David Attenborough"

**Fictifs :**
- "Yoda (maître Jedi)"
- "Darth Vader"
- "Gandalf"
- "Spongebob"

**Originaux :**
- "Un vendeur de tapis marocain enthousiaste"
- "Un professeur de physique excentrique"
- "Un pirate des Caraïbes bourru"

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL VOICE AGENT v3.0                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MODE REALTIME (OpenAI Native)               │    │
│  │                                                          │    │
│  │  Microphone ──► Daily.co ──► OpenAI Realtime ──► HP     │    │
│  │                    (150ms latence)                       │    │
│  │                    8 voix prédéfinies                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              OR                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MODE PIPELINE (Modulaire)                   │    │
│  │                                                          │    │
│  │  Microphone ──► Deepgram STT ──► Text                   │    │
│  │                                     │                    │    │
│  │                                     ▼                    │    │
│  │                              GPT-4o-mini                 │    │
│  │                                     │                    │    │
│  │                                     ▼                    │    │
│  │  Haut-parleur ◄── ElevenLabs TTS ◄── Texte réponse      │    │
│  │                                                          │    │
│  │  Features:                                               │    │
│  │  • Voice Cloning (toute voix)                           │    │
│  │  • 500-800ms latence                                    │    │
│  │  • Contrôle total prosodie                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Structure du Projet

```
immersive-voice-agent/
├── universal_agent.py          # v2.0 - Mode Realtime uniquement
├── universal_agent_v3.py       # v3.0 - Architecture hybride ⭐
├── requirements.txt            # Dépendances
├── .env.example               # Template configuration
├── .env                       # Configuration (gitignored)
├── .gitignore                 # Fichiers ignorés
├── voice_samples/             # Cache samples vocaux
│   └── emmanuel_macron/
│       ├── sample1.mp3
│       └── sample2.wav
└── logs/                      # Logs quotidiens
    └── agent_2026-02-06.log
```

## 🔑 API Keys Requises

### Mode Realtime (Minimal)
| Service | Coût | Lien |
|---------|------|------|
| OpenAI | ~$0.06/min | [platform.openai.com](https://platform.openai.com) |
| Daily.co | Gratuit (10k min/mois) | [daily.co](https://daily.co) |

### Mode Pipeline (Complet)
| Service | Coût | Lien |
|---------|------|------|
| OpenAI | ~$0.003/1K tokens | [platform.openai.com](https://platform.openai.com) |
| Deepgram | $200 crédits gratuits | [deepgram.com](https://deepgram.com) |
| ElevenLabs | ~$0.30/1000 chars | [elevenlabs.io](https://elevenlabs.io) |
| Daily.co | Gratuit | [daily.co](https://daily.co) |

## 🛠️ Configuration Avancée

### Clonage de Voix Manuel

Si la recherche automatique ne trouve pas de samples :

```bash
# Créer le dossier
mkdir -p voice_samples/emmanuel_macron

# Placer des fichiers audio:
# - Format: MP3 ou WAV
# - Durée: 30 secondes minimum
# - Qualité: Propre, sans bruit de fond
# - Contenu: La personne qui parle normalement
```

### Personnalisation ElevenLabs

```env
# .env
ELEVENLABS_STABILITY=0.5          # 0-1 (bas = plus expressif)
ELEVENLABS_SIMILARITY_BOOST=0.75  # 0-1 (fidélité au sample)
```

### Sélection de Voix ElevenLabs

| Voice ID | Description |
|----------|-------------|
| XB0fDUnXU5powFXDhCwa | Male neutre (défaut) |
| XrM2xpfBbr21lHjPgkQJ | Français masculin |
| cjVigY5qzO86Huf0OWal | Américain masculin |
| N2lVS1w4EtoT3dr4eOWO | Voix aiguë/enfant |

## 🐛 Troubleshooting

### Erreur "invalid-token"
```
Solution: Configurer la room Daily.co en mode PUBLIC
```

### Erreur "Module not found"
```bash
# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Pas de son
```
1. Vérifier que le micro est autorisé dans le navigateur
2. Vérifier DAILY_ROOM_URL dans .env
3. Room Daily.co doit être en mode PUBLIC
```

### Latence élevée en mode Pipeline
```
Normal: 500-800ms avec ElevenLabs
Solution: Utiliser le mode Realtime pour moins de latence
```

## 📊 Comparaison des Modes

| Feature | Realtime | Pipeline |
|---------|----------|----------|
| **Latence** | ⚡ 150ms | 🔧 500-800ms |
| **Voix** | 8 prédéfinies | Illimitées (clonage) |
| **Coût** | $0.06/min | Variable |
| **Setup** | Simple | Complexe |
| **Clonage** | ❌ Non | ✅ Oui |
| **STT** | Whisper | Deepgram |
| **LLM** | GPT-4o RT | GPT-4o-mini |
| **TTS** | OpenAI | ElevenLabs |

## 🎯 Roadmap

- [x] Mode Realtime (OpenAI)
- [x] Mode Pipeline (Deepgram + ElevenLabs)
- [x] Clonage de voix ElevenLabs
- [x] Recherche automatique de samples
- [ ] Intégration YouTube-dl pour auto-download
- [ ] Support multi-langue amélioré
- [ ] Effects sonores en temps réel
- [ ] Mode conversation multi-participants

## ⚠️ Avertissements Légaux

**Clonage de voix :**
- ⚠️ Ne clonez que des voix dont vous avez l'autorisation
- ⚠️ Le clonage de voix de personnes sans consentement peut être illégal
- ⚠️ Utilisez uniquement à des fins éducatives/artistiques
- ✅ Préférez les voix fictives ou libres de droits

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir des issues
- Proposer des pull requests
- Suggérer de nouvelles features

## 📝 License

MIT License - Voir LICENSE pour les détails

---

**Créé avec ❤️ et beaucoup de café ☕**

*Powered by: GPT-4o-mini • OpenAI Realtime • Deepgram • ElevenLabs • Pipecat*
