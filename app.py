from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file
)

import requests
import io
import os
import re

from pypdf import PdfReader

from database import (
    init_database,
    create_user,
    authenticate_user,
    save_message,
    get_messages,
    clear_messages,
    save_memory,
    get_memories,
    clear_memories,
    save_document,
    get_latest_document,
    clear_documents
)


app = Flask(__name__)

app.secret_key = "ai-chatbot-secret-key-change-this"

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODEL = "llama3.2:latest"

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

init_database()


# --------------------------------------------------
# LOGIN REQUIRED
# --------------------------------------------------

def login_required():
    return "user_id" in session


# --------------------------------------------------
# LANGUAGE DETECTION
# --------------------------------------------------

def detect_language(text):

    tamil_chars = re.findall(r"[\u0B80-\u0BFF]", text)

    english_chars = re.findall(
        r"[A-Za-z]",
        text
    )

    if tamil_chars and english_chars:
        return "Tanglish"

    if tamil_chars:
        return "Tamil"

    return "English"


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return redirect(url_for("chat"))


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return render_template(
                "register.html",
                error="Username and password are required."
            )

        if len(password) < 4:
            return render_template(
                "register.html",
                error="Password must contain at least 4 characters."
            )

        success = create_user(username, password)

        if not success:
            return render_template(
                "register.html",
                error="Username already exists."
            )

        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(username, password)

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("chat"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# --------------------------------------------------
# CHAT PAGE
# --------------------------------------------------

@app.route("/chat")
def chat():

    if not login_required():
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        username=session.get("username")
    )


# --------------------------------------------------
# GET CHAT HISTORY
# --------------------------------------------------

@app.route("/api/history")
def history():

    if not login_required():
        return jsonify({"error": "Login required"}), 401

    rows = get_messages(
        session["user_id"],
        50
    )

    messages = []

    for row in rows:

        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    return jsonify({
        "messages": messages
    })


# --------------------------------------------------
# CHAT WITH OLLAMA
# --------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():

    if not login_required():
        return jsonify({
            "error": "Please login first."
        }), 401

    data = request.get_json()

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "error": "Please enter a message."
        }), 400

    user_id = session["user_id"]

    # Save user message
    save_message(
        user_id,
        "user",
        user_message
    )

    # Get previous conversation
    history_rows = get_messages(
        user_id,
        20
    )

    # Get memory
    memories = get_memories(user_id)

    memory_text = ""

    if memories:

        memory_text = "\n".join(
            f"- {row['memory']}"
            for row in memories
        )

    language = detect_language(user_message)

    system_prompt = f"""
You are a helpful AI assistant.

CURRENT USER MESSAGE LANGUAGE:
{language}

IMPORTANT LANGUAGE RULES:

If the current user message is English:
Answer in English.

If the current user message is Tamil:
Answer in Tamil.

If the current user message is Tanglish:
Answer naturally in Tanglish.

Do NOT force Tamil when the current user message is English.

Do NOT let previous conversation language override the
current user's language.

Be helpful, clear and natural.

User memory:
{memory_text}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for row in history_rows:

        messages.append({
            "role": row["role"],
            "content": row["content"]
        })

    # PDF context
    document = get_latest_document(user_id)

    if document:

        pdf_context = document["content"]

        # Keep request size reasonable
        pdf_context = pdf_context[:12000]

        messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    "The user uploaded a PDF. "
                    "Use the following PDF content when "
                    "answering questions related to it:\n\n"
                    + pdf_context
                )
            }
        )

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

        result = response.json()

        assistant_message = result["message"]["content"]

    except requests.exceptions.ConnectionError:

        return jsonify({
            "error": (
                "Cannot connect to Ollama. "
                "Please make sure Ollama is running."
            )
        }), 500

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    # Save AI answer
    save_message(
        user_id,
        "assistant",
        assistant_message
    )

    # Simple memory detection
    lower_message = user_message.lower()

    memory_words = [
        "my name is",
        "i am",
        "i'm",
        "remember that",
        "remember my",
        "my favorite",
        "i like",
        "i love"
    ]

    if any(
        word in lower_message
        for word in memory_words
    ):

        save_memory(
            user_id,
            user_message
        )

    return jsonify({
        "answer": assistant_message
    })


# --------------------------------------------------
# CLEAR CHAT
# --------------------------------------------------

@app.route("/api/clear-chat", methods=["POST"])
def clear_chat():

    if not login_required():
        return jsonify({
            "error": "Login required"
        }), 401

    clear_messages(
        session["user_id"]
    )

    return jsonify({
        "success": True
    })


# --------------------------------------------------
# MEMORY
# --------------------------------------------------

@app.route("/api/memory")
def memory():

    if not login_required():
        return jsonify({
            "error": "Login required"
        }), 401

    rows = get_memories(
        session["user_id"]
    )

    memories = []

    for row in rows:

        memories.append({
            "id": row["id"],
            "memory": row["memory"]
        })

    return jsonify({
        "memories": memories
    })


# --------------------------------------------------
# CLEAR MEMORY
# --------------------------------------------------

@app.route("/api/clear-memory", methods=["POST"])
def clear_memory():

    if not login_required():
        return jsonify({
            "error": "Login required"
        }), 401

    clear_memories(
        session["user_id"]
    )

    return jsonify({
        "success": True
    })


# --------------------------------------------------
# PDF UPLOAD
# --------------------------------------------------

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():

    if not login_required():
        return jsonify({
            "error": "Login required"
        }), 401

    if "file" not in request.files:
        return jsonify({
            "error": "No file selected."
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "error": "No file selected."
        }), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files are supported."
        }), 400

    try:

        reader = PdfReader(file)

        text = ""

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        if not text.strip():
            return jsonify({
                "error": "Could not extract text from this PDF."
            }), 400

        filename = file.filename

        save_document(
            session["user_id"],
            filename,
            text
        )

        file_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(file_path)

        return jsonify({
            "success": True,
            "filename": filename
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# --------------------------------------------------
# EXPORT CHAT
# --------------------------------------------------

@app.route("/api/export")
def export_chat():

    if not login_required():
        return jsonify({
            "error": "Login required"
        }), 401

    rows = get_messages(
        session["user_id"],
        1000
    )

    text = ""

    for row in rows:

        role = "You" if row["role"] == "user" else "AI"

        text += f"{role}: {row['content']}\n\n"

    return send_file(
        io.BytesIO(text.encode("utf-8")),
        mimetype="text/plain",
        as_attachment=True,
        download_name="chat_history.txt"
    )


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 55)
    print("🤖 AI CHATBOT SERVER")
    print("=" * 55)
    print(f"Model: {MODEL}")
    print(f"Ollama: {OLLAMA_URL}")
    print("Database: chat_memory.db")
    print("Login: Enabled")
    print("Memory: Enabled")
    print("PDF Q&A: Enabled")
    print("Voice: Browser based")
    print("Text-to-Speech: Browser based")
    print("Export: Enabled")
    print()
    print("🌐 http://127.0.0.1:5000")
    print("=" * 55)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )