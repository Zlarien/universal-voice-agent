"""
Immersive Voice Agent - Gradio Web Frontend
Pipeline: Deepgram STT -> GPT-4o-mini -> ElevenLabs TTS
Deployable on HuggingFace Spaces (CPU Basic)
"""

import json
import os
import tempfile
from io import BytesIO
import gradio as gr
from deepgram import DeepgramClient
from elevenlabs import ElevenLabs
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AMBIANCE_DESCRIPTIONS = {
    "Aucune": "",
    "Vaisseau Spatial": "Tu es a bord d'un vaisseau spatial. On entend le ronronnement des moteurs, les bips des consoles et parfois des annonces automatiques.",
    "Taverne": "Tu es dans une taverne animee. Il y a du bruit de fond : conversations, verres qui s'entrechoquent, musique de barde.",
    "Foret": "Tu es en pleine foret. On entend les oiseaux, le vent dans les feuilles, des craquements de branches.",
    "Ville": "Tu es dans une ville animee. Klaxons, sirenes au loin, foule qui passe.",
    "Sous-marin": "Tu es dans un environnement sous-marin. Sons etouffes, bulles, sonar.",
    "Tempete": "Il y a une tempete dehors. Tonnerre, pluie battante, vent violent.",
    "Champ de Bataille": "Tu es sur un champ de bataille. Explosions au loin, ordres cries, chaos.",
}
VOICE_SUGGESTIONS = {
    "macron": "SOLYcAMMMFvdbTCfUWWU",  # Une voix masculine posée
    "trump": "G17SuINrv2H9FC6nvetn",   # Une voix masculine forte
    "zelensky": "G17SuINrv2H9FC6nvetn",
    "gandalf": "G17SuINrv2H9FC6nvetn",
    "yoda": "qr9D67rNgxf5xNgv46nx",
    "darth vader": "NxGA8X3YhTrnf3TRQf6Q",
    "spongebob": "qr9D67rNgxf5xNgv46nx",
}
 


DEFAULT_VOICE_ID = "SOLYcAMMMFvdbTCfUWWU"

CONTEXT_LENGTH_MAP = {
    "Court": 6,
    "Moyen": 14,
    "Long": 30,
}

CASTING_PROMPT = """Tu es un expert en "Prompt Engineering" pour des acteurs IA vocaux.
Ton but est de creer une "Fiche Personnage" ultra-detaillee pour un agent vocal.
L'utilisateur va te donner un nom de personnage (reel, fictif ou generique).
Tu dois generer un profil COMPLET avec :
1. **SYSTEM_PROMPT IMMERSIF** :
   - Definir le ton general, le vocabulaire, les tics de langage
   - Inclure le contexte et le background du personnage
   - Ajouter des REGLES STRICTES pour ne jamais sortir du personnage
2. **DIRECTIVES DE PROSODIE** :
   - Rythme de parole (rapide, lent, saccade, fluide)
   - Intonations typiques (montantes, descendantes, monotones)
   - Volume et intensite (chuchotements, eclats, variations)
3. **MARQUEURS EMOTIONNELS** :
   - Liste des emotions principales du personnage
   - Comment ces emotions se manifestent vocalement
4. **CHOIX DE VOIX** :
   Choisis la plus adaptee parmi : [alloy, ash, ballad, coral, echo, sage, shimmer, verse]
Format JSON STRICT :
{
    "system_prompt": "Tu es [Nom]... [prompt complet avec prosodie integree]",
    "voice": "ash",
    "emotional_markers": ["fierte", "colere_froide", "sarcasme"],
    "prosody_notes": "Parle lentement avec des pauses dramatiques..."
}"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_openai() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("Cle API manquante : OPENAI_API_KEY. Configurez-la dans les Secrets HuggingFace.")
    return OpenAI(api_key=key)


def _get_deepgram() -> DeepgramClient:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise EnvironmentError("Cle API manquante : DEEPGRAM_API_KEY. Configurez-la dans les Secrets HuggingFace.")
    return DeepgramClient(api_key=key)


def _get_elevenlabs() -> ElevenLabs:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise EnvironmentError("Cle API manquante : ELEVENLABS_API_KEY. Configurez-la dans les Secrets HuggingFace.")
    return ElevenLabs(api_key=key)


def suggest_voice(character_name: str) -> str:
    """Return the best ElevenLabs voice ID for a character."""
    name_lower = character_name.lower()
    for key, voice_id in VOICE_SUGGESTIONS.items():
        if key in name_lower:
            return voice_id
    return DEFAULT_VOICE_ID


def generate_profile(character_name: str, ambiance: str) -> dict:
    """Call GPT-4o-mini to build a character profile (system_prompt, voice, etc.)."""
    client = _get_openai()

    ambiance_context = ""
    if ambiance != "Aucune":
        ambiance_context = f"\n\nCONTEXTE AMBIANT: {AMBIANCE_DESCRIPTIONS[ambiance]}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CASTING_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Cree le profil pour : {character_name}\n"
                    f"Regles strictes pour rester dans le personnage."
                    f"{ambiance_context}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
        max_tokens=2000,
    )

    data = json.loads(response.choices[0].message.content)

    system_prompt = data.get("system_prompt", "")
    if ambiance != "Aucune":
        system_prompt += f"\n\n[AMBIANCE SONORE]\n{AMBIANCE_DESCRIPTIONS[ambiance]}"

    return {
        "system_prompt": system_prompt,
        "voice": data.get("voice", "ash"),
        "emotional_markers": data.get("emotional_markers", []),
        "prosody_notes": data.get("prosody_notes", ""),
    }


def clone_voice(name: str, sample_files: list[str]) -> str:
    """Clone a voice from uploaded sample files via ElevenLabs IVC API."""
    client = _get_elevenlabs()
    files = []
    for path in sample_files:
        with open(path, "rb") as f:
            files.append(BytesIO(f.read()))

    voice = client.voices.ivc.create(
        name=f"{name}_cloned",
        files=files,
        description=f"Voix clonee de {name} pour agent vocal",
    )
    return voice.voice_id


def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file bypassing the SDK to avoid versioning errors."""
    import requests
    import os
    
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&language=fr"
    
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav"
    }
    
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
        
    response = requests.post(url, headers=headers, data=audio_bytes)
    result = response.json()
    
    channels = result.get("results", {}).get("channels", [])
    if not channels:
        return ""
        
    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        return ""
        
    return alternatives[0].get("transcript", "")


