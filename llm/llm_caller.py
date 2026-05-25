import json

from llm.api import call_llm_json, load_text_file


if __name__ == "__main__":
    system_prompt = load_text_file("llm/prompts/json_only_system.txt")
    user_prompt = input("Prompt> ")

    result = call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))