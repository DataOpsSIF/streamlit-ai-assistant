import streamlit as st
import asyncio
from langgraph_sdk import get_client
import nest_asyncio
from langsmith import Client

LANGGRAPH_URL = st.secrets["LANGGRAPH_CLOUD_ENDPOINT"]
API_KEY = st.secrets["API_KEY"]


# Initialize the langsmith Client for feedback submissions
feedback_client = Client(
    api_url="https://eu.api.smith.langchain.com/",
    api_key=API_KEY
)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()


client = get_client(url=LANGGRAPH_URL, api_key=API_KEY)

APP_TITLE = "AI Explorer"
APP_ICON = "✨"

st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        menu_items={},
)

# Hide the Streamlit top status bar
st.markdown(
    """
    <style>
    [data-testid="stStatusWidget"] { visibility: hidden; height: 0%; position: fixed; }
    </style>
    """,
    unsafe_allow_html=True
)

if st.get_option("client.toolbarMode") != "minimal":
    st.set_option("client.toolbarMode", "minimal")
    st.rerun()

# Initialize session state for messages
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Initialize session state for json document
if 'solutions_json' not in st.session_state:
    st.session_state['solutions_json'] = None

if 'assistant' not in st.session_state or 'thread' not in st.session_state:
    async def init_assistant():
        client = get_client(url=LANGGRAPH_URL, api_key=API_KEY)
        assistants = await client.assistants.search(metadata={"created_by": "system"})
        assistant = assistants[0]
        thread = await client.threads.create()
        st.session_state['assistant'] = assistant
        st.session_state['thread'] = thread
        st.session_state['agent_client'] = client  # Store AgentClient in session

    asyncio.run(init_assistant())


async def handle_feedback() -> None:
    """Draws a feedback widget and records feedback from the user."""

    # Ensure last feedback state is tracked to avoid duplicates
    if "last_feedback" not in st.session_state:
        st.session_state.last_feedback = (None, None)

    # Get the run_id of the last assistant message
    latest_run_id = st.session_state['messages'][-1].get("run_id")

    # Display feedback widget
    feedback = st.feedback("stars", key=latest_run_id)

    # Check if feedback is new, and if so, send it to LangSmith
    if feedback is not None and (latest_run_id, feedback) != st.session_state.last_feedback:
        # Normalize feedback (an index) to a score between 0 and 1
        normalized_score = (feedback + 1) / 5.0

        # Create feedback on LangSmith for the run_id
        feedback_client.create_feedback(
            run_id=latest_run_id,
            key="human-feedback-stars",
            score=normalized_score,
            comment="In-line human feedback"
        )

        # Update session state to avoid duplicate feedback submissions
        st.session_state.last_feedback = (latest_run_id, feedback)
        st.toast("Feedback recorded", icon=":material/reviews:")


# Config options
with st.sidebar:
    st.image("logo.svg", use_column_width=True)
    st.markdown("---")
    st.header(f"{APP_ICON} {APP_TITLE}")
    ""
    "Advanced RAG Assistant for the Solution Explorer, powered by LangChain & Typesense"
    st.markdown("Discover the latest climate tech solutions with our new assistant designed to recommend the best clean & profitable solutions tailored for your needs. Visit the [Solution Explorer](https://solarimpulse.com/solutions-explorer) to discover more solutions.")
    ""
    ""
    ""

    # Language options and translations
    languages = {
        "🇬🇧": ("en",
               "Hello! I'm your AI assistant specialized in climate-tech solutions. How can I assist you today in discovering innovative and sustainable technologies?"),
        "🇫🇷": ("fr",
               "Bonjour ! Je suis votre assistant IA spécialisé dans les solutions de technologie climatique. Comment puis-je vous aider aujourd'hui à découvrir des technologies innovantes et durables ?"),
        "🇮🇹": ("it",
               "Ciao! Sono il tuo assistente AI specializzato in soluzioni tecnologiche per il clima. Come posso aiutarti oggi a scoprire tecnologie innovative e sostenibili?"),
        "🇩🇪": ("de",
               "Hallo! Ich bin Ihr KI-Assistent, spezialisiert auf Klimatechnologien. Wie kann ich Ihnen heute helfen, innovative und nachhaltige Technologien zu entdecken?")
    }

    with st.popover(":material/language: Language", use_container_width=True):
        # Language selection
        selected_flag = st.radio("Language to use", options=list(languages.keys()))
        selected_language, welcome_message = languages[selected_flag]

    with st.popover(":material/policy: Terms & Privacy", use_container_width=True):
        st.write(
            "By messaging AI Assistant, you agree to our [Terms](https://solutions-explorer.gitbook.io/resources/additional-resources/terms-and-conditions) and have read our [Privacy Policy](https://solarimpulse.com/pdf/Solar_Impulse_Foundation_Website_Privacy_Policy_10.2017.pdf) Prompts, responses and feedback in this app are anonymously recorded and saved to LangSmith for product evaluation and improvement purposes only. More info about the general terms and conditions and privacy policy are available [Here](https://app.gitbook.com/o/Op3VdU0fhQCgGVhwv4jx/s/KGAN4ko2qLFQDMJgRgce/additional-resources/terms-and-conditions)"
        )

    st.link_button("Solutions Explorer Resources 🌍", "https://solutions-explorer.gitbook.io/resources", use_container_width=True)


    st.markdown("---")

    st.markdown(
        f"Thread ID: **{st.session_state.thread['thread_id']}**",
        help=f"Set URL query parameter ?thread_id={st.session_state.thread['thread_id']} to continue this conversation",
    )
    # Show current language with flag
    st.markdown(f"**Current language selected:** {selected_flag}")

    "[View the source code](https://github.com/DataOpsSIF/streamlit-ai-assistant)"
    st.caption(
        "Made with :material/favorite: by [Solar Impulse Foundation](https://solarimpulse.com/) in Lausanne 🇨🇭"
    )
    ""
    ""
    ""
    ""
    # Add the "Clear Conversation" button at the very bottom
    if st.button("🗑️  Clear Conversation"):
        st.session_state['messages'] = []

        # Reset the thread to clear server-side history
        async def reset_thread():
            client = get_client(url=LANGGRAPH_URL)
            thread = await client.threads.create()
            st.session_state['thread'] = thread

        asyncio.run(reset_thread())

        st.rerun()

