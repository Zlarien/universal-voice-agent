# Immersive Voice Agent

> **Incarnez n'importe quel personnage grâce à l'IA vocale en temps réel**

Un agent vocal immersif qui utilise GPT-4o-mini pour le "casting" intelligent et OpenAI Realtime pour la synthèse vocale en temps réel via Pipecat.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-Realtime-orange.svg)

---

## Fonctionnalités

- **Casting Intelligent** : GPT-4o-mini analyse votre demande et génère automatiquement le profil vocal parfait
- **Voix en Temps Réel** : Conversation fluide grâce à OpenAI Realtime (Speech-to-Speech)
- **Interruptions Naturelles** : Coupez la parole à l'IA naturellement, comme dans une vraie conversation
- **Ambiances Sonores** : 7 environnements immersifs (vaisseau spatial, taverne, forêt, etc.)
- **Prosodie Avancée** : Intonations, pauses dramatiques et marqueurs émotionnels personnalisés
- **Interface Futuriste** : Terminal stylisé avec Rich pour une expérience visuelle premium

---

## Prérequis

- Python 3.10 ou supérieur
- Un compte OpenAI avec accès à l'API (GPT-4o-mini + Realtime)
- Un compte Daily.co (gratuit) pour le transport audio

---

## Installation

### 1. Cloner le repository

```bash
git clone https://github.com/votre-username/immersive-voice-agent.git
cd immersive-voice-agent
```

### 2. Créer un environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet :

```env
# OpenAI API Key (obligatoire)
OPENAI_API_KEY=sk-votre-cle-api-openai

# Daily.co Room URL (obligatoire)
DAILY_ROOM_URL=https://votre-domaine.daily.co/votre-room

# Daily.co Token (optionnel mais recommandé)
DAILY_TOKEN=votre-token-daily
```

---

## Obtenir les Clés API

### OpenAI API Key

