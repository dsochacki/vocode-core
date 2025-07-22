# Standard library imports
import os
import sys

from dotenv import load_dotenv

# Third-party imports
from fastapi import FastAPI
from loguru import logger
from pyngrok import ngrok

# Local application/library specific imports
from speller_agent import SpellerAgentFactory

from vocode.logging import configure_pretty_logging
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.telephony import TwilioConfig
from vocode.streaming.telephony.config_manager.redis_config_manager import RedisConfigManager
from vocode.streaming.telephony.server.base import TelephonyServer, TwilioInboundCallConfig
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig

from vocode.streaming.models.transcriber import AzureTranscriberConfig
from vocode.streaming.synthesizer.eleven_labs_websocket_synthesizer import ElevenLabsWSSynthesizer

from redis.asyncio import Redis
from redis.backoff import ExponentialBackoff, NoBackoff
from redis.retry import Retry
from redis.exceptions import ConnectionError, TimeoutError
import os


# Fix for ssl issues with Redis on fly.io
def my_initialize_redis(retries: int = 1):
    backoff = ExponentialBackoff() if retries > 1 else NoBackoff()
    retry = Retry(backoff, retries)
    return Redis(
        host=os.environ.get("REDISHOST", "localhost"),
        port=int(os.environ.get("REDISPORT", 6379)),
        username=os.environ.get("REDISUSER", None),
        password=os.environ.get("REDISPASSWORD", None),
        decode_responses=True,
        retry=retry,
        ssl=os.environ.get("REDISSSL", "false").lower() == "true",
        ssl_cert_reqs="none",
        retry_on_error=[ConnectionError, TimeoutError],
        health_check_interval=30,
    )

# if running from python, this will load the local .env
# docker-compose will load the .env file by itself
load_dotenv()
# Remove default logger to configure our own
#logger.remove()
#logger.add(sys.stderr, level="DEBUG") 

configure_pretty_logging()

app = FastAPI(docs_url=None)

config_manager = RedisConfigManager()
if os.getenv("ENVIRONMENT") == "FLY":
    config_manager.redis = my_initialize_redis()

BASE_URL = os.getenv("BASE_URL")

if not BASE_URL:
    ngrok_auth = os.environ.get("NGROK_AUTH_TOKEN")
    if ngrok_auth is not None:
        ngrok.set_auth_token(ngrok_auth)
    port = sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else 3000

    # Open a ngrok tunnel to the dev server
    BASE_URL = ngrok.connect(port).public_url.replace("https://", "")
    logger.info('ngrok tunnel "{}" -> "http://127.0.0.1:{}"'.format(BASE_URL, port))

if not BASE_URL:
    raise ValueError("BASE_URL must be set in environment if not using pyngrok")

with open("agent_prompt.txt", "r", encoding="utf-8") as f:
    prompt_preamble = f.read()

elevenlabs_config = ElevenLabsSynthesizerConfig.from_telephone_output_device(
    api_key=os.environ["ELEVEN_LABS_API_KEY"],
    voice_id="1iF3vHdwHKuVKSPDK23Z",
    model_id="eleven_multilingual_v2",
    language_code="de",
    experimental_websocket=True,
    experimental_streaming=True,
    optimize_streaming_latency=2,
    stability=0.3,
    similarity_boost=0.75,
)
#ElevenLabsSynthesizer geht beim zweiten mal nicht (IMO: True)
synthesizer = ElevenLabsWSSynthesizer(elevenlabs_config)
logger.info(f"Using synthesizer: {type(synthesizer).__name__}")

telephony_server = TelephonyServer(
    base_url=BASE_URL,
    config_manager=config_manager,
    inbound_call_configs=[
        TwilioInboundCallConfig(
            url="/inbound_call",
            agent_config=ChatGPTAgentConfig(
                initial_message=BaseMessage(text="Willkommen bei firstclass! Wie kann ich Ihnen helfen?"),
                prompt_preamble=prompt_preamble,
                generate_responses=True,
                transcriber_callback=lambda transcript: logger.debug(f"🗣️ Nutzer sagt: {transcript.text}"),
                is_interruptible=False,
                allow_agent_to_be_cut_off=False,
                send_end_of_turn=True,
            ),
            #synthesizer_config = AzureSynthesizerConfig(
            #    voice_name="de-DE-KatjaNeural",  # or "de-DE-ConradNeural"
            #    language_code="de-DE", # Language of text to be synthesized
            #    sampling_rate=8000,   
            #    audio_encoding="mulaw"
            #),
            synthesizer_config=elevenlabs_config,
            synthesizer=synthesizer,
            transcriber_config = AzureTranscriberConfig(
                sampling_rate=8000,
                audio_encoding="mulaw",
                language="de-DE",
                api_key=os.environ["AZURE_SPEECH_KEY"],
                region=os.environ["AZURE_SPEECH_REGION"],
                chunk_size=1024
            ),
            # uncomment this to use the speller agent instead
            # agent_config=SpellerAgentConfig(
            #     initial_message=BaseMessage(
            #         text="im a speller agent, say something to me and ill spell it out for you"
            #     ),
            #     generate_responses=False,
            # ),
            twilio_config=TwilioConfig(
                account_sid=os.environ["TWILIO_ACCOUNT_SID"],
                auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            ),
        )
    ],
    #agent_factory=SpellerAgentFactory(),
)

app.include_router(telephony_server.get_router())
