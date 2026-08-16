/* =========================================================
   AI CHATBOT - SCRIPT
========================================================= */


/* =========================================================
   ELEMENTS
========================================================= */

const chatBox = document.getElementById("chatMessages");

const messageInput =
    document.getElementById("messageInput");

const sendBtn =
    document.getElementById("sendBtn");

const voiceBtn =
    document.getElementById("voiceBtn");

const clearChatBtn =
    document.getElementById("clearChatBtn");

const exportBtn =
    document.getElementById("exportBtn");

const darkBtn =
    document.getElementById("darkModeBtn");

const clearMemoryBtn =
    document.getElementById("clearMemoryBtn");

const memoryList =
    document.getElementById("memoryList");

const pdfInput =
    document.getElementById("pdfInput");

const pdfStatus =
    document.getElementById("pdfStatus");


/* =========================================================
   ADD MESSAGE
========================================================= */

function addMessage(role, text) {

    if (!chatBox) {
        console.error("Chat box not found.");
        return;
    }

    const div = document.createElement("div");

    div.classList.add("message");

    if (role === "user") {

        div.classList.add("user-message");

        div.innerHTML = `
            <div class="message-name">
                You
            </div>

            <div class="message-text"></div>
        `;

    } else {

        div.classList.add("ai-message");

        div.innerHTML = `
            <div class="message-name">
                AI
                <button
                    class="speak-button"
                    title="Click to hear"
                    type="button"
                >
                    🔊
                </button>
            </div>

            <div class="message-text"></div>
        `;

        const speakButton =
            div.querySelector(".speak-button");

        if (speakButton) {

            speakButton.addEventListener(
                "click",
                function(event) {

                    event.stopPropagation();

                    speakText(text);

                }
            );

        }
    }

    const textElement =
        div.querySelector(".message-text");

    if (textElement) {
        textElement.textContent = text;
    }

    chatBox.appendChild(div);

    chatBox.scrollTop =
        chatBox.scrollHeight;
}


/* =========================================================
   LOAD CHAT HISTORY
========================================================= */

async function loadHistory() {

    if (!chatBox) {
        return;
    }

    try {

        const response =
            await fetch("/api/history");

        const data =
            await response.json();

        if (data.messages) {

            chatBox.innerHTML = "";

            for (const message of data.messages) {

                addMessage(
                    message.role,
                    message.content
                );

            }

        }

    } catch (error) {

        console.error(
            "History error:",
            error
        );

    }
}


/* =========================================================
   SEND MESSAGE
========================================================= */

async function sendMessage() {

    if (!messageInput || !sendBtn) {
        return;
    }

    const message =
        messageInput.value.trim();

    if (!message) {
        return;
    }


    /* Add user message */

    addMessage(
        "user",
        message
    );


    /* Clear input */

    messageInput.value = "";

    messageInput.style.height = "50px";


    /* Disable button */

    sendBtn.disabled = true;


    /* Loading message */

    const loading =
        document.createElement("div");

    loading.className =
        "message ai-message";

    loading.innerHTML = `
        <div class="message-name">
            AI
        </div>

        <div class="message-text">
            Thinking...
        </div>
    `;

    chatBox.appendChild(loading);

    chatBox.scrollTop =
        chatBox.scrollHeight;


    try {

        const response =
            await fetch("/api/chat", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    message: message
                })

            });


        const data =
            await response.json();


        /* Remove loading */

        loading.remove();


        /* Error */

        if (data.error) {

            addMessage(
                "assistant",
                "❌ " + data.error
            );

        }

        /* Success */

        else {

            addMessage(
                "assistant",
                data.answer
            );

            loadMemory();

        }


    } catch (error) {

        loading.remove();

        addMessage(
            "assistant",
            "❌ Connection error. Please check Ollama and Flask server."
        );

        console.error(
            "Chat error:",
            error
        );

    }


    sendBtn.disabled = false;

    messageInput.focus();
}


/* =========================================================
   SEND BUTTON
========================================================= */

if (sendBtn) {

    sendBtn.addEventListener(
        "click",
        sendMessage
    );

}


/* =========================================================
   ENTER KEY
========================================================= */

