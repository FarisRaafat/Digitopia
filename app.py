import os
import io
import zipfile
import tempfile
from typing import Tuple

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
try:
    import networkx as nx  # type: ignore
except Exception:
    nx = None  # type: ignore

from semgrep_runner import run_semgrep
from chatbot import dataframe_to_context, has_env_gemini_key, recommend_secure_fixes_rest
from auth import init_database, show_auth_forms, is_logged_in, get_current_user, logout_user
from models import init_models, insert_scan_with_findings, query_scan_history, list_projects
from report import build_pdf_report


st.set_page_config(page_title="Semgrep Security Assistant", layout="wide")

# Custom CSS for enhanced styling
st.markdown("""
<style>
    /* Global styles */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Hero section animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .hero-section {
        animation: fadeInUp 1s ease-out;
    }
    
    /* Feature cards hover effects */
    .feature-card {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    /* Step numbers animation */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .step-number {
        animation: pulse 2s infinite;
    }
    
    /* Gradient text effect */
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Custom button styles */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize database
init_database()

# Initialize models
init_models()

st.title("Semgrep Security Assistant")

# Landing page for unauthenticated users
if "user" not in st.session_state or st.session_state["user"] is None:
    # Hero Section
    st.markdown("""
    <div class="hero-section" style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 3rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">🔒 Semgrep Security Assistant</h1>
        <p style="color: white; font-size: 1.2rem; margin-bottom: 0; opacity: 0.9;">AI-Powered Code Security Analysis & Remediation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Section
    st.markdown("### 🚀 Why Choose Our Security Assistant?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card" style="padding: 1.5rem; border-radius: 10px; background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); text-align: center;">
            <h3 style="color: #333; margin-bottom: 1rem;">🔍 Deep Analysis</h3>
            <p style="color: #555; margin: 0;">Advanced static analysis using Semgrep's powerful rule engine to detect security vulnerabilities</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card" style="padding: 1.5rem; border-radius: 10px; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); text-align: center;">
            <h3 style="color: #333; margin-bottom: 1rem;">🤖 AI Guidance</h3>
            <p style="color: #555; margin: 0;">Get intelligent remediation advice powered by Google's Gemini AI for secure coding practices</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card" style="padding: 1.5rem; border-radius: 10px; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); text-align: center;">
            <h3 style="color: #333; margin-bottom: 1rem;">📊 Visual Insights</h3>
            <p style="color: #555; margin: 0;">Beautiful charts, dashboards, and PDF reports to track your security posture over time</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # How It Works Section
    st.markdown("### ⚡ How It Works")
    
    steps_col1, steps_col2, steps_col3, steps_col4 = st.columns(4)
    
    with steps_col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div class="step-number" style="background: #4CAF50; color: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;">1</div>
            <h4 style="color: #333;">Upload Code</h4>
            <p style="color: #666; font-size: 0.9rem;">Upload single files or entire project zips</p>
        </div>
        """, unsafe_allow_html=True)
    
    with steps_col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div class="step-number" style="background: #2196F3; color: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;">2</div>
            <h4 style="color: #333;">Run Analysis</h4>
            <p style="color: #666; font-size: 0.9rem;">Semgrep scans for security vulnerabilities</p>
        </div>
        """, unsafe_allow_html=True)
    
    with steps_col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div class="step-number" style="background: #FF9800; color: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;">3</div>
            <h4 style="color: #333;">Get Insights</h4>
            <p style="color: #666; font-size: 0.9rem;">View findings with visual charts</p>
        </div>
        """, unsafe_allow_html=True)
    
    with steps_col4:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div class="step-number" style="background: #9C27B0; color: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;">4</div>
            <h4 style="color: #333;">AI Recommendations</h4>
            <p style="color: #666; font-size: 0.9rem;">Get AI-powered fix suggestions</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Call to Action Section
    st.markdown("### 🎯 Ready to Secure Your Code?")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("""
        <div style="padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; text-align: center;">
            <h3 style="color: white; margin-bottom: 1rem;">🆕 New User?</h3>
            <p style="color: white; opacity: 0.9; margin-bottom: 1.5rem;">Create your account to start analyzing code and building your security dashboard</p>
            <div style="background: white; color: #667eea; padding: 0.5rem 1rem; border-radius: 25px; display: inline-block; font-weight: bold;">Sign Up Now</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("""
        <div style="padding: 2rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 15px; text-align: center;">
            <h3 style="color: white; margin-bottom: 1rem;">👋 Returning User?</h3>
            <p style="color: white; opacity: 0.9; margin-bottom: 1.5rem;">Welcome back! Access your dashboard and continue your security journey</p>
            <div style="background: white; color: #f5576c; padding: 0.5rem 1rem; border-radius: 25px; display: inline-block; font-weight: bold;">Login Here</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Stats Section
    st.markdown("### 📈 Trusted by Developers Worldwide")
    
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.metric("🔍", "1000+", "Scans Completed")
    
    with stats_col2:
        st.metric("🛡️", "500+", "Vulnerabilities Found")
    
    with stats_col3:
        st.metric("🤖", "95%", "AI Accuracy")
    
    with stats_col4:
        st.metric("⭐", "4.9/5", "User Rating")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px; margin-top: 2rem;">
        <p style="color: #666; margin: 0;">🔒 Powered by Semgrep & Google Gemini AI | Built with ❤️ for Secure Coding</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

# Check authentication
if not is_logged_in():
    st.info("Please log in to access the Semgrep Security Assistant")
    show_auth_forms()
    st.stop()

# User is logged in - show main interface
current_user = get_current_user()
st.success(f"Welcome, {current_user}!")

# Logout button
if st.button("Logout", type="secondary"):
    logout_user()
    st.rerun()

st.divider()

# Initialize session state containers
if "results_df" not in st.session_state:
    st.session_state["results_df"] = None
if "raw_json" not in st.session_state:
    st.session_state["raw_json"] = None
if "chat_answer" not in st.session_state:
    st.session_state["chat_answer"] = ""
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Secure Recommendations Chatbot"

uploaded = st.file_uploader("Upload a single file or a .zip project", type=None)
run_clicked = st.button("Run Analysis", disabled=uploaded is None)

results_df = st.session_state.get("results_df")
raw_json = st.session_state.get("raw_json")

if run_clicked and uploaded is not None:
    if uploaded.name.lower().endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmpdir:
            zpath = os.path.join(tmpdir, uploaded.name)
            with open(zpath, "wb") as f:
                f.write(uploaded.getbuffer())
            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(tmpdir)
            target = tmpdir
            with st.spinner("Running Semgrep on project..."):
                results_df, raw_json = run_semgrep(target)
                st.session_state["results_df"] = results_df
                st.session_state["raw_json"] = raw_json
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, uploaded.name)
            with open(fpath, "wb") as f:
                f.write(uploaded.getbuffer())
            with st.spinner("Running Semgrep on file..."):
                results_df, raw_json = run_semgrep(fpath)
                st.session_state["results_df"] = results_df
                st.session_state["raw_json"] = raw_json

    # After st.session_state["results_df"] and raw_json are set, record scan
    try:
        current_user = get_current_user()
        project_name = st.text_input("Project name", value="Default Project")
        # Store temporarily; will insert after analysis completes
        st.session_state["_pending_project_name"] = project_name
    except Exception:
        pass


if st.session_state.get("results_df") is not None:
    tab1, tab2, tab3 = st.tabs(["Findings", "Secure Recommendations Chatbot", "Dashboard"])

    with tab1:
        st.subheader("Semgrep Findings Table")
        st.dataframe(st.session_state["results_df"], width='stretch')
        # Persist to DB button
        if st.button("Save scan to history"):
            try:
                user = get_current_user()
                project_name = st.session_state.get("_pending_project_name") or "Default Project"
                target_label = uploaded.name if uploaded else "uploaded"
                scan_id, score, count = insert_scan_with_findings(user, project_name, target_label, st.session_state["results_df"], st.session_state.get("chat_answer"))
                st.success(f"Saved scan #{scan_id} (score {score}, findings {count})")
            except Exception as e:
                st.error(f"Failed to save scan: {e}")

        st.subheader("Findings per Rule")
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        rule_counts = st.session_state["results_df"]["rule"].value_counts()
        rule_counts.plot(kind="bar", ax=ax1)
        ax1.set_xlabel("Rule")
        ax1.set_ylabel("Count")
        ax1.set_title("Number of findings per rule")
        st.pyplot(fig1)

        st.subheader("Severity Distribution")
        fig2, ax2 = plt.subplots(figsize=(5, 5))
        sev_counts = st.session_state["results_df"]["severity"].value_counts()
        ax2.pie(sev_counts.values, labels=sev_counts.index, autopct="%1.1f%%", startangle=90)
        ax2.axis("equal")
        st.pyplot(fig2)

    with tab2:
        st.subheader("Ask for secure coding recommendations")
        user_q = st.text_area("Your question", value="Provide secure coding recommendations for these findings.")
        
        # Fixed max_rows value (no slider)
        max_rows = 100

        # Option to use a free, browser-side model via Puter.js to avoid quotas
        use_browser_llm = st.checkbox("Use browser-based free model (no API key)", value=False, help="Uses Puter.js in your browser to call a free model.")

        if use_browser_llm:
            st.info("Falling back to free Puter.js model (no key needed)")
            context_csv = dataframe_to_context(st.session_state["results_df"], max_rows=max_rows)

            html_code = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <script src=\"https://js.puter.com/v2/\"></script>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 0; }}
      .wrap {{ padding: 8px 12px; }}
      textarea {{ width: 100%; height: 120px; box-sizing: border-box; }}
      button {{ margin-top: 8px; padding: 8px 12px; }}
      pre {{ white-space: pre-wrap; word-wrap: break-word; background: #1118270d; padding: 8px; border-radius: 6px; }}
      .small {{ color: #6b7280; font-size: 12px; }}
    </style>
  </head>
  <body>
    <div class=\"wrap\">
      <div class=\"small\">Model: google/gemini-2.0-flash-lite-001 (free)</div>
      <div class=\"small\">Context rows: {max_rows}</div>
      <textarea id=\"q\">{user_q}</textarea>
      <button id=\"go\" disabled>Loading model…</button>
      <pre id=\"out\"></pre>
      <details>
        <summary>Show findings CSV context</summary>
        <pre>{context_csv}</pre>
      </details>
    </div>
    <script>
      const go = document.getElementById('go');
      const q = document.getElementById('q');
      const out = document.getElementById('out');
      function isPuterReady() {{ return typeof window !== 'undefined' && window.puter && puter.ai && typeof puter.ai.chat === 'function'; }}
      async function waitForPuterReady(timeoutMs = 15000) {{
        const start = Date.now();
        while (!isPuterReady()) {{
          if (Date.now() - start > timeoutMs) {{ throw new Error('Puter.js failed to load. Please check your network and try again.'); }}
          await new Promise(r => setTimeout(r, 300));
        }}
      }}
      async function run() {{
        out.textContent = 'Generating recommendations...';
        try {{
          const base = "You are a senior application security engineer. Given static analysis findings in CSV, provide precise, language-appropriate secure coding recommendations with concise examples when useful. Be practical.\n\nFindings (CSV):\n";
          const ctx = `{context_csv}`;
          const suffix = "\n\nUser question: ";
          const prompt = base + ctx + suffix + q.value;
          const chat = await puter.ai.chat({{ model: 'google/gemini-2.0-flash-lite-001' }});
          const response = await chat.send(prompt);
          out.textContent = response.message?.content || JSON.stringify(response, null, 2);
        }} catch (e) {{
          out.textContent = 'Error: ' + (e?.message || e);
        }}
      }}
      (async () => {{ try {{ await waitForPuterReady(); go.disabled = false; go.textContent = 'Generate Recommendations'; }} catch (e) {{ go.disabled = true; go.textContent = 'Failed to load model'; out.textContent = 'Error: ' + (e?.message || e); }} }})();
      go.addEventListener('click', (ev) => {{ ev.preventDefault(); run(); }});
    </script>
  </body>
 </html>
            """
            st.components.v1.html(html_code, height=550)
        else:
            # Use REST Gemini if key exists, else auto-fallback banner and embed Puter.js
            if has_env_gemini_key():
                st.success("Using Gemini API with provided key")
                model_choice = st.selectbox(
                    "Gemini model",
                    options=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
                    index=0,
                    help="If one model fails due to access, try another."
                )
                gen_clicked = st.button("Generate Recommendations")
                if gen_clicked:
                    # Don't switch tabs - stay in chatbot tab
                    try:
                        with st.spinner("Consulting Gemini (REST)..."):
                            answer = recommend_secure_fixes_rest(
                                st.session_state["results_df"],
                                user_q,
                                model_choice,
                                max_rows=max_rows,
                            )
                        st.session_state["chat_answer"] = answer
                    except Exception as e:
                        st.error(f"Failed to generate recommendations: {e}")
                if st.session_state.get("chat_answer"):
                    st.markdown(st.session_state["chat_answer"])
            else:
                st.info("Falling back to free Puter.js model (no key needed)")
                context_csv = dataframe_to_context(st.session_state["results_df"], max_rows=max_rows)
                html_code = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <script src=\"https://js.puter.com/v2/\"></script>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 0; }}
      .wrap {{ padding: 8px 12px; }}
      textarea {{ width: 100%; height: 120px; box-sizing: border-box; }}
      button {{ margin-top: 8px; padding: 8px 12px; }}
      pre {{ white-space: pre-wrap; word-wrap: break-word; background: #1118270d; padding: 8px; border-radius: 6px; }}
      .small {{ color: #6b7280; font-size: 12px; }}
    </style>
  </head>
  <body>
    <div class=\"wrap\">
      <div class=\"small\">Model: google/gemini-2.0-flash-lite-001 (free)</div>
      <div class=\"small\">Context rows: {max_rows}</div>
      <textarea id=\"q\">{user_q}</textarea>
      <button id=\"go\" disabled>Loading model…</button>
      <pre id=\"out\"></pre>
      <details>
        <summary>Show findings CSV context</summary>
        <pre>{context_csv}</pre>
      </details>
    </div>
    <script>
      const go = document.getElementById('go');
      const q = document.getElementById('q');
      const out = document.getElementById('out');
      function isPuterReady() {{ return typeof window !== 'undefined' && window.puter && puter.ai && typeof puter.ai.chat === 'function'; }}
      async function waitForPuterReady(timeoutMs = 15000) {{
        const start = Date.now();
        while (!isPuterReady()) {{
          if (Date.now() - start > timeoutMs) {{ throw new Error('Puter.js failed to load. Please check your network and try again.'); }}
          await new Promise(r => setTimeout(r, 300));
        }}
      }}
      async function run() {{
        out.textContent = 'Generating recommendations...';
        try {{
          const base = "You are a senior application security engineer. Given static analysis findings in CSV, provide precise, language-appropriate secure coding recommendations with concise examples when useful. Be practical.\n\nFindings (CSV):\n";
          const ctx = `{context_csv}`;
          const suffix = "\n\nUser question: ";
          const prompt = base + ctx + suffix + q.value;
          const chat = await puter.ai.chat({{ model: 'google/gemini-2.0-flash-lite-001' }});
          const response = await chat.send(prompt);
          out.textContent = response.message?.content || JSON.stringify(response, null, 2);
        }} catch (e) {{
          out.textContent = 'Error: ' + (e?.message || e);
        }}
      }}
      (async () => {{ try {{ await waitForPuterReady(); go.disabled = false; go.textContent = 'Generate Recommendations'; }} catch (e) {{ go.disabled = true; go.textContent = 'Failed to load model'; out.textContent = 'Error: ' + (e?.message || e); }} }})();
      go.addEventListener('click', (ev) => {{ ev.preventDefault(); run(); }});
    </script>
  </body>
 </html>
                """
                st.components.v1.html(html_code, height=550)

    with tab3:
        st.subheader("User Dashboard")
        user = get_current_user()
        col1, col2, col3 = st.columns(3)
        with col1:
            projects = [""] + list_projects(user)
            project_filter = st.selectbox("Project", options=projects, index=0)
        with col2:
            severity_filter = st.selectbox("Severity", options=["", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], index=0)
        with col3:
            date_range = st.date_input("Date Range", value=None)
        start_dt = None
        end_dt = None
        if isinstance(date_range, tuple) and len(date_range) == 2 and date_range[0] and date_range[1]:
            start_dt = pd.Timestamp(date_range[0]).to_pydatetime()
            end_dt = pd.Timestamp(date_range[1]).to_pydatetime()

        df_hist = query_scan_history(user, project_filter or None, severity_filter or None, start_dt, end_dt)
        st.dataframe(df_hist, width='stretch')

        # Details per finding
        if not df_hist.empty:
            st.subheader("Finding Details")
            for idx, row in df_hist.head(100).iterrows():
                label = f"Scan #{int(row['scan_id'])} - {row['file']}:{int(row['line']) if pd.notna(row['line']) else '?'} - {row['rule']}"
                with st.expander(label):
                    st.write(f"Message: {row['message']}")
                    st.write(f"Severity: {row['severity']}")
                    st.write(f"OWASP: {row['owasp']}")
                    # Simple explain mode
                    st.markdown("**Why this is dangerous:**")
                    st.write("This issue may enable attackers to compromise confidentiality, integrity, or availability depending on context. Validate inputs, use parameterized APIs, and follow least privilege.")
                    st.markdown("**Remediation tips:**")
                    st.write("Apply secure coding patterns for the affected language and framework. Prefer safe APIs, validate user input, and sanitize outputs where applicable.")

