from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import requests
import os
import json
import re
import time


# ============================================================
# SETUP
# ============================================================

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GEMINI API KEYS
# ============================================================

API1_KEY = os.getenv("GEMINI_API_KEY_1")
API2_KEY = os.getenv("GEMINI_API_KEY_2")
API3_KEY = os.getenv("GEMINI_API_KEY_3")


# ============================================================
# LIMITS
# ============================================================

MAX_CHARACTERS = 60000

API1_LIMIT = 20000
API2_LIMIT = 40000
API3_LIMIT = 60000


# ============================================================
# MODELS
# ============================================================

API1_MODEL = "gemini-2.5-flash"
API2_MODEL = "gemini-2.5-flash"
API3_MODEL = "gemini-2.5-flash"


# ============================================================
# REQUEST MODEL
# ============================================================

class TestRequest(BaseModel):

    text: str
    difficulty: str
    question_count: int
    question_type: str


# ============================================================
# GET API KEY
# ============================================================

def get_api_key(level):

    if level == 1:
        return API1_KEY

    if level == 2:
        return API2_KEY

    if level == 3:
        return API3_KEY

    return None


# ============================================================
# GEMINI REQUEST
# ============================================================

def ask_gemini(api_key, model, prompt):

    if not api_key:

        raise ValueError(
            "Gemini API key for this level was not found in .env."
        )


    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )


    payload = {

        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],

        "generationConfig": {

            "responseMimeType": "application/json",

            "thinkingConfig": {
                "thinkingBudget": 0
            },

            "maxOutputTokens": 4096
        }
    }


    response = requests.post(

        url,

        json=payload,

        timeout=90
    )


    return response


# ============================================================
# SPLIT MATERIAL
# ============================================================

def split_material(text, chunk_size=20000):

    chunks = []

    start = 0


    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )


        # ----------------------------------------------------
        # Try paragraph break
        # ----------------------------------------------------

        if end < len(text):

            paragraph_break = text.rfind(
                "\n",
                start,
                end
            )

            if paragraph_break > start + 10000:

                end = paragraph_break


        # ----------------------------------------------------
        # Try sentence break
        # ----------------------------------------------------

        if end < len(text):

            sentence_positions = [

                text.rfind(".", start, end),

                text.rfind("?", start, end),

                text.rfind("!", start, end)

            ]


            sentence_break = max(
                sentence_positions
            )


            if sentence_break > start + 10000:

                end = sentence_break + 1


        chunk = text[start:end].strip()


        if chunk:

            chunks.append(chunk)


        start = end


    return chunks


# ============================================================
# CREATE PROMPT
# ============================================================

def create_prompt(
    material,
    difficulty,
    question_count,
    question_type
):

    if question_type == "MCQ":

        structure = """
{
    "questions": [
        {
            "question": "Question text",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": "Option A",
            "explanation": "Short explanation"
        }
    ]
}
"""

    else:

        structure = """
{
    "questions": [
        {
            "question": "Question text",
            "options": [
                "True",
                "False"
            ],
            "answer": "True",
            "explanation": "Short explanation"
        }
    ]
}
"""


    return f"""
You are an expert school question generator.

Your task is to create a test ONLY from the study material provided below.

STUDY MATERIAL:
{material}

DIFFICULTY:
{difficulty}

NUMBER OF QUESTIONS:
{question_count}

QUESTION TYPE:
{question_type}


STRICT RULES:

1. Use ONLY information contained in the supplied study material.

2. Do not introduce unrelated facts.

3. Match the requested difficulty.

4. For MCQ questions, provide exactly 4 options.

5. For True/False questions, provide exactly:
   "True"
   "False"

6. Every question must have exactly one correct answer.

7. The answer must exactly match one of the provided options.

8. Give a short and useful explanation.

9. Avoid duplicate questions.

10. Questions must be suitable for school students.

11. Do not make questions that require information outside the supplied material.

12. Return ONLY valid JSON.

13. Do NOT use Markdown.

14. Do NOT write anything before the JSON.

15. Do NOT write anything after the JSON.


Return exactly this structure:

{structure}
"""


# ============================================================
# EXTRACT GEMINI TEXT
# ============================================================