1. Rendez-vous sur [platform.openai.com](https://platform.openai.com/)
2. Connectez-vous ou créez un compte
3. Allez dans **API Keys** > **Create new secret key**
4. Copiez la clé (elle ne sera plus visible après)
5. Assurez-vous d'avoir des crédits sur votre compte

> **Note** : L'API Realtime nécessite un accès spécifique. Vérifiez que votre compte y a accès.

### Daily.co Room

1. Créez un compte gratuit sur [daily.co](https://www.daily.co/)
2. Dans le Dashboard, cliquez sur **Rooms** > **Create Room**
3. Configurez votre room :
   - **Room name** : choisissez un nom (ex: `voice-agent-room`)
   - **Privacy** : `public` pour les tests
4. Copiez l'URL de la room (format: `https://votre-domaine.daily.co/voice-agent-room`)

**Optionnel - Token d'authentification :**
1. Allez dans **Developers** > **API Keys**
2. Créez une clé API
3. Utilisez-la pour générer des tokens de meeting (voir documentation Daily.co)

---

## Utilisation

### Lancement

```bash
python universal_agent.py
```

### Workflow

1. **Démarrage** : L'interface futuriste s'affiche
2. **Choix du personnage** : Décrivez qui vous voulez incarner
3. **Sélection d'ambiance** : Choisissez un environnement sonore (optionnel)
4. **Casting** : L'IA génère le profil vocal optimal
5. **Connexion** : Ouvrez l'URL Daily.co dans votre navigateur
6. **Conversation** : Parlez avec votre personnage !

---

## Exemples de Personnages

### Personnages Fictifs

| Personnage | Description | Ambiance Recommandée |
|------------|-------------|---------------------|
| **Yoda** | Maître Jedi sage, syntaxe inversée | Forêt |
| **GLaDOS** | IA sarcastique de Portal | Vaisseau Spatial |
| **Gandalf** | Magicien bienveillant mais mystérieux | Taverne |
| **Dark Vador** | Seigneur Sith intimidant | Vaisseau Spatial |
| **Jack Sparrow** | Pirate excentrique et rusé | Taverne |

### Personnages Historiques

| Personnage | Description | Ambiance Recommandée |
|------------|-------------|---------------------|
| **Napoléon Bonaparte** | Empereur stratège et ambitieux | Champ de Bataille |
| **Cléopâtre** | Reine d'Égypte, charisme légendaire | Aucune |
| **Albert Einstein** | Physicien génial et espiègle | Aucune |
| **Sherlock Holmes** | Détective logique et observateur | Ville |

### Personnages Génériques

| Personnage | Description | Ambiance Recommandée |
|------------|-------------|---------------------|
| **Un barman de speakeasy des années 20** | Mystérieux, accent de l'époque | Taverne |
| **Un capitaine de sous-marin** | Autoritaire mais bienveillant | Sous-marin |
| **Un vendeur de tapis marocain** | Enthousiaste, négociateur né | Ville |
| **Un druide de forêt ancienne** | Sage, connecté à la nature | Forêt |
| **Un commandant de vaisseau spatial** | Professionnel, calme sous pression | Vaisseau Spatial |

### Prompts Créatifs Avancés

```
"Un robot qui découvre les émotions humaines pour la première fois"

"Un fantôme victorien poli qui hante poliment sa propre maison"

"Un chef cuisinier français passionné qui s'énerve facilement"

"Un narrateur de documentaire nature façon David Attenborough"

"Un vendeur de voitures d'occasion BEAUCOUP trop enthousiaste"
```

---

## Architecture du Projet

```
immersive-voice-agent/
├── universal_agent.py    # Application principale
├── requirements.txt      # Dépendances Python
├── .env                  # Variables d'environnement (non versionné)
├── .gitignore           # Fichiers à ignorer par Git
├── README.md            # Cette documentation
└── logs/                # Logs de l'application (auto-généré)
    └── agent_YYYY-MM-DD.log
```

### Modules Internes

Le code est organisé en 4 modules principaux :

1. **CastingDirector** : Génération intelligente des profils via GPT-4o-mini
2. **VoiceEngine** : Orchestration du pipeline Pipecat + OpenAI Realtime
3. **TerminalUI** : Interface console stylisée avec Rich
4. **ImmersiveVoiceAgent** : Coordinateur principal de l'application

---

## Configuration Avancée

### Personnaliser les Voix

Les voix disponibles sont :

| Voix | Description |
|------|-------------|
| `alloy` | Neutre, polyvalente |
| `ash` | Grave, posée, mature |
| `ballad` | Chaleureuse, expressive |
| `coral` | Claire, amicale |
| `echo` | Profonde, mystérieuse |
| `sage` | Calme, sage, réfléchie |
| `shimmer` | Brillante, énergique |
| `verse` | Poétique, mélodieuse |

### Ajouter une Ambiance Personnalisée

Modifiez le dictionnaire `AMBIANCE_DESCRIPTIONS` dans `universal_agent.py` :

```python
AMBIANCE_DESCRIPTIONS = {
    # ... ambiances existantes ...
    Ambiance.CUSTOM: "Description de votre ambiance personnalisée...",
}
```

### Ajuster la Sensibilité aux Interruptions

Dans la méthode `_create_session_properties` de `VoiceEngine` :

```python
turn_detection = SemanticTurnDetection(
    eagerness=0.8,  # 0.0 à 1.0 - Plus haut = plus réactif
    create_response=True,
    interrupt_response=True
)
```

---

## Dépannage

### "OPENAI_API_KEY not found"

- Vérifiez que le fichier `.env` existe à la racine du projet
- Vérifiez que la clé est correctement formatée (commence par `sk-`)
- Relancez le terminal après avoir créé le fichier `.env`

### "Connection refused" sur Daily.co

- Vérifiez l'URL de votre room Daily.co
- Assurez-vous que la room existe et est active
- Testez l'URL directement dans votre navigateur

### L'IA ne répond pas / Audio muet

1. Autorisez l'accès au microphone dans votre navigateur
2. Vérifiez que votre micro fonctionne (test dans les paramètres système)
3. Consultez les logs dans `logs/agent_YYYY-MM-DD.log`

### Erreur "Rate limit exceeded"

- Vous avez atteint la limite de requêtes OpenAI
- Attendez quelques minutes ou vérifiez votre quota sur platform.openai.com

---

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit vos changements (`git commit -m 'Add amazing feature'`)
4. Push sur la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

---

## Licence

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## Remerciements

- [Pipecat](https://github.com/pipecat-ai/pipecat) - Framework de pipelines vocaux
- [OpenAI](https://openai.com) - API GPT-4o-mini et Realtime
- [Daily.co](https://daily.co) - Infrastructure de communication en temps réel
- [Rich](https://github.com/Textualize/rich) - Interface terminal magnifique
- [Loguru](https://github.com/Delgan/loguru) - Logging simplifié

---

<p align="center">
  <strong>Créé avec passion pour l'immersion vocale</strong><br>
  <em>Que la Force (vocale) soit avec vous !</em>
</p>
