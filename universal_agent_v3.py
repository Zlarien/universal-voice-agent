    #!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     UNIVERSAL VOICE AGENT v3.0                               ║
║                                                                              ║
║  Architecture Hybride : REALTIME vs STT-LLM-TTS Pipeline                     ║
║  Features:                                                                     ║
║    • Mode Realtime: OpenAI Realtime natif (voix prédéfinies)                 ║
║    • Mode Pipeline: Deepgram STT → GPT-4o-mini → ElevenLabs TTS              ║
║    • Clonage de voix automatique avec ElevenLabs                             ║
║    • Recherche intelligente de samples vocaux                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import sys
import time
import base64
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Literal, Dict, List, Callable
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI, OpenAIError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import box
import aiohttp

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.openai.realtime.events import (
    AudioConfiguration,
    AudioInput,
    InputAudioNoiseReduction,
    InputAudioTranscription,
    SemanticTurnDetection,
    SessionProperties,
)
from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
from pipecat.transports.daily.transport import DailyTransport, DailyParams

# Deepgram imports
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

# ElevenLabs imports
from elevenlabs import ElevenLabs, Voice, VoiceSettings, play
from elevenlabs.types import Voice as ElevenLabsVoice

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

load_dotenv(override=True)
console = Console()

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
    colorize=True
)
logger.add(
    "logs/agent_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)


class VoiceMode(Enum):
    """Available voice interaction modes."""
    REALTIME = auto()      # OpenAI Realtime native (faster, limited voices)
    PIPELINE = auto()      # Deepgram STT → GPT → ElevenLabs TTS (custom voices)


class VoiceType(str, Enum):
    """Available OpenAI Realtime voices."""
    ALLOY = "alloy"
    ASH = "ash"
    BALLAD = "ballad"
    CORAL = "coral"
    ECHO = "echo"
    SAGE = "sage"
    SHIMMER = "shimmer"
    VERSE = "verse"


class Ambiance(str, Enum):
    """Pre-defined ambient environments for immersion."""
    NONE = "none"
    SPACESHIP = "spaceship"
    TAVERN = "tavern"
    FOREST = "forest"
    CITY = "city"
    UNDERWATER = "underwater"
    STORM = "storm"
    BATTLEFIELD = "battlefield"


AMBIANCE_DESCRIPTIONS = {
    Ambiance.NONE: "",
    Ambiance.SPACESHIP: "Tu es à bord d'un vaisseau spatial. On entend le ronronnement des moteurs, les bips des consoles et parfois des annonces automatiques.",
    Ambiance.TAVERN: "Tu es dans une taverne animée. Il y a du bruit de fond : conversations, verres qui s'entrechoquent, musique de barde.",
    Ambiance.FOREST: "Tu es en pleine forêt. On entend les oiseaux, le vent dans les feuilles, des craquements de branches.",
    Ambiance.CITY: "Tu es dans une ville animée. Klaxons, sirènes au loin, foule qui passe.",
    Ambiance.UNDERWATER: "Tu es dans un environnement sous-marin. Sons étouffés, bulles, sonar.",
    Ambiance.STORM: "Il y a une tempête dehors. Tonnerre, pluie battante, vent violent.",
    Ambiance.BATTLEFIELD: "Tu es sur un champ de bataille. Explosions au loin, ordres criés, chaos.",
}


@dataclass
class CharacterProfile:
    """Complete character profile."""
    name: str
    system_prompt: str
    voice: VoiceType
    voice_mode: VoiceMode
    ambiance: Ambiance = Ambiance.NONE
    emotional_markers: list = field(default_factory=list)
    prosody_notes: str = ""
    elevenlabs_voice_id: Optional[str] = None  # For pipeline mode
    voice_samples: List[str] = field(default_factory=list)  # URLs/paths to voice samples


@dataclass
class VoiceCloneConfig:
    """Configuration for voice cloning."""
    name: str
    description: str
    samples: List[str]  # URLs or local paths
    stability: float = 0.5
    similarity_boost: float = 0.75


# ============================================================================
# MODULE 1: VOICE SAMPLE FINDER
# ============================================================================

class VoiceSampleFinder:
    """
    Finds voice samples for a given character/person.
    Uses multiple strategies: YouTube, text-to-speech datasets, etc.
    """
    
    def __init__(self):
        self.cache_dir = Path("voice_samples")
        self.cache_dir.mkdir(exist_ok=True)
        logger.debug("VoiceSampleFinder initialized")
    
    async def find_samples(self, character_name: str, max_samples: int = 3) -> List[str]:
        """
        Find voice samples for a character.
        
        Returns:
            List of sample file paths or URLs
        """
        logger.info(f"Recherche de samples vocaux pour: {character_name}")
        
        # Strategy 1: Check local cache
        cached_samples = self._check_cache(character_name)
        if cached_samples:
            logger.info(f"{len(cached_samples)} samples trouvés en cache")
            return cached_samples[:max_samples]
        
        # Strategy 2: Search YouTube (would require yt-dlp in production)
        # For now, we'll guide the user
        console.print(
            Panel(
                f"[bold yellow]Recherche de voix pour: {character_name}[/bold yellow]\n\n"
                f"Pour cloner une voix, j'ai besoin de samples audio propres (30s minimum).\n\n"
                f"[cyan]Options:[/cyan]\n"
                f"1. [bold]YouTube[/bold]: Cherche des interviews de {character_name}\n"
                f"2. [bold]Fichiers locaux[/bold]: Place des .mp3/.wav dans voice_samples/{character_name}/\n"
                f"3. [bold]Utiliser voix ElevenLabs[/bold]: Utilise une voix préfaite\n\n"
                f"[dim]Pour l'instant, je vais utiliser une voix ElevenLabs générique.[/dim]",
                title="Voice Cloning",
                border_style="yellow"
            )
        )
        
        return []
    
    def _check_cache(self, character_name: str) -> List[str]:
        """Check if we have cached samples for this character."""
        char_dir = self.cache_dir / character_name.lower().replace(" ", "_")
        if char_dir.exists():
            samples = list(char_dir.glob("*.mp3")) + list(char_dir.glob("*.wav"))
            return [str(s) for s in samples]
        return []


# ============================================================================
# MODULE 2: ELEVENLABS VOICE CLONER
# ============================================================================

class ElevenLabsVoiceCloner:
    """
    Manages voice cloning with ElevenLabs.
    Can clone from samples or use existing voices.
    """
    
    # Mapping of character names to suggested ElevenLabs voices
    VOICE_SUGGESTIONS = {
        "macron": "XrM2xpfBbr21lHjPgkQJ",  # French male voice
        "trump": "cjVigY5qzO86Huf0OWal",     # American male
        "zelensky": "XB0fDUnXU5powFXDhCwa",  # Deep male
        "gandalf": "TX3AEvVoIzMeN6CkEd4u",   # Old wise
        "yoda": "XB0fDUnXU5powFXDhCwa",      # Small wise
        "darth vader": "XB0fDUnXU5powFXDhCwa",  # Deep villain
        "spongebob": "N2lVS1w4EtoT3dr4eOWO",  # High pitched
    }
    
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ELEVENLABS_API_KEY not found. Required for pipeline mode."
            )
        self.client = ElevenLabs(api_key=api_key)
        self.cloned_voices: Dict[str, str] = {}  # name -> voice_id
        logger.debug("ElevenLabsVoiceCloner initialized")
    
    def suggest_voice(self, character_name: str) -> str:
        """
        Suggest the best ElevenLabs voice for a character.
        
        Returns:
            Voice ID to use
        """
        name_lower = character_name.lower()
        
        # Check direct matches
        for key, voice_id in self.VOICE_SUGGESTIONS.items():
            if key in name_lower:
                logger.info(f"Voix suggérée pour {character_name}: {key}")
                return voice_id
        
        # Default: return a neutral voice
        return "XB0fDUnXU5powFXDhCwa"  # Default male voice
    
    async def clone_voice(self, config: VoiceCloneConfig) -> str:
        """
        Clone a voice from samples.
        
        Args:
            config: VoiceCloneConfig with samples and settings
            
        Returns:
            Voice ID of the cloned voice
        """
        logger.info(f"Clonage de voix: {config.name}")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]Clonage de la voix en cours..."),
                console=console,
                transient=True
            ) as progress:
                progress.add_task("cloning", total=None)
                
                # Load sample files
                files = []
                for sample_path in config.samples:
                    if sample_path.startswith("http"):
                        # Download from URL
                        async with aiohttp.ClientSession() as session:
                            async with session.get(sample_path) as response:
                                content = await response.read()
                                files.append(BytesIO(content))
                    else:
                        # Load from file
                        with open(sample_path, "rb") as f:
                            files.append(BytesIO(f.read()))
                
                # Clone voice
                voice = self.client.voices.ivc.create(
                    name=f"{config.name}_cloned",
                    files=files,
                    description=config.description
                )
                
                voice_id = voice.voice_id
                self.cloned_voices[config.name] = voice_id
                
                logger.success(f"Voix clonée avec succès: {voice_id}")
                return voice_id
                
        except Exception as e:
            logger.error(f"Erreur lors du clonage: {e}")
            # Fallback to suggested voice
            fallback_id = self.suggest_voice(config.name)
            logger.warning(f"Fallback sur voix préfaite: {fallback_id}")
            return fallback_id
    
    def text_to_speech(self, text: str, voice_id: str, stability: float = 0.5) -> bytes:
        """
        Convert text to speech.
        
        Args:
            text: Text to speak
            voice_id: ElevenLabs voice ID
            stability: Voice stability (0-1)
            
        Returns:
            Audio bytes
        """
        try:
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=0.75,
                )
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio)
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Erreur TTS: {e}")
            raise