def llm_respond(system_prompt: str, conversation: list[dict], context_length: str) -> str:
    """Generate a response with GPT-4o-mini."""
    client = _get_openai()
    n = CONTEXT_LENGTH_MAP.get(context_length, 14)
    messages = [{"role": "system", "content": system_prompt}] + conversation[-n:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.9,
        max_tokens=500,
    )
    return response.choices[0].message.content


def text_to_speech(text: str, voice_id: str) -> str:
    """Convert text to speech with ElevenLabs. Returns path to mp3 file."""
    client = _get_elevenlabs()
    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(audio_iter)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(audio_bytes)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Gradio Event Handlers
# ---------------------------------------------------------------------------


def launch_agent(
    character_name: str,
    context_length: str,
    ambiance: str,
    voice_clone_enabled: bool,
    clone_files,
    state: dict,
):
    """Initialize the agent with a character profile."""
    if not character_name or not character_name.strip():
        return (
            state,
            gr.update(interactive=False),
            "Veuillez entrer un nom de personnage.",
            [],
        )

    try:
        profile = generate_profile(character_name.strip(), ambiance)
    except Exception as exc:
        return (
            state,
            gr.update(interactive=False),
            f"Erreur lors du casting : {exc}",
            [],
        )

    # Resolve voice
    voice_id = DEFAULT_VOICE_ID
    if voice_clone_enabled and clone_files:
        try:
            paths = [f.name if hasattr(f, "name") else f for f in clone_files]
            voice_id = clone_voice(character_name.strip(), paths)
        except Exception as exc:
            voice_id = suggest_voice(character_name.strip())
            status_extra = f" (clonage echoue : {exc}, voix par defaut utilisee)"
        else:
            status_extra = " (voix clonee)"
    else:
        voice_id = suggest_voice(character_name.strip())
        status_extra = ""

    state = {
        "active": True,
        "system_prompt": profile["system_prompt"],
        "voice_id": voice_id,
        "conversation": [],
        "character_name": character_name.strip(),
        "context_length": context_length,
    }

    markers = ", ".join(profile.get("emotional_markers", []))
    status = (
        f"Agent actif : {character_name.strip()}{status_extra}\n"
        f"Prosodie : {profile.get('prosody_notes', 'N/A')}\n"
        f"Emotions : {markers or 'N/A'}"
    )

    return (
        state,
        gr.update(interactive=True),
        status,
        [],  # clear chatbot
    )


def process_audio(audio_path, state: dict, chatbot_history: list):
    """Handle a recorded audio clip: STT -> LLM -> TTS."""
    if not state or not state.get("active"):
        return state, chatbot_history, None, "Agent non actif. Lancez l'agent d'abord."

    if audio_path is None:
        return state, chatbot_history, None, "Aucun audio enregistre."

    # 1. STT
    try:
        transcript = transcribe_audio(audio_path)
    except Exception as exc:
        return state, chatbot_history, None, f"Erreur STT : {exc}"

    if not transcript.strip():
        return state, chatbot_history, None, "Aucune parole detectee. Reessayez."

    # 2. Update conversation
    state["conversation"].append({"role": "user", "content": transcript})
    chatbot_history = chatbot_history + [
        {"role": "user", "content": transcript},
    ]

    # 3. LLM
    try:
        answer = llm_respond(
            state["system_prompt"],
            state["conversation"],
            state["context_length"],
        )
    except Exception as exc:
        return state, chatbot_history, None, f"Erreur LLM : {exc}"

    state["conversation"].append({"role": "assistant", "content": answer})
    chatbot_history = chatbot_history + [
        {"role": "assistant", "content": answer},
    ]

    # 4. TTS
    try:
        audio_out_path = text_to_speech(answer, state["voice_id"])
    except Exception as exc:
        return state, chatbot_history, None, f"Erreur TTS : {exc}"

    status = f"Agent actif : {state['character_name']}"
    return state, chatbot_history, audio_out_path, status


