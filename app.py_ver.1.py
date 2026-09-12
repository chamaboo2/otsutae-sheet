import json
import re
from html import escape

import streamlit as st

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


st.set_page_config(page_title="おつたえシート", page_icon="💬", layout="centered")

st.markdown(
    """
<style>
  .stApp { background: #eef7fb; color: #172f4c; }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stToolbar"] { display:none; }
  .block-container { max-width: 410px; min-height:100vh; padding: .55rem 1.05rem 2.5rem; background:#fff; box-shadow:0 2px 24px #58768b2b; border-left:1px solid #deebf1; border-right:1px solid #deebf1; }
  h1, h2, h3 { color: #15395f; letter-spacing: .02em; }
  .hero { text-align:center; margin:0 -1.05rem; padding: 1.1rem 1.25rem .3rem; background:linear-gradient(180deg,#e7f5ff 0%,#f1faff 80%,#fff 100%); }
  .hero-icon { width:59px; height:59px; margin:auto; display:grid; place-items:center; border-radius:20px; background:white; color:#1769bb; font-size:31px; box-shadow:0 7px 21px #a8c9df55; }
  .hero h1 { margin:.65rem 0 .2rem; font-size:1.82rem; font-weight:800; letter-spacing:.05em; }
  .lead { font-size:.98rem; line-height:1.8; color:#315a75; margin-bottom:.2rem; }
  .small-note { text-align:center; color:#668096; font-size:.82rem; line-height:1.65; margin-top:.8rem; }
  .step { color:#3374a8; font-weight:700; font-size:.92rem; letter-spacing:.08em; }
  .soft-card { border-radius:17px; padding:.82rem 1rem; margin:.72rem 0 .35rem; border:1px solid #dbe9ef; box-shadow:0 3px 12px #7595a812; }
  .fact { background:#eaf6ff; } .wish { background:#fff0f2; }
  .ask { background:#ecf9f4; } .order { background:#fff8e7; }
  .cue { background:#fff; border:1px solid #d9e9f2; border-radius:18px; padding:1.25rem; font-size:1.18rem; line-height:1.85; box-shadow:0 6px 18px #7595a81c; }
  div.stButton > button { width:100%; min-height:3.15rem; border-radius:16px; font-weight:700; font-size:.98rem; }
  div.stButton > button[kind="primary"] { background:#2f80ed; border-color:#2f80ed; color:white; }
  div.stButton > button[kind="primary"]:hover { background:#246fce; border-color:#246fce; }
  div[data-testid="stTextArea"] textarea { min-height:190px; border-radius:17px; font-size:1rem; line-height:1.65; background:#fbfdff; }
  [data-testid="stAudioInput"] { border-radius:18px; }
  .status { padding:.85rem 1rem; background:#edf8f4; border-radius:16px; color:#24634f; }
  h1 { font-size:1.6rem !important; text-align:center; }
  h2 { font-size:1.35rem !important; text-align:center; }
  h3 { font-size:1.12rem !important; }
  [data-testid="stImage"] img { display:block; margin:auto; }
  @media (max-width:480px){ .block-container{max-width:100%;box-shadow:none;border:0;} }
</style>
""",
    unsafe_allow_html=True,
)


DEFAULTS = {
    "screen": "start",
    "input_mode": "text",
    "raw_text": "",
    "facts": [],
    "wishes": [],
    "questions": [],
    "order": [],
    "cue_30": "",
    "cue_15": "",
    "cue_long": "",
    "cue_mode": "30秒",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go(screen):
    st.session_state.screen = screen
    st.rerun()


def reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value.copy() if isinstance(value, list) else value
    st.rerun()


def ai_client():
    key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=key) if OpenAI and key else None


def ask_ai(prompt, audio=None):
    client = ai_client()
    if not client:
        return None
    text = prompt
    if audio is not None:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe", file=("input.wav", audio.getvalue(), "audio/wav")
        )
        text += "\n\n音声の文字起こし:\n" + transcript.text
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": "あなたは、話す直前の人の頭の中を整理する日本語編集者です。推測で事実を補わず、主語と述語を明確にし、自然な口語にしてください。出力は指定されたJSONだけにしてください。"},
            {"role": "user", "content": text},
        ],
    )
    return response.output_text


def sentences(text):
    return [s.strip(" ・\n") for s in re.split(r"[。！？!?\n]+", text) if s.strip()]


