import os
from textwrap import dedent

from griptape.config import StructureConfig, StructureGlobalDriversConfig
from griptape.drivers import MarkdownifyWebScraperDriver
from griptape.loaders import WebLoader
from griptape.rules import Rule
from griptape.structures import Pipeline
from griptape.tasks import ToolkitTask, ToolTask, CodeExecutionTask, AudioGenerationTask
from griptape.tools import RestApiClient, TaskMemoryClient, WebScraper
from griptape.utils import play_audio
from griptape.drivers import (
    AnthropicPromptDriver,
    OpenAiEmbeddingDriver,
    ElevenLabsAudioGenerationDriver,
)
from proxycurl_client import ProxycurlClient


structure = Pipeline(
    config=StructureConfig(
        global_drivers=StructureGlobalDriversConfig(
            prompt_driver=AnthropicPromptDriver(
                model="claude-3-opus-20240229",
                api_key=os.environ["ANTHROPIC_API_KEY"],
                max_tokens=1000,
            ),
            embedding_driver=OpenAiEmbeddingDriver(
                model="text-embedding-3-large",
                api_key=os.environ["OPENAI_API_KEY"],
            ),
            audio_generation_driver=ElevenLabsAudioGenerationDriver(
                api_key=os.environ["ELEVEN_LABS_API_KEY"],
                model="eleven_multilingual_v2",
                voice="Rachel",
            ),
        )
    ),
    tasks=[
        ToolkitTask(
            "Use this email address to scrape their company's website for their LinkedIn URL: {{ args[0] }}.",
            rules=[
                Rule(
                    "Output your answer as just the url, no extra words or formatting."
                ),
                Rule("If you can't find it, make a best educated guess."),
                Rule("Find the company's LinkedIn URL, not the person's."),
            ],
            id="linkedin_url",
            tools=[
                WebScraper(
                    off_prompt=True,
                    web_loader=WebLoader(
                        web_scraper_driver=MarkdownifyWebScraperDriver(timeout=1000),
                    ),
                ),
                TaskMemoryClient(off_prompt=False),
            ],
        ),
        ToolkitTask(
            "Get information on this company from their LinkedIn URL, "
            "then write a summary on the company using this information. LinkedIn URL: {{ parent_output }}.",
            id="summary",
            rules=[
                Rule(
                    "Keep your summary to under 2 sentences. Include the company's industry, size, and any other relevant information."
                ),
            ],
            tools=[
                ProxycurlClient(
                    proxycurl_api_key=os.environ["PROXYCURL_API_KEY"],
                    allowlist=["get_company"],
                    off_prompt=True,
                ),
                TaskMemoryClient(off_prompt=False),
            ],
        ),
        AudioGenerationTask(lambda task: task.parents[0].output),
        CodeExecutionTask(run_fn=lambda task: play_audio(task.parents[0].output)),
        ToolTask(
            dedent(
                """Send this info to Slack:
            Summary: {{ structure.tasks[1].output }}.
            LinkedIn: {{ structure.tasks[0].output }}
            Email: {{ args[0] }}
            """
            ),
            rules=[
                Rule(
                    'Use the keys "email", "summary" and "url" to send the email, summary and url to Slack.'
                )
            ],
            tool=RestApiClient(
                base_url=os.environ["ZAPIER_WEBHOOK_URL"],
                description="Used to send messages to Slack.",
                off_prompt=False,
            ),
        ),
    ],
)

if __name__ == "__main__":
    structure.run("collin@griptape.ai")