# ============================================================================
# MODULE 3: DEEPGRAM STT
# ============================================================================

class DeepgramSTT:
    """
    Real-time speech-to-text using Deepgram.
    """
    
    def __init__(self):
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "DEEPGRAM_API_KEY not found. Required for pipeline mode."
            )
        self.client = DeepgramClient(api_key)
        self.transcription_callbacks: List[Callable[[str], None]] = []
        self.dg_connection = None
        logger.debug("DeepgramSTT initialized")
    
    def on_transcription(self, callback: Callable[[str], None]):
        """Register a callback for transcription events."""
        self.transcription_callbacks.append(callback)
    
    async def start_streaming(self, language: str = "fr"):
        """Start real-time transcription stream."""
        logger.info("Démarrage du stream Deepgram STT...")
        
        self.dg_connection = self.client.listen.websocket.v("1")
        
        def on_message(self, result, **kwargs):
            transcript = result.channel.alternatives[0].transcript
            if transcript:
                for callback in self.transcription_callbacks:
                    callback(transcript)
        
        def on_error(self, error, **kwargs):
            logger.error(f"Deepgram error: {error}")
        
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        options = LiveOptions(
            model="nova-2",
            language=language,
            smart_format=True,
            interim_results=True,
        )
        
        self.dg_connection.start(options)
        logger.success("Deepgram STT stream démarré")
    
    def send_audio(self, audio_data: bytes):
        """Send audio chunk to Deepgram."""
        if self.dg_connection:
            self.dg_connection.send(audio_data)
    
    def finish(self):
        """Stop the transcription stream."""
        if self.dg_connection:
            self.dg_connection.finish()
            logger.info("Deepgram STT stream arrêté")