def extract_gemini_text(data):

    try:

        candidates = data.get(
            "candidates",
            []
        )


        if not candidates:

            raise ValueError(
                "Gemini returned no candidates."
            )


        candidate = candidates[0]


        content = candidate.get(
            "content",
            {}
        )


        parts = content.get(
            "parts",
            []
        )


        # ----------------------------------------------------
        # Look for normal final text
        # ----------------------------------------------------

        for part in parts:

            # Ignore thinking parts
            if part.get("thought") is True:
                continue


            if "text" in part:

                text = part["text"]


                if text and text.strip():

                    return text.strip()


        # ----------------------------------------------------
        # No final text found
        # ----------------------------------------------------

        raise ValueError(
            "Gemini did not return a final text response."
        )


    except Exception as e:

        raise ValueError(
            f"Could not read Gemini response: {str(e)}"
        )


# ============================================================
# CLEAN JSON TEXT
# ============================================================

def clean_json_text(text):

    text = text.strip()


    # Remove Markdown code fences

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"^```\s*",
        "",
        text
    )


    text = re.sub(
        r"\s*```$",
        "",
        text
    )


    text = text.strip()


    return text


# ============================================================
# GENERATE FROM ONE CHUNK
# ============================================================

def generate_from_chunk(
    material,
    difficulty,
    question_count,
    question_type,
    api_key,
    model
):

    prompt = create_prompt(

        material,

        difficulty,

        question_count,

        question_type
    )


    response = ask_gemini(

        api_key,

        model,

        prompt
    )


    # --------------------------------------------------------
    # API ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        return None, response


    # --------------------------------------------------------
    # READ RESPONSE JSON
    # --------------------------------------------------------

    try:

        data = response.json()

    except Exception:

        return None, response


    # --------------------------------------------------------
    # EXTRACT FINAL TEXT
    # --------------------------------------------------------

    text = extract_gemini_text(data)


    # --------------------------------------------------------
    # CLEAN JSON
    # --------------------------------------------------------

    text = clean_json_text(text)


    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    result = json.loads(text)


    return result, response


# ============================================================
# VALIDATE QUESTIONS
# ============================================================

def validate_questions(
    questions,
    question_type
):

    valid_questions = []


    for question in questions:

        if not isinstance(question, dict):

            continue


        question_text = question.get(
            "question"
        )


        options = question.get(
            "options"
        )


        answer = question.get(
            "answer"
        )


        explanation = question.get(
            "explanation"
        )


        if not question_text:

            continue


        if not isinstance(options, list):

            continue


        if question_type == "MCQ":

            if len(options) != 4:

                continue

        else:

            options = [
                "True",
                "False"
            ]


        if answer not in options:

            continue


        if not explanation:

            explanation = ""


        valid_questions.append({

            "question": str(
                question_text
            ),

            "options": [
                str(option)
                for option in options
            ],

            "answer": str(
                answer
            ),

            "explanation": str(
                explanation
            )

        })


    return valid_questions


# ============================================================
# MAIN GENERATOR
# ============================================================