def local_organize(text):
    parts = sentences(text)
    question_words = ("ですか", "でしょうか", "知りたい", "確認", "教えて", "聞きたい", "なぜ", "いつ", "どこ")
    wish_words = ("してほしい", "したい", "お願い", "希望", "相談したい", "変えて", "対応して")
    questions = [p for p in parts if any(w in p for w in question_words)]
    wishes = [p for p in parts if any(w in p for w in wish_words) and p not in questions]
    facts = [p for p in parts if p not in questions and p not in wishes]
    if not facts and parts:
        facts = parts[:]
    order = (["最初に、起きていることを伝える"] if facts else []) + (["次に、希望を伝える"] if wishes else []) + (["最後に、確認したいことを質問する"] if questions else [])
    cue_parts = facts[:3] + wishes[:2] + questions[:2]
    cue = "。".join(cue_parts)
    if cue and not cue.endswith("。"): cue += "。"
    short = "。".join((facts[:1] + wishes[:1] + questions[:1]))
    if short and not short.endswith("。"): short += "。"
    return {"facts": facts, "wishes": wishes, "questions": questions, "order": order, "cue_30": cue, "cue_15": short, "cue_long": cue}


def organize(text, audio=None):
    prompt = f"""次の入力を整理してください。情報がない項目は空配列にし、入力にない内容は作らないでください。
JSON形式: {{"facts":["..."],"wishes":["..."],"questions":["..."],"order":["..."],"cue_30":"30秒程度で自然に話せる文","cue_15":"15秒程度の要点","cue_long":"必要情報を残した少し詳しい文"}}
文字入力:\n{text}"""
    result = ask_ai(prompt, audio)
    if result:
        try:
            return json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
        except Exception:
            st.warning("AIの応答を読み取れなかったため、簡易整理で表示しました。内容を修正してお使いください。")
    return local_organize(text)


def card_editor(title, icon, key, css_class):
    st.markdown(f'<div class="soft-card {css_class}"><b>{icon} {title}</b></div>', unsafe_allow_html=True)
    items = st.session_state[key]
    remove = None
    for i, item in enumerate(items):
        c1, c2 = st.columns([8, 1.4])
        items[i] = c1.text_area(f"{title} {i+1}", item, key=f"{key}_{i}", label_visibility="collapsed", height=82)
        if c2.button("削除", key=f"del_{key}_{i}"):
            remove = i
    if remove is not None:
        items.pop(remove)
        st.rerun()
    if st.button(f"＋ {title}を追加", key=f"add_{key}"):
        items.append("")
        st.rerun()


def build_cues():
    data = {k: st.session_state[k] for k in ("facts", "wishes", "questions", "order")}
    prompt = f"""次の確定済みメモから、読み上げ用カンペを3種類作ってください。情報を足さず、主語述語を明確にしつつ自然な話し言葉にしてください。
{json.dumps(data, ensure_ascii=False)}
JSON形式: {{"cue_30":"30秒程度","cue_15":"15秒程度","cue_long":"少し詳しく"}}"""
    result = ask_ai(prompt)
    if result:
        try:
            cues = json.loads(result.strip().removeprefix("```json").removesuffix("```").strip())
            st.session_state.update(cues)
            return
        except Exception:
            pass
    all_parts = [x for k in ("facts", "wishes", "questions") for x in st.session_state[k] if x.strip()]
    st.session_state.cue_30 = "。".join(all_parts[:6]).rstrip("。") + "。"
    st.session_state.cue_15 = "。".join(all_parts[:3]).rstrip("。") + "。"
    st.session_state.cue_long = "。".join(all_parts).rstrip("。") + "。"


screen = st.session_state.screen

if screen == "start":
    st.markdown('<div class="hero"><div class="hero-icon">💬</div><h1>おつたえシート</h1><p class="lead"><b>話す前に、伝えたいことを整理します。</b><br><br>まとまっていなくても大丈夫です。<br>まず、そのまま話してください。</p></div>', unsafe_allow_html=True)
    side1, middle, side2 = st.columns([1.15, 2, 1.15])
    middle.image("assets/hero_woman.png", use_container_width=True)
    if st.button("🎤　話して入力する", type="primary", use_container_width=True):
        st.session_state.input_mode = "voice"; go("input")
    if st.button("⌨️　文字で入力する", use_container_width=True):
        st.session_state.input_mode = "text"; go("input")
    st.markdown('<p class="small-note">上司・学校・病院・役所・家族など、いろいろな場面で使えます。</p>', unsafe_allow_html=True)