def change_character(state: dict):
    """Reset the agent so the user can pick a new character."""
    state = {
        "active": False,
        "system_prompt": "",
        "voice_id": "",
        "conversation": [],
        "character_name": "",
        "context_length": "Moyen",
    }
    return (
        state,
        gr.update(interactive=False),
        "Choisissez un nouveau personnage et relancez l'agent.",
        [],
    )


def stop_agent(state: dict):
    """Stop the current agent session."""
    if state:
        state["active"] = False
    return (
        state,
        gr.update(interactive=False),
        "Agent arrete.",
    )


def toggle_clone_ui(enabled: bool):
    """Show or hide the voice sample upload component."""
    return gr.update(visible=enabled)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
.gradio-container {
    max-width: 960px !important;
    margin: auto !important;
}
footer { display: none !important; }
#title-block {
    text-align: center;
    padding: 0.5rem 0 0 0;
}
#title-block h1 {
    margin-bottom: 0.2rem;
}
#powered-by {
    text-align: center;
    opacity: 0.5;
    font-size: 0.85rem;
    padding-top: 0.5rem;
}
"""

# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------

with gr.Blocks(
    title="Immersive Voice Agent",
) as demo:

    # State
    agent_state = gr.State(
        value={
            "active": False,
            "system_prompt": "",
            "voice_id": "",
            "conversation": [],
            "character_name": "",
            "context_length": "Moyen",
        }
    )

    # Header
    gr.HTML(
        """
        <div id="title-block">
            <h1>Immersive Voice Agent</h1>
            <p>Incarnez n'importe quel personnage grace a l'IA vocale</p>
        </div>
        """,
    )

    # ---- Row 1 : Configuration ----
    with gr.Row():
        with gr.Column(scale=1):
            character_input = gr.Textbox(
                label="Personnage",
                placeholder="Ex : Emmanuel Macron, Yoda, Un pirate...",
                lines=1,
            )
            context_dd = gr.Dropdown(
                label="Longueur du contexte",
                choices=["Court", "Moyen", "Long"],
                value="Moyen",
            )
        with gr.Column(scale=1):
            ambiance_dd = gr.Dropdown(
                label="Ambiance (optionnel)",
                choices=list(AMBIANCE_DESCRIPTIONS.keys()),
                value="Aucune",
            )
            clone_cb = gr.Checkbox(label="Clonage de voix", value=False)
            clone_files_input = gr.File(
                label="Samples audio pour clonage (.mp3 / .wav)",
                file_types=[".mp3", ".wav"],
                file_count="multiple",
                visible=False,
            )

    # ---- Row 2 : Controls ----
    with gr.Row():
        launch_btn = gr.Button("Lancer l'Agent", variant="primary")
        change_btn = gr.Button("Changer de Personnage", variant="secondary")
        stop_btn = gr.Button("Arreter", variant="stop")

    # ---- Row 3 : Audio I/O ----
    with gr.Row():
        with gr.Column(scale=1):
            mic_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="Parlez ici",
                interactive=False,
            )
        with gr.Column(scale=1):
            audio_output = gr.Audio(
                label="Reponse",
                autoplay=True,
            )

    # ---- Row 4 : Chatbot ----
    chatbot = gr.Chatbot(
        label="Historique de conversation",
        height=400,
    )

    # ---- Row 5 : Status ----
    status_box = gr.Textbox(
        label="Statut",
        interactive=False,
        value="Choisissez un personnage et cliquez sur 'Lancer l'Agent'.",
    )

    # Footer
    gr.HTML('<p id="powered-by">Powered by GPT-4o-mini &bull; Deepgram &bull; ElevenLabs</p>')

    # ---- Events ----

    clone_cb.change(
        fn=toggle_clone_ui,
        inputs=[clone_cb],
        outputs=[clone_files_input],
    )

    launch_btn.click(
        fn=launch_agent,
        inputs=[
            character_input,
            context_dd,
            ambiance_dd,
            clone_cb,
            clone_files_input,
            agent_state,
        ],
        outputs=[
            agent_state,
            mic_input,
            status_box,
            chatbot,
        ],
    )

    mic_input.stop_recording(
        fn=process_audio,
        inputs=[mic_input, agent_state, chatbot],
        outputs=[agent_state, chatbot, audio_output, status_box],
    )

    change_btn.click(
        fn=change_character,
        inputs=[agent_state],
        outputs=[agent_state, mic_input, status_box, chatbot],
    )

    stop_btn.click(
        fn=stop_agent,
        inputs=[agent_state],
        outputs=[agent_state, mic_input, status_box],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860,theme=gr.themes.Soft(), css=CUSTOM_CSS)
