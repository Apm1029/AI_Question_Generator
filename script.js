let testData = null;
let currentQuestion = 0;
let userAnswers = [];


async function generateTest() {

    const text =
        document.getElementById("studyText").value.trim();

    const difficulty =
        document.getElementById("difficulty").value;

    const questionCount =
        Number(document.getElementById("questionCount").value);

    const questionType =
        document.getElementById("questionType").value;

    const button =
        document.getElementById("generateBtn");


    if (!text) {
        alert("Please enter some study material first.");
        return;
    }


    button.disabled = true;
    button.textContent = "⏳ Generating...";


    try {

        const response = await fetch(
            "https://YOUR-RENDER-SERVICE.onrender.com/generate",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    text: text,
                    difficulty: difficulty,
                    question_count: questionCount,
                    question_type: questionType
                })
            }
        );


        const data = await response.json();


        if (!response.ok || data.error) {
            throw new Error(
                data.details || data.error || "Server error"
            );
        }


        if (
            !data.questions ||
            !Array.isArray(data.questions) ||
            data.questions.length === 0
        ) {
            throw new Error(
                "The AI did not generate any questions."
            );
        }


        testData = data;

        currentQuestion = 0;

        userAnswers =
            new Array(testData.questions.length).fill(null);


        document.getElementById("testTitle").textContent =
            testData.title || "Generated Test";


        document
            .getElementById("testSection")
            .classList.remove("hidden");


        document
            .getElementById("resultSection")
            .classList.add("hidden");


        renderQuestion();


        document
            .getElementById("testSection")
            .scrollIntoView({
                behavior: "smooth"
            });


    } catch (error) {

        console.error(error);

        alert(
            "Could not generate the test.\n\n" +
            error.message
        );

    } finally {

        button.disabled = false;

        button.textContent =
            "✨ Generate Test";
    }
}



function renderQuestion() {

    if (!testData || !testData.questions) {
        return;
    }


    const question =
        testData.questions[currentQuestion];


    document.getElementById("questionCounter").textContent =
        `${currentQuestion + 1} / ${testData.questions.length}`;


    const container =
        document.getElementById("questionContainer");


    let optionsHTML = "";


    question.options.forEach((option, index) => {

        const letter =
            String.fromCharCode(65 + index);


        const checked =
            userAnswers[currentQuestion] === option
                ? "checked"
                : "";


        optionsHTML += `
            <label class="option">

                <input
                    type="radio"
                    name="answer"
                    value="${escapeHTML(option)}"
                    ${checked}
                    onchange="saveAnswer(this.value)"
                >

                <strong>${letter}.</strong>

                ${escapeHTML(option)}

            </label>
        `;
    });


    container.innerHTML = `

        <div class="questionCard">

            <div class="questionNumber">
                QUESTION ${currentQuestion + 1}
            </div>

            <div class="questionText">
                ${escapeHTML(question.question)}
            </div>

            <div>
                ${optionsHTML}
            </div>

        </div>
    `;


    const previousButton =
        document.getElementById("previousBtn");

    const nextButton =
        document.getElementById("nextBtn");

    const submitButton =
        document.getElementById("submitBtn");


    previousButton.disabled =
        currentQuestion === 0;


    if (
        currentQuestion ===
        testData.questions.length - 1
    ) {

        nextButton.classList.add("hidden");

        submitButton.classList.remove("hidden");

    } else {

        nextButton.classList.remove("hidden");

        submitButton.classList.add("hidden");
    }
}



function saveAnswer(answer) {

    userAnswers[currentQuestion] = answer;
}



function nextQuestion() {

    if (
        currentQuestion <
        testData.questions.length - 1
    ) {

        currentQuestion++;

        renderQuestion();
    }
}



function previousQuestion() {

    if (currentQuestion > 0) {

        currentQuestion--;

        renderQuestion();
    }
}



function submitTest() {

    if (!testData) {
        return;
    }


    let correct = 0;


    testData.questions.forEach(
        (question, index) => {

            if (
                userAnswers[index] ===
                question.answer
            ) {
                correct++;
            }
        }
    );


    const total =
        testData.questions.length;


    const percentage =
        Math.round((correct / total) * 100);


    document.getElementById("score").textContent =
        `${percentage}%`;


    document.getElementById("scoreText").textContent =
        `You got ${correct} out of ${total} questions correct.`;


    document
        .getElementById("resultSection")
        .classList.remove("hidden");


    document
        .getElementById("testSection")
        .classList.add("hidden");


    document
        .getElementById("resultSection")
        .scrollIntoView({
            behavior: "smooth"
        });
}



function restartTest() {

    document
        .getElementById("resultSection")
        .classList.add("hidden");


    document
        .getElementById("testSection")
        .classList.add("hidden");


    document
        .getElementById("studyText")
        .focus();
}



function escapeHTML(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
const studyText = document.getElementById("studyText");
const characterCounter = document.getElementById("characterCounter");

studyText.addEventListener("input", function () {

    const length = studyText.value.length;

    characterCounter.textContent =
        `${length.toLocaleString()} / 60,000 characters`;

});