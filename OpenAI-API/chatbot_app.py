import streamlit as st
import openai
import base64
from pathlib import Path
import os
import json
from datetime import datetime

# ============ SETTINGS ============
CHATDIR = "chats"
if not os.path.exists(CHATDIR):
    os.makedirs(CHATDIR)

# ============ CHATBOT CLASS ============
class OpenAIChatbot:
    def __init__(self, api_key, history=None):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"
        self.history = history or [self._get_system_prompt()]
        self.total_cost = 0.0
        self.kennisbank = self._load_beleidsvoorbeelden("Beleidsvoorbeelden")

        # Gekozen hyperparameters
        self.temperature = 1.0
        self.top_p = 1.0
        self.frequency_penalty = 0.0
        self.presence_penalty = 1.0

    def _get_system_prompt(self):
        with open("system-prompts.txt", encoding="utf-8") as f:
            system_prompt = f.read()
        return {"role": "system", "content": system_prompt}

    def _load_beleidsvoorbeelden(self, folder_path):
        kennisbank = {}
        if not os.path.isdir(folder_path):
            print(f"Let op: map '{folder_path}' bestaat niet!")
            return kennisbank
        for fname in os.listdir(folder_path):
            if fname.endswith(".txt"):
                with open(os.path.join(folder_path, fname), encoding="utf-8") as f:
                    kennisbank[fname] = f.read()
        print(f"{len(kennisbank)} beleidsvoorbeelden geladen!")
        return kennisbank

    def ask(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": answer})
        cost = self._calculate_cost(response)
        self.total_cost += cost
        return answer, cost, self.total_cost

    def _calculate_cost(self, response):
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        input_cost = (input_tokens / 1_000_000) * 5
        output_cost = (output_tokens / 1_000_000) * 15
        total = input_cost + output_cost
        return total

# ============ MEMORY MANAGEMENT ============
def get_chat_ids_and_titles():
    chat_files = [f for f in os.listdir(CHATDIR) if f.endswith(".json")]
    chat_ids = []
    chat_titles = []
    for f in sorted(chat_files):
        chat_id = f[:-5]
        try:
            with open(os.path.join(CHATDIR, f), encoding="utf-8") as fp:
                history = json.load(fp)
            first_user = next((m["content"] for m in history if m["role"] == "user"), None)
            if first_user:
                title = first_user.strip().split("\n")[0][:40]
                title = (title + "...") if len(title) >= 40 else title
            else:
                title = "Onbenoemd gesprek"
        except Exception:
            title = "Onbenoemd gesprek"
        chat_ids.append(chat_id)
        chat_titles.append(f"{title} ({chat_id[-6:]})")
    return chat_ids, chat_titles

def load_history(chat_id):
    with open(os.path.join(CHATDIR, f"{chat_id}.json"), encoding="utf-8") as f:
        return json.load(f)

def save_history(chat_id, history):
    with open(os.path.join(CHATDIR, f"{chat_id}.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def new_chat_id():
    return datetime.now().strftime("chat-%Y%m%d-%H%M%S")

# ============ STREAMLIT LAYOUT ============
st.markdown(
    """
    <style>
    .stApp { background-color: #b8c7df !important; }
    .centered-logo { display: flex; justify-content: center; align-items: center; margin-bottom: 14px; margin-top: 34px; }
    .chatblock { border-radius: 10px; padding: 18px 16px 15px 16px; margin-bottom: 10px; font-size: 1.07em;
        box-shadow: 0 2px 18px 0 rgba(50,50,93,0.08), 0 1.5px 4px 0 rgba(0,0,0,0.03); border: 1.5px solid #b8c7df; background: #f7fafd; }
    .userblock { border-left: 6px solid #4092ff; background: #e6edfa; }
    .aiblock { border-left: 6px solid #7c3aed; background: #e8e6fa; }
    hr { margin: 9px 0 15px 0; border: none; border-top: 2px solid #b5c6e0; }
    .block-container { padding-top: 1.1rem; max-width: 850px !important; }
    .stTextInput > div > input { font-size: 18px; padding: 12px 10px; border-radius: 7px;}
    </style>
    """,
    unsafe_allow_html=True
)

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

# ---- Sidebar ----
st.sidebar.title("OpenAI instellingen")
api_key = st.sidebar.text_input("Vul je OpenAI API key in:", type="password")
st.sidebar.markdown("---")
chat_ids, chat_titles = get_chat_ids_and_titles()

# --- Nieuw: Selectbox met bovenaan "Nieuwe chat"
options = ["Nieuwe chat"] + chat_titles
chosen_idx = st.sidebar.selectbox("Kies een gesprek", range(len(options)), format_func=lambda i: options[i])
chosen = None if chosen_idx == 0 else chat_ids[chosen_idx - 1]

if "costs" in st.session_state and st.session_state["costs"]:
    st.sidebar.write(f"**Totale kosten:** ${sum(st.session_state['costs']):.6f} USD")

if st.sidebar.button("Start nieuw gesprek"):
    st.session_state["messages"] = []
    st.session_state["costs"] = []
    st.session_state["active_chat_id"] = None
    st.session_state["chatbot"] = None
    st.rerun()

# Start nieuwe chat of laad een bestaande chat
if "active_chat_id" not in st.session_state:
    st.session_state["active_chat_id"] = None

# Alleen als gebruiker een chat kiest, laad deze. Anders, nieuwe chat
if chosen is not None and api_key:
    if st.session_state.get("active_chat_id") != chosen:
        history = load_history(chosen)
        st.session_state["messages"] = history
        st.session_state["costs"] = []
        st.session_state["active_chat_id"] = chosen
else:
    # Als er nog geen chat actief is, maak er één aan bij eerste input
    if "messages" not in st.session_state or not st.session_state["messages"]:
        st.session_state["messages"] = []
    if "costs" not in st.session_state:
        st.session_state["costs"] = []
    if "active_chat_id" not in st.session_state or st.session_state["active_chat_id"] is None:
        st.session_state["active_chat_id"] = None

# Chatbot instance
if "chatbot" not in st.session_state or st.session_state["chatbot"] is None:
    if api_key:
        st.session_state["chatbot"] = OpenAIChatbot(api_key=api_key, history=st.session_state.get("messages", []))
elif (
    "chatbot" in st.session_state
    and st.session_state["chatbot"] is not None
    and st.session_state["chatbot"].api_key != api_key
):
    st.session_state["chatbot"] = OpenAIChatbot(api_key=api_key, history=st.session_state.get("messages", []))

# Chatgeschiedenis tonen
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
        if i < len(st.session_state["messages"]) - 1:
            st.markdown("<hr>", unsafe_allow_html=True)
show_chat()

# Inputveld met ENTER/submit, legen van de invoer na verzenden
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Typ je bericht en druk op Enter...",
        key="user_input",
        value="",
        label_visibility="hidden",
        placeholder="Typ hier je vraag..."
    )
    submitted = st.form_submit_button("Verstuur")

    # FIX: garandeer chatbot instance
    if (
        "chatbot" not in st.session_state
        or st.session_state["chatbot"] is None
    ):
        if api_key:
            st.session_state["chatbot"] = OpenAIChatbot(api_key=api_key, history=st.session_state.get("messages", []))

    if (
        submitted
        and user_input
        and api_key
        and "chatbot" in st.session_state
        and st.session_state["chatbot"] is not None
    ):
        answer, cost, total_cost = st.session_state["chatbot"].ask(user_input)
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.session_state["costs"].append(cost)

        # **Alleen een nieuwe chat_id aanmaken als er nog GEEN is**
        if not st.session_state.get("active_chat_id"):
            chat_id = new_chat_id()
            st.session_state["active_chat_id"] = chat_id
        else:
            chat_id = st.session_state["active_chat_id"]
        save_history(chat_id, st.session_state["messages"])
        st.rerun()
