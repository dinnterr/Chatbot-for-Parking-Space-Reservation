from langchain.chat_models import init_chat_model

class AdminAgent:

    def __init__(self):
        self.llm = init_chat_model(
    "microsoft/Phi-3-mini-4k-instruct",
    model_provider="huggingface",
    temperature=0.5,
    max_new_tokens=512,
)

    def create_admin_request(self, reservation_data):

        prompt = f"""
        Create a professional reservation approval request
        for the administrator.

        Reservation:
        {reservation_data}
        """

        response = self.llm.invoke(prompt, clean_up_tokenization_spaces=False)

        return response.content

    def process_admin_response(self, admin_text: str) -> dict:
        """
        Process the administrator's response to return a structured result.

        Args:
            admin_text (str): Text input containing admin's free-form response.

        Returns:
            dict: The processed response in the format:
                {
                    "status": "confirmed" or "rejected",
                    "details": "Any additional details extracted or provided."
                }
        """
        # Define a strict prompt for LLM to return structured data
        prompt = f"""
        You are processing an administrator's response to a reservation. 
        Always respond in the following JSON format:

        {{
            "status": "confirmed/rejected",
            "details": "Any additional information or reasons, or an empty string if no details are provided."
        }}

        Administrator Response:
        {admin_text}

        Respond only with valid JSON and nothing else. No additional explanations, no text outside the JSON.
        """

        # Query the LLM
        response = self.llm.invoke(prompt)

        # Debugging: Log the raw response for troubleshooting
        raw_response = response.content.strip()
        print(f"LLM raw response: {raw_response}")
        assistant_part = raw_response.split("<|assistant|>")[-1].strip()

        # Extract the JSON content
        import json
        import re

        try:
            # search JSON  ```json  ```
            match = re.search(r"```json\s*(\{.*?\})\s*```", assistant_part, re.DOTALL)

            if match:
                json_str = match.group(1)
            else:
                # search first {}
                match = re.search(r"(\{.*\})", assistant_part, re.DOTALL)
                if not match:
                    raise ValueError("No JSON found in response")

                json_str = match.group(1)

            json_response = json.loads(json_str)

            return json_response

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error processing response: {e}")

            return {
                "status": "error",
                "details": "Failed to process admin response. Please try again."
            }
