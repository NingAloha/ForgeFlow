use anyhow::{Context, Result, anyhow};
use reqwest::blocking::Client;
use serde_json::{Value, json};
use std::env;
use std::time::Duration;

const DEFAULT_API_BASE: &str = "https://api.deepseek.com";

pub fn call_llm_json(system_prompt: &str, user_prompt: &str) -> Result<Value> {
    if system_prompt.trim().is_empty() {
        anyhow::bail!("system_prompt must not be empty");
    }
    if user_prompt.trim().is_empty() {
        anyhow::bail!("user_prompt must not be empty");
    }

    dotenvy::dotenv().ok();

    let api_key = read_non_empty_env("MODEL_API_KEY")?;
    let api_base = read_optional_api_base()?;
    let model = read_non_empty_env("MODEL_NAME")?;

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
        "temperature": 0,
        "response_format": {
            "type": "json_object"
        }
    });

    let client = Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .context("failed to build HTTP client")?;

    let http_response = client
        .post(endpoint)
        .bearer_auth(api_key)
        .json(&request_body)
        .send()
        .context("failed to send LLM request")?;

    let status = http_response.status();
    let response_body = http_response
        .text()
        .context("failed to read LLM response body")?;
    if !status.is_success() {
        anyhow::bail!(
            "LLM request returned non-success status {}: {}",
            status,
            response_body
        );
    }

    let response: Value =
        serde_json::from_str(&response_body).context("failed to parse LLM HTTP response JSON")?;

    parse_llm_message_content(&response)
}

fn read_non_empty_env(name: &str) -> Result<String> {
    let raw = match env::var(name) {
        Ok(raw) => raw,
        Err(env::VarError::NotPresent) => return Err(anyhow!("missing {name}")),
        Err(env::VarError::NotUnicode(_)) => {
            return Err(anyhow!("{name} is not valid unicode"));
        }
    };
    let value = raw.trim();
    if value.is_empty() {
        anyhow::bail!("{name} must not be empty");
    }
    Ok(value.to_string())
}

fn read_optional_api_base() -> Result<String> {
    match env::var("MODEL_BASE_URL") {
        Ok(raw) => {
            let value = raw.trim();
            if value.is_empty() {
                anyhow::bail!("MODEL_BASE_URL must not be empty");
            }
            Ok(value.to_string())
        }
        Err(env::VarError::NotPresent) => Ok(DEFAULT_API_BASE.to_string()),
        Err(env::VarError::NotUnicode(_)) => Err(anyhow!("MODEL_BASE_URL is not valid unicode")),
    }
}

fn parse_llm_message_content(response: &Value) -> Result<Value> {
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

#[cfg(test)]
mod tests {
    use super::parse_llm_message_content;
    use serde_json::json;

    #[test]
    fn parse_llm_message_content_accepts_json_object() {
        let response = json!({
            "choices": [
                {
                    "message": {
                        "content": "{\"goal\":\"设计一个集成开发环境\"}"
                    }
                }
            ]
        });

        let parsed = parse_llm_message_content(&response).expect("should parse content");
        assert_eq!(parsed, json!({ "goal": "设计一个集成开发环境" }));
    }

    #[test]
    fn parse_llm_message_content_rejects_missing_content() {
        let response = json!({ "choices": [] });

        let err = parse_llm_message_content(&response).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("LLM response missing choices[0].message.content")
        );
    }

    #[test]
    fn parse_llm_message_content_rejects_invalid_json_content() {
        let response = json!({
            "choices": [
                {
                    "message": {
                        "content": "not-json"
                    }
                }
            ]
        });

        let err = parse_llm_message_content(&response).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("LLM message content is not valid JSON")
        );
    }

    #[test]
    fn parse_llm_message_content_rejects_json_array_content() {
        let response = json!({
            "choices": [
                {
                    "message": {
                        "content": "[1,2,3]"
                    }
                }
            ]
        });

        let err = parse_llm_message_content(&response).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("LLM JSON response must be an object")
        );
    }
}
