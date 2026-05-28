use anyhow::{anyhow, Context, Result};
use reqwest::blocking::Client;
use serde_json::{json, Value};
use std::env;

const DEFAULT_API_BASE: &str = "https://api.deepseek.com";

pub fn call_llm_json(system_prompt: &str, user_prompt: &str) -> Result<Value> {
    dotenvy::dotenv().ok();

    let api_key = env::var("MODEL_API_KEY").context("missing MODEL_API_KEY")?;

    let api_base =
        env::var("MODEL_BASE_URL").unwrap_or_else(|_| DEFAULT_API_BASE.to_string());

    let model = env::var("MODEL_NAME").context("missing MODEL_NAME")?;

    let endpoint = format!("{}/chat/completions", api_base.trim_end_matches('/'));

    let request_body = json!({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "response_format": {
            "type": "json_object"
        }
    });

    let client = Client::new();

    let response: Value = client
        .post(endpoint)
        .bearer_auth(api_key)
        .json(&request_body)
        .send()
        .context("failed to send LLM request")?
        .error_for_status()
        .context("LLM request returned non-success status")?
        .json()
        .context("failed to parse LLM response JSON")?;

    let content = response
        .get("choices")
        .and_then(|choices| choices.get(0))
        .and_then(|choice| choice.get("message"))
        .and_then(|message| message.get("content"))
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("LLM response missing choices[0].message.content"))?;

    let parsed: Value =
        serde_json::from_str(content).context("LLM message content is not valid JSON")?;

    if !parsed.is_object() {
        return Err(anyhow!("LLM JSON response must be an object"));
    }

    Ok(parsed)
}