elif screen == "input":
    st.button("← 戻る", on_click=lambda: go("start"))
    st.markdown('<p class="step">STEP 1 / 4　自由に入力</p>', unsafe_allow_html=True)
    st.header("入力する")
    st.markdown('<div class="soft-card fact" style="text-align:center"><b>まとまっていなくても大丈夫。<br>まず、そのまま話してください。</b></div>', unsafe_allow_html=True)
    st.write("順番を気にせず、思いついたことをそのまま入力してください。")
    audio = None
    if st.session_state.input_mode == "voice":
        st.info("うまく話そうとしなくて大丈夫です。")
        st.markdown('<div style="width:110px;height:110px;margin:8px auto 12px;border-radius:55px;background:linear-gradient(145deg,#439af6,#186ee8);display:grid;place-items:center;color:white;font-size:48px;box-shadow:0 10px 25px #2f80ed55">🎤</div>', unsafe_allow_html=True)
        audio = st.audio_input("🎤 ここを押して話す")
        st.caption("録音後に、補足したいことがあれば下にも入力できます。")
    st.session_state.raw_text = st.text_area("伝えたいこと", st.session_state.raw_text, placeholder="例：先週から頭が痛くて、火曜日は少し気持ち悪くなりました。薬を飲むと少し楽になります。原因と検査が必要かを聞きたいです。")
    if st.button("整理してもらう", type="primary", disabled=not (st.session_state.raw_text.strip() or audio)):
        with st.spinner("内容を整理しています…"):
            data = organize(st.session_state.raw_text, audio)
            for key in ("facts", "wishes", "questions", "order", "cue_30", "cue_15", "cue_long"):
                st.session_state[key] = data.get(key, [] if key in ("facts", "wishes", "questions", "order") else "")
        go("review")

elif screen == "review":
    st.markdown('<p class="step">STEP 2・3 / 4　AIが整理 → 本人が確認</p>', unsafe_allow_html=True)
    st.header("整理した内容")
    st.write("AIの整理結果は確定ではありません。違うところは自由に直してください。")
    card_editor("事実（実際に起きたこと）", "📌", "facts", "fact")
    card_editor("希望（してほしいこと）", "🌱", "wishes", "wish")
    card_editor("確認したいこと", "❓", "questions", "ask")
    card_editor("話す順番", "🗣", "order", "order")
    if st.button("この内容でカンペを作る", type="primary"):
        with st.spinner("話しやすい言葉に整えています…"):
            build_cues()
        go("cue")
    if st.button("← 入力に戻る"):
        go("input")

elif screen == "cue":
    st.markdown('<p class="step">STEP 4 / 4　おつたえカンペ</p>', unsafe_allow_html=True)
    st.header("これを見ながら話せます")
    st.markdown('<div class="status" style="text-align:center">✨ 準備はできました。きっと、うまく伝わります。</div>', unsafe_allow_html=True)
    mode = st.session_state.cue_mode
    c1, c2, c3 = st.columns(3)
    if c1.button("もっと短く", type="primary" if mode == "15秒" else "secondary"):
        st.session_state.cue_mode = "15秒"; st.rerun()
    if c2.button("30秒版", type="primary" if mode == "30秒" else "secondary"):
        st.session_state.cue_mode = "30秒"; st.rerun()
    if c3.button("少し詳しく", type="primary" if mode == "少し詳しく" else "secondary"):
        st.session_state.cue_mode = "少し詳しく"; st.rerun()
    mode = st.session_state.cue_mode
    key = {"15秒": "cue_15", "30秒": "cue_30", "少し詳しく": "cue_long"}[mode]
    cue = st.session_state[key]
    st.markdown(f'<div class="cue"><b>おつたえカンペ</b><br><br>{escape(cue)}</div>', unsafe_allow_html=True)
    st.write("")
    st.components.v1.html(
        f"""<button onclick='speak()' style='width:100%;height:52px;border:0;border-radius:16px;background:#2f80ed;color:white;font-size:17px;font-weight:700'>🔊 音声で聞く</button>
<script>function speak(){{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance({json.dumps(cue)});u.lang='ja-JP';u.rate=.92;speechSynthesis.speak(u);}}</script>""",
        height=65,
    )
    st.caption("端末の音声読み上げ機能を使います。音が出ない場合は、端末の音量をご確認ください。")
    if st.button("内容を修正する"):
        go("review")
    if st.button("最初からやり直す"):
        reset()
