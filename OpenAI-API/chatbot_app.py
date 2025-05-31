import streamlit as st
import openai
import base64
from pathlib import Path

# ---- OpenAIChatbot class----
class OpenAIChatbot:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"
        self.history = [self._get_system_prompt()]
        self.total_cost = 0.0  # In USD (misschien nog even omzetten naar EU koers)

    def _get_system_prompt(self):
        with open("system-prompts.txt", encoding="utf-8") as f:
            system_prompt = f.read()
        return {
            "role": "system",
            "content": system_prompt
        }

    def _calculate_cost(self, response):
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        input_cost = (input_tokens / 1_000_000) * 5
        output_cost = (output_tokens / 1_000_000) * 15
        total = input_cost + output_cost
        return total

    def ask(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            max_tokens=500
        )
        answer = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": answer})
        cost = self._calculate_cost(response)
        self.total_cost += cost
        return answer, cost, self.total_cost

# --- Custom CSS voor de achtergrond en layout ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #b8c7df !important; /* Donkerder blauw */
    }
    .centered-logo {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 14px;
        margin-top: 34px;  /* meer ruimte boven */
    }
    .chatblock {
        border-radius: 10px;
        padding: 18px 16px 15px 16px;
        margin-bottom: 10px;
        font-size: 1.07em;
        box-shadow: 0 2px 18px 0 rgba(50,50,93,0.08), 0 1.5px 4px 0 rgba(0,0,0,0.03);
        border: 1.5px solid #b8c7df; /* Zelfde kleur als achtergrond */
        background: #f7fafd;
    }
    .userblock {
        border-left: 6px solid #4092ff;
        background: #e6edfa;
    }
    .aiblock {
        border-left: 6px solid #7c3aed;
        background: #e8e6fa;
    }
    hr {
        margin: 9px 0 15px 0;
        border: none;
        border-top: 2px solid #b5c6e0;
    }
    .block-container {
        padding-top: 1.1rem;
        max-width: 850px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---- Sidebar voor API-key en kosten ----
st.sidebar.title("OpenAI instellingen")
api_key = st.sidebar.text_input("Vul je OpenAI API key in:", type="password")
if "costs" in st.session_state and st.session_state["costs"]:
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Totale kosten:** ${sum(st.session_state['costs']):.6f} USD")

# ---- Logo bovenaan gecentreerd, lokaal geladen ----
def show_logo():
    logo_path = "Kennisnet-logo-3744555391.png"
    logo_bytes = Path(logo_path).read_bytes()
    b64 = base64.b64encode(logo_bytes).decode()
    st.markdown(
        f"""
        <div class="centered-logo">
            <img src="data:image/png;base64,{b64}" width="180">
        </div>
        """,
        unsafe_allow_html=True
    )

show_logo()
st.markdown("<h1 style='text-align: center; margin-bottom:15px;'>Leermiddelenbeleid AI</h1>", unsafe_allow_html=True)

# ---- Chatbot & State ----
if "chatbot" not in st.session_state and api_key:
    st.session_state["chatbot"] = OpenAIChatbot(api_key=api_key)
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "costs" not in st.session_state:
    st.session_state["costs"] = []

# ---- Chatgeschiedenis tonen (prompts met lijnen) ----
def show_chat():
    for i, msg in enumerate(st.session_state["messages"]):
        if msg["role"] == "user":
            st.markdown(
                f"<div class='chatblock userblock'><b>Jij:</b> {msg['content']}</div>",
                unsafe_allow_html=True
            )
        elif msg["role"] == "assistant":
            st.markdown(
                f"<div class='chatblock aiblock'><b>Leermiddelenbeleid AI:</b> {msg['content']}</div>",
                unsafe_allow_html=True
            )
        # Duidelijke lijn tussen prompts, behalve na laatste prompt
        if i < len(st.session_state["messages"]) - 1:
            st.markdown("<hr>", unsafe_allow_html=True)

# ---- Inputveld ONDERAAN de pagina ----
show_chat()
with st.container():
    user_input = st.text_input("Stel je vraag...", key="user_input", label_visibility="hidden", placeholder="Typ hier je vraag...")
    send = st.button("Verstuur")
    if send and user_input and api_key and "chatbot" in st.session_state:
        answer, cost, total_cost = st.session_state["chatbot"].ask(user_input)
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.session_state["costs"].append(cost)
        st.rerun()
