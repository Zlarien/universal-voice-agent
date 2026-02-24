# Immersive Voice Agent

> **Incarnez n'importe quel personnage grace a l'IA vocale**

Agent vocal immersif avec deux interfaces : une **application web Gradio** deployable sur HuggingFace Spaces et un **agent terminal** pour usage local. GPT-4o-mini genere le profil du personnage, Deepgram transcrit la voix, ElevenLabs la synthetise.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Gradio](https://img.shields.io/badge/Gradio-Web%20App-orange.svg)

---

## Deux Interfaces

| | Web (app.py) | Terminal (universal\_agent\_v3.py) |
|---|---|---|
| **Pipeline** | Deepgram STT + GPT-4o-mini + ElevenLabs TTS | OpenAI Realtime **ou** Pipeline |
| **Transport** | Navigateur (micro Gradio) | Daily.co (WebRTC) |
| **Deploiement** | HuggingFace Spaces (CPU Basic) | Local |
| **Clonage de voix** | Oui (upload de samples) | Oui (dossier voice\_samples/) |
| **Prerequis** | 3 cles API | 3-4 cles API + Daily.co |

---

## Installation

```bash
git clone https://github.com/votre-username/immersive-voice-agent.git
cd immersive-voice-agent

python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

Copiez `.env.example` vers `.env` et remplissez vos cles :

```env
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
```

---

## Obtenir les Cles API

| Service | Lien | Gratuit ? |
|---------|------|-----------|
| OpenAI | [platform.openai.com](https://platform.openai.com/api-keys) | Credits prepaid |
| Deepgram | [console.deepgram.com](https://console.deepgram.com/signup) | $200 de credits offerts |
| ElevenLabs | [elevenlabs.io](https://elevenlabs.io/app/sign-up) | Plan gratuit disponible |

---

## Utilisation

### Application Web (Gradio)

```bash
python app.py
```

Ouvrez `http://localhost:7860` dans votre navigateur.

1. Entrez un nom de personnage (ex: *Emmanuel Macron*, *Yoda*, *Un pirate*)
2. Choisissez la longueur du contexte (Court / Moyen / Long)
3. Optionnel : selectionnez une ambiance, activez le clonage de voix
4. Cliquez **Lancer l'Agent**
5. Parlez dans le micro — l'agent repond avec la voix du personnage

#### Deploiement HuggingFace Spaces

1. Creez un Space avec le SDK **Gradio**
2. Poussez le code (au minimum `app.py` + `requirements.txt`)
3. Dans **Settings > Secrets**, ajoutez `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`
4. Le Space demarre automatiquement

### Agent Terminal (local)

```bash
python universal_agent_v3.py
```

Necessite un compte [Daily.co](https://daily.co) (gratuit). Ajoutez dans `.env` :

```env
DAILY_ROOM_URL=https://votre-domaine.daily.co/room-name
DAILY_TOKEN=          # vide pour room publique
```

Deux modes disponibles :
- **Realtime** : OpenAI Realtime natif (8 voix, ~150ms)
- **Pipeline** : Deepgram STT + GPT-4o-mini + ElevenLabs TTS (clonage de voix)

---

## Exemples de Personnages

| Personnage | Style | Ambiance suggeree |
|------------|-------|-------------------|
| Emmanuel Macron | Discours presidentiel | Aucune |
| Yoda | Syntaxe inversee, sagesse | Foret |
| Darth Vader | Voix grave, menacant | Vaisseau Spatial |
| Gandalf | Bienveillant, mysterieux | Taverne |
| Un vendeur de tapis marocain | Enthousiaste, negociateur | Ville |
| Un capitaine de sous-marin | Autoritaire, precis | Sous-marin |

**Prompts creatifs** :
- "Un robot qui decouvre les emotions humaines"
- "Un chef cuisinier francais qui s'enerve facilement"
- "Un narrateur de documentaire nature facon David Attenborough"

---

## Architecture

```
immersive-voice-agent/
├── app.py                  # Interface web Gradio (HuggingFace Spaces)
├── universal_agent_v3.py   # Agent terminal (Realtime + Pipeline)
├── requirements.txt        # Dependances Python
├── .env                    # Variables d'environnement (non versionne)
├── .env.example            # Template de configuration
├── .gitignore
├── README.md
├── voice_samples/          # Samples vocaux pour clonage (optionnel)
│   └── emmanuel_macron/
│       └── sample.mp3
└── logs/                   # Logs (terminal uniquement)
```

### Pipeline Web (app.py)

```
Micro navigateur ──> Deepgram STT ──> GPT-4o-mini ──> ElevenLabs TTS ──> Audio navigateur
                     (nova-2, fr)     (casting +       (eleven_multilingual_v2)
                                       conversation)
```

### Pipeline Terminal - Mode Realtime

```
Micro ──> Daily.co ──> OpenAI Realtime (speech-to-speech) ──> Daily.co ──> Haut-parleur
```

### Pipeline Terminal - Mode Pipeline

```
Micro ──> Daily.co ──> Deepgram STT ──> GPT-4o-mini ──> ElevenLabs TTS ──> Daily.co ──> HP
```

---

## Clonage de Voix

### Via l'interface web

1. Cochez **Clonage de voix**
2. Uploadez 1 a 3 fichiers audio (.mp3 / .wav) de la personne a cloner
3. Lancez l'agent — ElevenLabs clone la voix automatiquement

### Via le terminal

Placez des fichiers audio dans `voice_samples/<nom_personnage>/` :

```bash
mkdir -p voice_samples/emmanuel_macron
# Ajoutez des .mp3 ou .wav (30s minimum, voix propre)
```

Si aucun sample n'est disponible, une voix ElevenLabs predefinie est utilisee.

---

## Depannage

| Probleme | Solution |
|----------|----------|
| "Cle API manquante" | Verifiez `.env` ou les Secrets HuggingFace |
| Pas de transcription | Verifiez que le micro est autorise dans le navigateur |
| Erreur STT / TTS | Verifiez vos credits Deepgram / ElevenLabs |
| "Rate limit exceeded" | Attendez ou verifiez votre quota OpenAI |
| Audio muet (terminal) | Verifiez `DAILY_ROOM_URL`, room en mode PUBLIC |

---

## Licence

MIT License

---

*Powered by GPT-4o-mini, Deepgram, ElevenLabs, Gradio, Pipecat*
