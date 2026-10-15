
document.addEventListener("DOMContentLoaded", () => {
    const micButton = document.getElementById("mic-button");
    const micLabel = document.getElementById("mic-label");
    const input = document.getElementById("message-input");
    const voiceStatus = document.getElementById("voice-status");
    const stopButton = document.getElementById("stop-speaking");

    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    let recognition = null;
    let isListening = false;

    function setStatus(message) {
        if (voiceStatus) {
            voiceStatus.textContent = message;
        }
    }

    // Voice input: English only
    if (SpeechRecognition && micButton) {
        recognition = new SpeechRecognition();
        recognition.lang = "en-IN";
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        micButton.addEventListener("click", () => {
            if (isListening) {
                recognition.stop();
                return;
            }

            try {
                recognition.start();
            } catch (error) {
                console.error(error);
                setStatus("Could not start microphone. Please try again.");
            }
        });

        recognition.onstart = () => {
            isListening = true;
            micButton.classList.add("recording");

            if (micLabel) {
                micLabel.textContent = "Listening...";
            }

            setStatus("Listening... speak your question.");
        };

        recognition.onresult = event => {
            const transcript =
                event.results[event.resultIndex]?.[0]?.transcript?.trim();

            if (transcript && input) {
                input.value = transcript;
                input.focus();
                setStatus("Voice captured. Press Ask Nyaya AI.");
            }
        };

        recognition.onerror = event => {
            setStatus(
                event.error === "not-allowed"
                    ? "Please allow microphone access in Chrome."
                    : "Microphone error: " + event.error
            );
        };

        recognition.onend = () => {
            isListening = false;
            micButton.classList.remove("recording");

            if (micLabel) {
                micLabel.textContent = "Speak";
            }
        };
    } else if (micButton) {
        micButton.disabled = true;
        setStatus("Voice input is not supported in this browser.");
    }

    // Voice output: English only
    function speakAnswer(text) {
        if (!("speechSynthesis" in window)) {
            setStatus("Speech output is not supported in this browser.");
            return;
        }

        if (typeof text !== "string" || !text.trim()) {
            return;
        }

        window.speechSynthesis.cancel();

        const cleanText = text
            .replace(/```[\s\S]*?```/g, " Code omitted. ")
            .replace(/https?:\/\/\S+/g, " source link ")
            .replace(/[*#_`~]/g, "")
            .replace(/\n+/g, ". ")
            .trim();

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = "en-IN";
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 1;

        const voices = window.speechSynthesis.getVoices();
        const englishVoice =
            voices.find(voice => voice.lang === "en-IN") ||
            voices.find(voice => voice.lang.startsWith("en-")) ||
            voices.find(voice => voice.lang.startsWith("en"));

        if (englishVoice) {
            utterance.voice = englishVoice;
            utterance.lang = englishVoice.lang;
        }

        utterance.onstart = () => {
            setStatus("Nyaya AI is speaking...");
        };

        utterance.onend = () => {
            setStatus("Spoken answer completed.");
        };

        utterance.onerror = event => {
            if (
                event.error === "canceled" ||
                event.error === "interrupted"
            ) {
                return;
            }

            console.error("Speech error:", event.error);
            setStatus("Could not play the spoken answer.");
        };

        window.speechSynthesis.speak(utterance);
    }

    // Used by chat.js
    window.speakNyayaAnswer = speakAnswer;

    if (stopButton) {
        stopButton.addEventListener("click", () => {
            window.speechSynthesis.cancel();
            setStatus("Speech stopped.");
        });
    }

    console.log("Nyaya AI English voice system loaded.");
});