@app.post("/generate")
def generate_test(request: TestRequest):

    # --------------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------------

    text = request.text.strip()


    # --------------------------------------------------------
    # EMPTY MATERIAL
    # --------------------------------------------------------

    if not text:

        return {

            "error":
                "Please provide study material."
        }


    # --------------------------------------------------------
    # CHARACTER LIMIT
    # --------------------------------------------------------

    if len(text) > MAX_CHARACTERS:

        return {

            "error":
                "Study material is too long.",

            "details":
                "Maximum allowed study material is 60,000 characters."
        }


    # --------------------------------------------------------
    # QUESTION COUNT
    # --------------------------------------------------------

    if request.question_count < 1:

        return {

            "error":
                "Question count must be at least 1."
        }


    if request.question_count > 20:

        return {

            "error":
                "Maximum 20 questions are allowed."
        }


    # --------------------------------------------------------
    # QUESTION TYPE
    # --------------------------------------------------------

    if request.question_type not in [
        "MCQ",
        "True/False"
    ]:

        return {

            "error":
                "Invalid question type."
        }


    # --------------------------------------------------------
    # CHOOSE API LEVEL
    # --------------------------------------------------------

    material_length = len(text)


    if material_length <= API1_LIMIT:

        level = 1

        chunks = [text]

        model = API1_MODEL


    elif material_length <= API2_LIMIT:

        level = 2

        chunks = split_material(
            text,
            20000
        )

        model = API2_MODEL


    else:

        level = 3

        chunks = split_material(
            text,
            20000
        )

        model = API3_MODEL


    # --------------------------------------------------------
    # GET CORRECT API KEY
    # --------------------------------------------------------

    api_key = get_api_key(level)


    if not api_key:

        return {

            "error":
                f"Gemini API key {level} is not configured.",

            "details":
                f"Please add GEMINI_API_KEY_{level} to your .env file."
        }


    # --------------------------------------------------------
    # SERVER LOG
    # --------------------------------------------------------

    print()

    print("=" * 60)

    print("NEW TEST REQUEST")

    print("=" * 60)

    print(
        f"Characters: {material_length}"
    )

    print(
        f"API Level: {level}"
    )

    print(
        f"Model: {model}"
    )

    print(
        f"Chunks: {len(chunks)}"
    )

    print(
        f"Questions requested: "
        f"{request.question_count}"
    )

    print(
        f"Question type: "
        f"{request.question_type}"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # DISTRIBUTE QUESTIONS
    # --------------------------------------------------------

    total_questions = request.question_count

    chunk_count = len(chunks)


    base_questions = (
        total_questions // chunk_count
    )


    extra_questions = (
        total_questions % chunk_count
    )


    all_questions = []


    # --------------------------------------------------------
    # GENERATE QUESTIONS
    # --------------------------------------------------------

    for index, chunk in enumerate(chunks):

        questions_for_chunk = base_questions


        if index < extra_questions:

            questions_for_chunk += 1


        if questions_for_chunk <= 0:

            continue


        print(
            f"Generating chunk "
            f"{index + 1}/{chunk_count}..."
        )


        try:

            result, response = generate_from_chunk(

                chunk,

                request.difficulty,

                questions_for_chunk,

                request.question_type,

                api_key,

                model
            )


            # ------------------------------------------------
            # 503 FALLBACK
            # ------------------------------------------------

            if (
                result is None
                and response.status_code == 503
            ):

                print(
                    f"{model} temporarily unavailable."
                )


                backup_model = (
                    "gemini-2.5-flash-lite"
                )


                print(
                    f"Trying backup model: "
                    f"{backup_model}"
                )


                result, response = (
                    generate_from_chunk(

                        chunk,

                        request.difficulty,

                        questions_for_chunk,

                        request.question_type,

                        api_key,

                        backup_model
                    )
                )


            # ------------------------------------------------
            # OTHER API ERROR
            # ------------------------------------------------

            if result is None:

                try:

                    error_details = response.text

                except Exception:

                    error_details = (
                        "Unknown Gemini API error."
                    )


                return {

                    "error":
                        "Gemini API error.",

                    "details":
                        error_details
                }


            # ------------------------------------------------
            # GET QUESTIONS
            # ------------------------------------------------

            questions = result.get(
                "questions",
                []
            )


            if not isinstance(
                questions,
                list
            ):

                questions = []


            # ------------------------------------------------
            # VALIDATE QUESTIONS
            # ------------------------------------------------

            questions = validate_questions(

                questions,

                request.question_type
            )


            # ------------------------------------------------
            # ADD QUESTIONS
            # ------------------------------------------------

            all_questions.extend(
                questions
            )


            print(
                f"Chunk generated "
                f"{len(questions)} valid questions."
            )


        except json.JSONDecodeError:

            return {

                "error":
                    "AI returned invalid JSON.",

                "details":
                    "Please try generating the test again."
            }


        except Exception as e:

            return {

                "error":
                    "Something went wrong.",

                "details":
                    str(e)
            }


        # ----------------------------------------------------
        # SMALL PAUSE BETWEEN REQUESTS
        # ----------------------------------------------------

        if index < chunk_count - 1:

            time.sleep(1)


    # --------------------------------------------------------
    # LIMIT FINAL QUESTIONS
    # --------------------------------------------------------

    all_questions = all_questions[
        :total_questions
    ]


    # --------------------------------------------------------
    # NO QUESTIONS
    # --------------------------------------------------------

    if not all_questions:

        return {

            "error":
                "No questions were generated.",

            "details":
                "Please try again with different study material."
        }


    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    print()

    print(
        f"Generated questions: "
        f"{len(all_questions)}"
    )

    print("=" * 60)

    print()


    return {

        "title":
            "Generated Test",

        "questions":
            all_questions
    }