# Display Chat Messages
if st.session_state['solutions_json']:
    chat_container = st.container(height=screen_height, border=False)
    for message in st.session_state['messages']:
        chat_message = chat_container.chat_message("assistant" if message["role"] == "assistant" else "user")
        chat_message.markdown(message["content"])
else:
    for message in st.session_state['messages']:
        with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
            st.markdown(message["content"])
if not st.session_state['messages']:
    with st.chat_message("assistant"):
        st.markdown(welcome_message)

# Display feedback after assistant's response
if st.session_state['messages'] and st.session_state['messages'][-1]["role"] == "assistant":
    asyncio.run(handle_feedback())  # Ensure this is only called after assistant's response

# User input area using st.chat_input
if prompt := st.chat_input("What climate-tech solutions do you want to discover today?"):
    # Add user message to session state
    st.session_state['messages'].append({"role": "user", "content": prompt})
    if st.session_state['solutions_json']:
        new_chat_message = chat_container.chat_message("user")
        new_chat_message.markdown(prompt)
    else:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Assistant's response
    with st.chat_message("assistant"):
        # Placeholder for the assistant's response
        if st.session_state['solutions_json']:
           response_placeholder = chat_container.empty()
        else:
            response_placeholder = st.empty()

        # Show a spinner while waiting for the assistant's response
        with st.spinner('Thinking about clean & efficient solutions...'):

            async def get_assistant_response():
                assistant = st.session_state['assistant']
                thread = st.session_state['thread']
                run_id = None  # Variable to store the first 'run_id'

                # Only send the latest user message
                input_data = {"messages": [{'role': 'human', 'content': prompt}]}
                response_text = ''
                solutions_json = ""
                try:
                    langgraph_node = ""
                    # Use stream_mode="updates" since "tokens" is not supported
                    async for chunk in client.runs.stream(
                            thread_id=thread["thread_id"],
                            assistant_id=assistant["assistant_id"],
                            input=input_data,
                            stream_mode=["messages"],
                            config={"configurable":{"locality": selected_language}}
                    ):
                        chunk_data = chunk.data

                        # Check if this is the initial chunk and capture the 'run_id'
                        if run_id is None:
                            run_id = chunk_data.get("run_id")
                            print(f"Initial run_id captured: {run_id}")

                        elif langgraph_node == "agent" and isinstance(chunk_data, list):
                            if len(chunk_data) > 0:
                                chunk_data = chunk_data[-1]
                                if chunk_data.get("content", "") != "" and chunk_data.get('type', "tool") != "tool":
                                    response_text = chunk_data.get("content", "")
                                    response_placeholder.markdown(response_text)
                        elif not isinstance(chunk_data, list):
                            first_key = next(iter(chunk_data))
                            langgraph_node = chunk_data[first_key]["metadata"].get("langgraph_node", "")
                            print("langgraph_node:", langgraph_node)
                        elif langgraph_node == "tools":
                            if chunk_data[-1].get("artifact", None):
                                solutions_json = chunk_data[-1].get("artifact", None)

                except Exception as e:
                    response_text = f"An error occurred: {e}"
                    response_placeholder.markdown(response_text)
                    solutions_json = None

                # Once done, add the response to messages
                st.session_state['messages'].append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "run_id": run_id
                    }
                )
                if solutions_json:
                    if "localhost" in LANGGRAPH_URL:
                        st.session_state['solutions_json'] = solutions_json

            # Run the asynchronous function synchronously
            asyncio.run(get_assistant_response())

    # Rerun the app to display the new messages
    st.rerun()