# ============================================================================
# MODULE 4: CASTING DIRECTOR (LLM)
# ============================================================================

class CastingDirector:
    """
    Uses GPT-4o-mini to analyze character requests and generate system prompts.
    """
    
    CASTING_PROMPT = """Tu es un expert en "Prompt Engineering" pour des acteurs IA vocaux.
Ton but est de créer une "Fiche Personnage" ultra-détaillée pour un agent vocal.

L'utilisateur va te donner un nom de personnage (réel, fictif ou générique).
Tu dois générer un profil COMPLET avec :

1. **SYSTEM_PROMPT IMMERSIF** : 
   - Définir le ton général, le vocabulaire, les tics de langage
   - Inclure le contexte et le background du personnage
   - Ajouter des RÈGLES STRICTES pour ne jamais sortir du personnage

2. **DIRECTIVES DE PROSODIE** :
   - Rythme de parole (rapide, lent, saccadé, fluide)
   - Intonations typiques (montantes, descendantes, monotones)
   - Volume et intensité (chuchotements, éclats, variations)

3. **MARQUEURS ÉMOTIONNELS** :
   - Liste des émotions principales du personnage
   - Comment ces émotions se manifestent vocalement

4. **CHOIX DE VOIX** (pour mode Realtime): 
   Choisis la plus adaptée parmi : [alloy, ash, ballad, coral, echo, sage, shimmer, verse]

Format JSON STRICT :
{
    "system_prompt": "Tu es [Nom]... [prompt complet avec prosodie intégrée]",
    "voice": "ash",
    "emotional_markers": ["fierté", "colère_froide", "sarcasme"],
    "prosody_notes": "Parle lentement avec des pauses dramatiques..."
}"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found")
        self.client = OpenAI(api_key=api_key)
        logger.debug("CastingDirector initialized")

    def generate_profile(
        self, 
        character_request: str, 
        voice_mode: VoiceMode,
        ambiance: Ambiance = Ambiance.NONE
    ) -> CharacterProfile:
        """Generate a complete character profile."""
        logger.info(f"Casting en cours pour: '{character_request}' (mode: {voice_mode.name})")
        
        ambiance_context = ""
        if ambiance != Ambiance.NONE:
            ambiance_context = f"\n\nCONTEXTE AMBIANT: {AMBIANCE_DESCRIPTIONS[ambiance]}"
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]Analyse du personnage..."),
                console=console,
                transient=True
            ) as progress:
                progress.add_task("casting", total=None)
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.CASTING_PROMPT},
                        {
                            "role": "user", 
                            "content": f"Crée le profil pour : {character_request}\n"
                                      f"Mode vocal: {voice_mode.name}\n"
                                      f"Règles strictes pour rester dans le personnage."
                                      f"{ambiance_context}"
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.8,
                    max_tokens=2000
                )
            
            data = json.loads(response.choices[0].message.content)
            
            # Build final prompt
            final_prompt = data["system_prompt"]
            if ambiance != Ambiance.NONE:
                final_prompt += f"\n\n[AMBIANCE SONORE]\n{AMBIANCE_DESCRIPTIONS[ambiance]}"
            
            profile = CharacterProfile(
                name=character_request,
                system_prompt=final_prompt,
                voice=VoiceType(data.get("voice", "ash")),
                voice_mode=voice_mode,
                ambiance=ambiance,
                emotional_markers=data.get("emotional_markers", []),
                prosody_notes=data.get("prosody_notes", "")
            )
            
            logger.success(f"Profil généré: '{character_request}'")
            return profile
            
        except Exception as e:
            logger.error(f"Erreur lors du casting: {e}")
            raise


# ============================================================================
# MODULE 5: PIPELINE MODE - STT → LLM → TTS
# ============================================================================

class PipelineVoiceEngine:
    """
    Voice engine using Deepgram STT + GPT-4o-mini + ElevenLabs TTS.
    Supports voice cloning for any character.
    """
    
    def __init__(self, profile: CharacterProfile):
        self.profile = profile
        self.stt = None
        self.llm = None
        self.tts = None
        self.voice_cloner = None
        self.conversation_history = []
        
        self._validate_environment()
        self._init_components()
        
        logger.debug(f"PipelineVoiceEngine initialized for: {profile.name}")
    
    def _validate_environment(self) -> None:
        """Validate required environment variables."""
        required = ["OPENAI_API_KEY", "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY", "DAILY_ROOM_URL"]
        missing = [var for var in required if not os.getenv(var)]
        
        if missing:
            raise EnvironmentError(f"Variables manquantes: {', '.join(missing)}")
    
    def _init_components(self):
        """Initialize STT, LLM, and TTS components."""
        # STT
        self.stt = DeepgramSTT()
        
        # LLM (OpenAI)
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # TTS (ElevenLabs with cloning)
        self.voice_cloner = ElevenLabsVoiceCloner()
    
    async def setup_voice(self) -> str:
        """
        Setup the voice for this character.
        Returns the voice ID to use.
        """
        # Find voice samples
        sample_finder = VoiceSampleFinder()
        samples = await sample_finder.find_samples(self.profile.name)
        
        if samples:
            # Clone the voice
            config = VoiceCloneConfig(
                name=self.profile.name,
                description=f"Voix de {self.profile.name} pour agent vocal",
                samples=samples,
                stability=0.6
            )
            voice_id = await self.voice_cloner.clone_voice(config)
        else:
            # Use suggested voice
            voice_id = self.voice_cloner.suggest_voice(self.profile.name)
            console.print(f"[yellow]Voix ElevenLabs suggérée utilisée: {voice_id}[/yellow]")
        
        return voice_id
    
    def generate_response(self, user_message: str) -> str:
        """Generate AI response using GPT-4o-mini."""
        # Add to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Keep only last 10 messages for context
        messages = [
            {"role": "system", "content": self.profile.system_prompt}
        ] + self.conversation_history[-10:]
        
        try:
            response = self.llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.9,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Erreur LLM: {e}")
            return "Je suis désolé, j'ai rencontré un problème technique."
    
    async def run(self) -> None:
        """Run the pipeline voice agent."""
        logger.info("Démarrage du Pipeline Voice Agent...")
        
        try:
            # Setup voice
            voice_id = await self.setup_voice()
            self.profile.elevenlabs_voice_id = voice_id
            
            console.print(
                Panel(
                    f"[bold green]Pipeline Mode Activé[/bold green]\n\n"
                    f"STT: [cyan]Deepgram[/cyan]\n"
                    f"LLM: [cyan]GPT-4o-mini[/cyan]\n"
                    f"TTS: [cyan]ElevenLabs[/cyan]\n"
                    f"Voix: [yellow]{voice_id}[/yellow]",
                    title="Configuration",
                    border_style="green"
                )
            )
            
            # Setup Daily transport
            daily_token = os.getenv("DAILY_TOKEN", "").strip() or None
            
            transport = DailyTransport(
                room_url=os.getenv("DAILY_ROOM_URL"),
                token=daily_token,
                bot_name=f"Pipeline-{self.profile.name[:15]}",
                params=DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                )
            )
            
            # Setup STT callback
            def on_transcript(transcript: str):
                logger.info(f"Utilisateur: {transcript}")
                
                # Generate response
                response = self.generate_response(transcript)
                logger.info(f"Assistant: {response}")
                
                # Convert to speech
                try:
                    audio_bytes = self.voice_cloner.text_to_speech(
                        response, 
                        voice_id,
                        stability=0.6
                    )
                    # Note: In full implementation, you'd stream this to Daily
                    logger.debug(f"Audio généré: {len(audio_bytes)} bytes")
                except Exception as e:
                    logger.error(f"Erreur TTS: {e}")
            
            self.stt.on_transcription(on_transcript)
            
            # Event handlers
            @transport.event_handler("on_client_connected")
            async def on_connect(transport, client):
                logger.success("Client connecté au Pipeline Agent!")
                console.print("[bold green]🎭 Pipeline Agent prêt![/bold green]")
                
                # Start STT
                await self.stt.start_streaming(language="fr")
            
            @transport.event_handler("on_client_disconnected")
            async def on_disconnect(transport, client):
                logger.info("Client déconnecté")
                self.stt.finish()
            
            # Run pipeline
            runner = PipelineRunner()
            await runner.run(PipelineTask(
                Pipeline([transport.input(), transport.output()]),
                params=PipelineParams(enable_metrics=True)
            ))
            
        except Exception as e:
            logger.error(f"Erreur Pipeline: {e}")
            raise


# ============================================================================
# MODULE 6: REALTIME MODE (Original)
# ============================================================================

class RealtimeVoiceEngine:
    """
    Voice engine using OpenAI Realtime API (native speech-to-speech).
    Faster but limited to preset voices.
    """
    
    def __init__(self, profile: CharacterProfile):
        self.profile = profile
        self._validate_environment()
        logger.debug(f"RealtimeVoiceEngine initialized for: {profile.name}")
    
    def _validate_environment(self) -> None:
        required = ["OPENAI_API_KEY", "DAILY_ROOM_URL"]
        missing = [var for var in required if not os.getenv(var)]
        
        if missing:
            raise EnvironmentError(f"Variables manquantes: {', '.join(missing)}")
    
    def _create_session_properties(self) -> SessionProperties:
        """Create OpenAI Realtime session properties."""
        turn_detection = SemanticTurnDetection(
            eagerness="high",
            create_response=True,
            interrupt_response=True
        )
        
        return SessionProperties(
            audio=AudioConfiguration(
                input=AudioInput(
                    transcription=InputAudioTranscription(model="whisper-1"),
                    turn_detection=turn_detection,
                    noise_reduction=InputAudioNoiseReduction(type="near_field"),
                )
            ),
            instructions=self.profile.system_prompt,
            voice=self.profile.voice.value,
            temperature=0.9,
            max_response_output_tokens=500,
        )
    
    async def run(self) -> None:
        """Run the realtime voice agent."""
        logger.info("Démarrage du Realtime Voice Agent...")
        
        try:
            daily_token = os.getenv("DAILY_TOKEN", "").strip() or None
            
            transport = DailyTransport(
                room_url=os.getenv("DAILY_ROOM_URL"),
                token=daily_token,
                bot_name=f"Realtime-{self.profile.name[:15]}",
                params=DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                )
            )
            
            session_properties = self._create_session_properties()
            
            llm = OpenAIRealtimeLLMService(
                api_key=os.getenv("OPENAI_API_KEY"),
                session_properties=session_properties,
            )
            
            initial_context = [
                {
                    "role": "user", 
                    "content": "La scène commence maintenant. Présente-toi brièvement."
                }
            ]
            context = LLMContext(initial_context)
            
            user_agg, assistant_agg = LLMContextAggregatorPair(context)
            
            pipeline = Pipeline([
                transport.input(),
                user_agg,
                llm,
                transport.output(),
                assistant_agg,
            ])
            
            task = PipelineTask(
                pipeline, 
                params=PipelineParams(
                    enable_metrics=True,
                    allow_interruptions=True,
                )
            )
            
            @transport.event_handler("on_client_connected")
            async def on_connect(transport, client):
                logger.success("Client connecté au Realtime Agent!")
                console.print("[bold green]⚡ Realtime Agent prêt![/bold green]")
            
            @transport.event_handler("on_client_disconnected")
            async def on_disconnect(transport, client):
                logger.info("Client déconnecté")
                await task.cancel()
            
            @transport.event_handler("on_error")
            async def on_error(transport, error):
                logger.error(f"Erreur transport: {error}")
            
            logger.info("En attente de connexion...")
            runner = PipelineRunner()
            await runner.run(task)
            
        except Exception as e:
            logger.error(f"Erreur Realtime: {e}")
            raise


# ============================================================================
# MODULE 7: CONSOLE UI
# ============================================================================

class TerminalUI:
    """Beautiful console interface."""
    
    BANNER = """