if (messageInput) {

    messageInput.addEventListener(
        "keydown",
        function(event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );


    /* Auto resize */

    messageInput.addEventListener(
        "input",
        function() {

            this.style.height = "50px";

            this.style.height =
                Math.min(
                    this.scrollHeight,
                    120
                ) + "px";

        }
    );

}


/* =========================================================
   LOAD MEMORY
========================================================= */

async function loadMemory() {

    if (!memoryList) {
        return;
    }

    try {

        const response =
            await fetch("/api/memory");

        const data =
            await response.json();

        memoryList.innerHTML = "";


        if (
            !data.memories ||
            data.memories.length === 0
        ) {

            memoryList.innerHTML = `
                <div class="no-memory">
                    No memories yet.
                </div>
            `;

            return;
        }


        for (
            const item of data.memories
        ) {

            const div =
                document.createElement("div");

            div.className =
                "memory-item";

            div.textContent =
                item.memory;

            memoryList.appendChild(div);

        }


    } catch (error) {

        console.error(
            "Memory error:",
            error
        );

    }
}


/* =========================================================
   CLEAR CHAT
========================================================= */

if (clearChatBtn) {

    clearChatBtn.addEventListener(
        "click",
        async function() {

            const confirmed =
                confirm(
                    "Clear the entire chat?"
                );

            if (!confirmed) {
                return;
            }


            try {

                const response =
                    await fetch(
                        "/api/clear-chat",
                        {
                            method: "POST"
                        }
                    );


                if (response.ok) {

                    chatBox.innerHTML = "";

                    addMessage(
                        "assistant",
                        "Chat cleared. 👋"
                    );

                }

            } catch (error) {

                console.error(
                    "Clear chat error:",
                    error
                );

            }

        }
    );

}


/* =========================================================
   CLEAR MEMORY
========================================================= */

if (clearMemoryBtn) {

    clearMemoryBtn.addEventListener(
        "click",
        async function() {

            const confirmed =
                confirm(
                    "Clear all saved memories?"
                );

            if (!confirmed) {
                return;
            }


            try {

                await fetch(
                    "/api/clear-memory",
                    {
                        method: "POST"
                    }
                );

                loadMemory();

            } catch (error) {

                console.error(
                    "Clear memory error:",
                    error
                );

            }

        }
    );

}


/* =========================================================
   EXPORT
========================================================= */

if (exportBtn) {

    exportBtn.addEventListener(
        "click",
        function() {

            window.location.href =
                "/api/export";

        }
    );

}


/* =========================================================
   DARK MODE
========================================================= */

if (darkBtn) {

    darkBtn.addEventListener(
        "click",
        function() {

            document.body.classList.toggle(
                "dark-mode"
            );


            if (
                document.body.classList.contains(
                    "dark-mode"
                )
            ) {

                localStorage.setItem(
                    "darkMode",
                    "true"
                );

                darkBtn.textContent =
                    "☀️";

            }

            else {

                localStorage.setItem(
                    "darkMode",
                    "false"
                );

                darkBtn.textContent =
                    "🌙";

            }

        }
    );

}


/* =========================================================
   RESTORE DARK MODE
========================================================= */

if (
    localStorage.getItem("darkMode")
    === "true"
) {

    document.body.classList.add(
        "dark-mode"
    );

    if (darkBtn) {
        darkBtn.textContent = "☀️";
    }

}


/* =========================================================
   VOICE INPUT
========================================================= */

let recognition = null;

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (SpeechRecognition && voiceBtn) {

    recognition =
        new SpeechRecognition();

    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.lang = "en-IN";


    recognition.onstart =
        function() {

            voiceBtn.textContent =
                "🔴";

        };


    recognition.onend =
        function() {

            voiceBtn.textContent =
                "🎤";

        };


    recognition.onresult =
        function(event) {

            const text =
                event.results[0][0].transcript;

            messageInput.value =
                text;

            messageInput.focus();

        };


    recognition.onerror =
        function(event) {

            console.error(
                "Voice error:",
                event.error
            );

            voiceBtn.textContent =
                "🎤";

        };


    voiceBtn.addEventListener(
        "click",
        function() {

            try {

                recognition.start();

            } catch (error) {

                console.error(
                    "Voice start error:",
                    error
                );

            }

        }
    );

}

else if (voiceBtn) {

    voiceBtn.addEventListener(
        "click",
        function() {

            alert(
                "Voice input is not supported by this browser."
            );

        }
    );

}


/* =========================================================
   TEXT TO SPEECH
========================================================= */

function speakText(text) {

    if (
        !("speechSynthesis" in window)
    ) {

        alert(
            "Text-to-speech is not supported."
        );

        return;
    }


    speechSynthesis.cancel();


    const speech =
        new SpeechSynthesisUtterance(text);


    speech.lang = "en-IN";

    speech.rate = 1;

    speech.pitch = 1;


    speechSynthesis.speak(
        speech
    );

}


/* =========================================================
   PDF UPLOAD
========================================================= */

if (pdfInput) {

    pdfInput.addEventListener(
        "change",
        async function() {

            const file =
                pdfInput.files[0];

            if (!file) {
                return;
            }


            if (
                !file.name
                    .toLowerCase()
                    .endsWith(".pdf")
            ) {

                pdfStatus.textContent =
                    "❌ Please select a PDF file.";

                return;
            }


            pdfStatus.textContent =
                "Uploading...";


            const formData =
                new FormData();


            formData.append(
                "file",
                file
            );


            try {

                const response =
                    await fetch(
                        "/api/upload-pdf",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const data =
                    await response.json();


                if (data.error) {

                    pdfStatus.textContent =
                        "❌ " + data.error;

                }

                else {

                    pdfStatus.textContent =
                        "✅ " + data.filename;

                }


            } catch (error) {

                pdfStatus.textContent =
                    "❌ Upload failed.";

                console.error(
                    "PDF upload error:",
                    error
                );

            }

        }
    );

}


/* =========================================================
   START
========================================================= */

loadHistory();

loadMemory();