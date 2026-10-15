document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("chat-form");
    const input = document.getElementById("message-input");
    const messages = document.getElementById("messages");
    const language = document.getElementById("language");
    const newChatButton = document.getElementById("new-chat");
    const sendButton = document.getElementById("send-button");

    // Get CSRF token from HTML
    const csrfTokenElement =
        document.querySelector('meta[name="csrf-token"]');

    const csrfToken =
        csrfTokenElement
            ? csrfTokenElement.getAttribute("content")
            : "";

    if (!form || !input || !messages) {
        console.error("Nyaya AI chat elements were not found.");
        return;
    }

    function addMessage(role, text, sources = []) {

        const welcome =
            messages.querySelector(".welcome");

        if (welcome) {
            welcome.remove();
        }

        const wrapper =
            document.createElement("div");

        wrapper.className =
            role === "user"
                ? "message user-message"
                : "message assistant-message";

        const content =
            document.createElement("div");

        content.className =
            "message-content";

        const label =
            document.createElement("div");

        label.className =
            "message-label";

        label.textContent =
            role === "user"
                ? "You"
                : "Nyaya AI";

        const textElement =
            document.createElement("div");

        textElement.className =
            "message-text";

        textElement.style.whiteSpace =
            "pre-wrap";

        textElement.textContent =
            text;

        content.appendChild(label);
        content.appendChild(textElement);

        // Legal sources
        if (
            role === "assistant" &&
            sources &&
            sources.length > 0
        ) {

            const sourceBox =
                document.createElement("div");

            sourceBox.className =
                "legal-sources";

            const title =
                document.createElement("h4");

            title.textContent =
                "legal sources";

            sourceBox.appendChild(title);

            sources.forEach(source => {

                const sourceItem =
                    document.createElement("div");

                sourceItem.className =
                    "legal-source-item";

                const heading =
                    document.createElement("strong");

                heading.textContent =
                    `${source.act_name || "Act"} — Section ${
                        source.section_number || "N/A"
                    }`;

                sourceItem.appendChild(heading);

                if (source.section_title) {

                    const description =
                        document.createElement("p");

                    description.textContent =
                        source.section_title;

                    sourceItem.appendChild(
                        description
                    );
                }

                if (source.source_url) {

                    const link =
                        document.createElement("a");

                    link.href =
                        source.source_url;

                    link.target =
                        "_blank";

                    link.rel =
                        "noopener noreferrer";

                    link.textContent =
                        "Open official source";

                    sourceItem.appendChild(link);
                }

                sourceBox.appendChild(sourceItem);
            });

            content.appendChild(sourceBox);
        }

        wrapper.appendChild(content);

        messages.appendChild(wrapper);

        messages.scrollTop =
            messages.scrollHeight;
    }


    function addLoading() {

        removeLoading();

        const loading =
            document.createElement("div");

        loading.id =
            "nyaya-loading";

        loading.className =
            "message assistant-message";

        loading.innerHTML = `
            <div class="message-content">
                <div class="message-label">Nyaya AI</div>
                <div class="message-text">
                    Searching verified legal sources...
                </div>
            </div>
        `;

        messages.appendChild(loading);

        messages.scrollTop =
            messages.scrollHeight;
    }


    function removeLoading() {

        const loading =
            document.getElementById(
                "nyaya-loading"
            );

        if (loading) {
            loading.remove();
        }
    }


    async function sendQuestion(question) {

        question =
            question.trim();

        if (!question) {
            return;
        }

        if (sendButton) {

            sendButton.disabled =
                true;

            sendButton.textContent =
                "Thinking...";
        }

        addMessage(
            "user",
            question
        );

        input.value = "";

        addLoading();

        try {

            console.log(
                "Sending question:",
                question
            );

            const response =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken
                        },

                        body: JSON.stringify({

                            message:
                                question,

                            language:
                                language
                                    ? language.value
                                    : "English"
                        })
                    }
                );


            console.log(
                "Server response:",
                response.status
            );


            let data;

            try {

                data =
                    await response.json();

            } catch (error) {

                throw new Error(
                    "The server returned an invalid response."
                );
            }


            removeLoading();


            if (!response.ok) {

                console.error(
                    "Nyaya API error:",
                    data
                );

                addMessage(
                    "assistant",
                    data.error ||
                    `Nyaya AI returned error ${response.status}.`
                );

                return;
            }


            if (data.answer) {

               const answer =
    data.answer ||
    "No answer was returned.";

addMessage(
    "assistant",
    answer,
    data.sources || []
);

if (window.speakNyayaAnswer) {
    window.speakNyayaAnswer(answer);
}

            } else {

                addMessage(
                    "assistant",
                    "The server responded, but no answer was returned."
                );
            }


        } catch (error) {

            console.error(
                "Nyaya AI request failed:",
                error
            );

            removeLoading();

            addMessage(
                "assistant",
                "Could not connect to Nyaya AI. Check that the Flask server is running."
            );

        } finally {

            if (sendButton) {

                sendButton.disabled =
                    false;

                sendButton.textContent =
                    "Ask Nyaya AI →";
            }
        }
    }


    // Form submit
    form.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            const question =
                input.value.trim();

            await sendQuestion(
                question
            );
        }
    );


    // Suggestion buttons
    function connectSuggestions() {

        const suggestions =
            document.querySelectorAll(
                ".suggestion"
            );

        suggestions.forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    input.value =
                        button.textContent.trim();

                    input.focus();
                }
            );
        });
    }

    connectSuggestions();


    // New chat
    if (newChatButton) {

        newChatButton.addEventListener(
            "click",
            async () => {

                try {

                    await fetch(
                        "/api/history",
                        {
                            method: "DELETE",

                            headers: {
                                "X-CSRFToken":
                                    csrfToken
                            }
                        }
                    );

                } catch (error) {

                    console.error(
                        "Could not clear history:",
                        error
                    );
                }

                messages.innerHTML = `
                    <div class="welcome">

                        <div class="welcome-icon">
                            ⚖
                        </div>

                        <h2 class="h5">
                            What would you like help understanding?
                        </h2>

                        <p class="text-muted small">
                            Choose an example or describe your situation below.
                        </p>

                        <div class="suggestions">

                            <button class="suggestion">
                                Someone is threatening me on WhatsApp.
                            </button>

                            <button class="suggestion">
                                My employer has not paid my salary.
                            </button>

                            <button class="suggestion">
                                My landlord is refusing to return my deposit.
                            </button>

                            <button class="suggestion">
                                I am facing online harassment.
                            </button>

                        </div>

                    </div>
                `;

                connectSuggestions();

                input.value = "";

                input.focus();
            }
        );
    }


    // Enter = send
    // Shift + Enter = new line
    input.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                form.requestSubmit();
            }
        }
    );


    console.log(
        "Nyaya AI chat.js loaded successfully."
    );

});