[bold cyan]
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██╗   ██╗███╗   ██╗██╗██╗   ██╗███████╗██████╗ ███████╗ █████╗ ██╗         ║
║   ██║   ██║████╗  ██║██║██║   ██║██╔════╝██╔══██╗██╔════╝██╔══██╗██║         ║
║   ██║   ██║██╔██╗ ██║██║██║   ██║█████╗  ██████╔╝█████╗  ███████║██║         ║
║   ██║   ██║██║╚██╗██║██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██╔══╝  ██╔══██║██║         ║
║   ╚██████╔╝██║ ╚████║██║ ╚████╔╝ ███████╗██║  ██║███████╗██║  ██║███████╗    ║
║    ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝    ║
║                                                                               ║
║                    [white]HYBRID VOICE AGENT v3.0[/white]                              ║
║         [dim]Realtime vs Pipeline • Voice Cloning • Any Character[/dim]              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
[/bold cyan]"""

    def __init__(self):
        self.console = console
    
    def display_banner(self) -> None:
        self.console.print(self.BANNER)
    
    def select_voice_mode(self) -> VoiceMode:
        """Let user choose voice interaction mode."""
        table = Table(
            title="[bold magenta]Mode de Voix[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta"
        )
        table.add_column("Code", style="cyan", width=8)
        table.add_column("Mode", style="green")
        table.add_column("Description", style="dim")
        table.add_column("Voix", style="yellow")
        
        modes = [
            ("1", "⚡ Realtime", "OpenAI natif, ultra rapide", "8 voix prédéfinies"),
            ("2", "🔧 Pipeline", "STT→LLM→TTS, plus flexible", "Clonage ElevenLabs"),
        ]
        
        for code, name, desc, voices in modes:
            table.add_row(code, name, desc, voices)
        
        self.console.print(table)
        
        choice = Prompt.ask(
            "[bold cyan]Choisis ton mode[/bold cyan]",
            default="1",
            choices=["1", "2"]
        )
        
        return VoiceMode.REALTIME if choice == "1" else VoiceMode.PIPELINE
    
    def display_ambiance_menu(self) -> Ambiance:
        """Display ambiance selection menu."""
        table = Table(
            title="[bold magenta]Ambiances[/bold magenta]",
            box=box.ROUNDED,
            border_style="magenta"
        )
        table.add_column("Code", style="cyan", width=4)
        table.add_column("Ambiance", style="green")
        
        ambiance_list = [
            ("0", "Aucune"),
            ("1", "Vaisseau Spatial"),
            ("2", "Taverne"),
            ("3", "Forêt"),
            ("4", "Ville"),
            ("5", "Sous-marin"),
            ("6", "Tempête"),
            ("7", "Champ de Bataille"),
        ]
        
        for code, name in ambiance_list:
            table.add_row(code, name)
        
        self.console.print(table)
        
        choice = Prompt.ask(
            "[bold cyan]Ambiance[/bold cyan]",
            default="0",
            choices=["0", "1", "2", "3", "4", "5", "6", "7"]
        )
        
        ambiance_map = {
            "0": Ambiance.NONE,
            "1": Ambiance.SPACESHIP,
            "2": Ambiance.TAVERN,
            "3": Ambiance.FOREST,
            "4": Ambiance.CITY,
            "5": Ambiance.UNDERWATER,
            "6": Ambiance.STORM,
            "7": Ambiance.BATTLEFIELD,
        }
        
        return ambiance_map.get(choice, Ambiance.NONE)
    
    def get_character_input(self) -> str:
        """Get character input from user."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold]Exemples:[/bold]\n"
                "[dim]• Emmanuel Macron[/dim]\n"
                "[dim]• Yoda (maître Jedi)[/dim]\n"
                "[dim]• Un vendeur de tapis marocain[/dim]\n"
                "[dim]• Darth Vader[/dim]\n"
                "[dim]• Sherlock Holmes[/dim]",
                title="[cyan]Personnages[/cyan]",
                border_style="dim"
            )
        )
        
        character = Prompt.ask(
            "\n[bold green]>>[/bold green] [bold cyan]Qui veux-tu incarner ?[/bold cyan]"
        )
        
        return character.strip()
    
    def display_profile(self, profile: CharacterProfile) -> None:
        """Display the generated character profile."""
        self.console.print()
        
        profile_text = Text()
        profile_text.append("Personnage: ", style="bold")
        profile_text.append(f"{profile.name}\n", style="cyan")
        profile_text.append("Mode: ", style="bold")
        profile_text.append(f"{profile.voice_mode.name}\n", style="magenta")
        profile_text.append("Voix: ", style="bold")
        profile_text.append(f"{profile.voice.value}\n", style="yellow")
        
        if profile.ambiance != Ambiance.NONE:
            profile_text.append("Ambiance: ", style="bold")
            profile_text.append(f"{profile.ambiance.value}\n", style="green")
        
        if profile.emotional_markers:
            profile_text.append("Émotions: ", style="bold")
            profile_text.append(f"{', '.join(profile.emotional_markers)}\n", style="green")
        
        self.console.print(
            Panel(
                profile_text,
                title="[bold green]Profil[/bold green]",
                border_style="green",
                box=box.DOUBLE
            )
        )
    
    def display_connection_info(self) -> None:
        """Display connection instructions."""
        room_url = os.getenv("DAILY_ROOM_URL", "Non configuré")
        
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Rejoins la session:[/bold]\n\n"
                f"1. Ouvre: [link={room_url}]{room_url}[/link]\n"
                f"2. Autorise le micro\n"
                f"3. Parle avec ton personnage !\n\n"
                f"[dim]Ctrl+C pour quitter[/dim]",
                title="[bold yellow]Connexion[/bold yellow]",
                border_style="yellow"
            )
        )
    
    def display_error(self, error: str) -> None:
        """Display an error message."""
        self.console.print(
            Panel(
                f"[bold red]{error}[/bold red]",
                title="Erreur",
                border_style="red"
            )
        )
    
    def display_goodbye(self) -> None:
        """Display goodbye message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold cyan]Merci d'avoir utilisé Universal Voice Agent ![/bold cyan]",
                border_style="cyan"
            )
        )


# ============================================================================
# MODULE 8: MAIN ORCHESTRATOR
# ============================================================================

class UniversalVoiceAgent:
    """Main application class."""
    
    def __init__(self):
        self.ui = TerminalUI()
        self.casting_director = None
        
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("voice_samples", exist_ok=True)
    
    async def run(self) -> None:
        """Main application loop."""
        self._ensure_directories()
        self.ui.display_banner()
        
        try:
            # Select voice mode first
            voice_mode = self.ui.select_voice_mode()
            
            # Validate environment based on mode
            try:
                self.casting_director = CastingDirector()
            except EnvironmentError as e:
                self.ui.display_error(str(e))
                return
            
            # Get character input
            character_request = self.ui.get_character_input()
            if not character_request:
                self.ui.display_error("Entrée vide")
                return
            
            # Get ambiance
            console.print()
            ambiance = self.ui.display_ambiance_menu()
            
            # Generate profile
            try:
                profile = self.casting_director.generate_profile(
                    character_request, 
                    voice_mode,
                    ambiance
                )
            except Exception as e:
                self.ui.display_error(f"Erreur casting: {e}")
                return
            
            # Display profile
            self.ui.display_profile(profile)
            self.ui.display_connection_info()
            
            # Run appropriate engine
            try:
                if voice_mode == VoiceMode.REALTIME:
                    engine = RealtimeVoiceEngine(profile)
                else:
                    engine = PipelineVoiceEngine(profile)
                
                await engine.run()
                
            except EnvironmentError as e:
                self.ui.display_error(str(e))
                logger.error(f"Engine error: {e}")
                return
            except Exception as e:
                self.ui.display_error(f"Erreur: {e}")
                logger.error(f"Engine error: {e}")
                return
                
        except KeyboardInterrupt:
            logger.info("Interrompu par l'utilisateur")
        finally:
            self.ui.display_goodbye()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point."""
    agent = UniversalVoiceAgent()
    
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        console.print(f"[bold red]Erreur inattendue: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
