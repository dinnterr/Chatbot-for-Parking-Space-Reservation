import gradio as gr
import pandas as pd

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from evidently import Report
from evidently.presets import DataDriftPreset

from app.reservations import init_db, handle_reservation_chatbot, get_all_reservations
from app.guardrails import guardrail_check

load_dotenv()

# configuration
CHROMA_PATH = r"chroma_db"

init_db()

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True},
)

# initiate the model
llm = init_chat_model(
    "microsoft/Phi-3-mini-4k-instruct",
    model_provider="huggingface",
    temperature=0.5,
    max_tokens=512,
)

# connect to the chromadb
vector_store = Chroma(
    collection_name="parking_spaces",
    embedding_function=embeddings,
    persist_directory=CHROMA_PATH,
)


# Set up the vectorstore to be the retriever
retriever = vector_store.as_retriever(search_kwargs={'k': 3})

# RESERVATION STATE
reservation_state = {
    "active": False,
    "step": None,
    "data": {}
}

# call this function for every message added to the chatbot
def stream_response(message, history):

    # GUARDRAIL CHECK
    if guardrail_check(message):
        return "Your message was blocked due to safety policy."

    # CHECK RESERVATION FLOW FIRST
    reservation_response = handle_reservation_chatbot(message, reservation_state)
    if reservation_response:
        return reservation_response

    msg = message.lower().strip()
    # SHOW RESERVATIONS COMMAND
    if msg in ["show reservations", "list reservations", "all reservations"]:
        rows = get_all_reservations()

        if not rows:
            return "No reservations found."

        result = "All reservations:\n\n"

        for r in rows:
            name, plate, date, time, created_at = r
            result += (
                f"Name:{name}\n"
                f"Plate:{plate}\n"
                f"{date} at {time}\n"
                f"Created: {created_at}\n"
                f"----------------------\n"
            )

        return result

    #RAG
    # retrieve the relevant chunks based on the question asked
    docs = retriever.invoke(message)

    # add all the chunks to 'knowledge'
    knowledge = ""

    for doc in docs:
        knowledge += doc.page_content + "\n\n"

    # make the call to the LLM (including prompt)
    if message is not None:

        rag_prompt = f"""
        You are a parking assistant chatbot which answers questions based on knowledge which is provided to you.
        While answering, you don't use your internal knowledge, 
        but solely the information in the "The knowledge" section.
        You don't mention anything to the user about the provided knowledge.

        The question: {message}

        The knowledge: {knowledge}

        """

        print(rag_prompt)

        response = llm.invoke([
            HumanMessage(content=rag_prompt)
        ])

        response_text = response.content
        if guardrail_check(response_text):
            return "Response blocked due to unsafe content."

        return  response.content.split("<|assistant|>")[-1].strip()

# EVALUATION
eval_dataset = [
    {"question": "What are the parking rates?", "keywords": ["hourly", "daily", "monthly"]},
    {"question": "Are EV chargers available?", "keywords": ["charging", "electric"]},
    {"question": "What is cancellation policy?", "keywords": ["cancel", "refund"]},
    {"question": "What is capacity?", "keywords": ["spaces", "250"]}
]


def evaluate_rag():
    print("Running RAG evaluation...\n")
    results = []

    for ex in eval_dataset:
        docs = retriever.invoke(ex["question"])
        text = " ".join([d.page_content for d in docs]).lower()

        hits = sum(1 for k in ex["keywords"] if k in text)

        precision = hits / len(docs)
        recall = hits / len(ex["keywords"])

        results.append({
            "question": ex["question"],
            "precision@k": precision,
            "recall@k": recall
        })

    df = pd.DataFrame(results)

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=df, current_data=df)

    print("AVG Precision:", df["precision@k"].mean())
    print("AVG Recall:", df["recall@k"].mean())

    return df

# initiate the Gradio app
with gr.Blocks() as demo:
    chatbot = gr.ChatInterface(stream_response, textbox=gr.Textbox(placeholder="Ask about parking or type 'reserve'",
        container=False,
        autoscroll=True,
        scale=7),
    )
    eval_btn = gr.Button("Run RAG Evaluation")
    eval_output = gr.Dataframe()

    def run_eval():
        df = evaluate_rag()
        return df

    eval_btn.click(run_eval, outputs=eval_output)

# launch the Gradio app
demo.launch()


