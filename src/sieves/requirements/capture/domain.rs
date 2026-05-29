use anyhow::{Result, anyhow};
use serde_json::Value;

use crate::llm::call_llm_json;

pub fn capture_domain(raw_input: &str) -> Result<Value> {
    if raw_input.trim().is_empty() {
        return Err(anyhow!("raw_input must not be empty"));
    }

    let response = call_llm_json(include_str!("prompts/domain_capture_system.txt"), raw_input)?;

    validate_capture_domain_response(raw_input, response)
}

fn validate_capture_domain_response(raw_input: &str, response: Value) -> Result<Value> {
    let top = response
        .as_object()
        .ok_or_else(|| anyhow!("capture response must be a JSON object"))?;

    if top.len() != 2 || !top.contains_key("origin") || !top.contains_key("boundary") {
        return Err(anyhow!(
            "capture response top-level fields must be exactly: origin, boundary"
        ));
    }

    let origin = top
        .get("origin")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("origin must be an object"))?;

    if origin.len() != 1 || !origin.contains_key("raw_input") {
        return Err(anyhow!("origin fields must be exactly: raw_input"));
    }

    let origin_raw_input = origin
        .get("raw_input")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("origin.raw_input must be a string"))?;

    if origin_raw_input != raw_input {
        return Err(anyhow!(
            "origin.raw_input must exactly match the input raw_input"
        ));
    }

    let boundary = top
        .get("boundary")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("boundary must be an object"))?;

    if boundary.len() != 1 || !boundary.contains_key("domain") {
        return Err(anyhow!("boundary fields must be exactly: domain"));
    }

    let domain = boundary
        .get("domain")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("boundary.domain must be a string"))?;

    if domain.trim().is_empty() {
        return Err(anyhow!("boundary.domain must be a non-empty string"));
    }

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::validate_capture_domain_response;
    use serde_json::json;

    #[test]
    fn validate_capture_domain_response_accepts_valid_payload() {
        let raw_input = "做一个 IDE";
        let response = json!({
            "origin": {
                "raw_input": "做一个 IDE"
            },
            "boundary": {
                "domain": "软件开发工具"
            }
        });

        let validated = validate_capture_domain_response(raw_input, response.clone())
            .expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_capture_domain_response_rejects_mismatched_origin_raw_input() {
        let raw_input = "做一个 IDE";
        let response = json!({
            "origin": {
                "raw_input": "做一个 Notion"
            },
            "boundary": {
                "domain": "软件开发工具"
            }
        });

        let err =
            validate_capture_domain_response(raw_input, response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("origin.raw_input must exactly match the input raw_input")
        );
    }

    #[test]
    fn validate_capture_domain_response_rejects_empty_boundary_domain() {
        let raw_input = "做一个 IDE";
        let response = json!({
            "origin": {
                "raw_input": "做一个 IDE"
            },
            "boundary": {
                "domain": "   "
            }
        });

        let err =
            validate_capture_domain_response(raw_input, response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("boundary.domain must be a non-empty string")
        );
    }

    #[test]
    fn validate_capture_domain_response_rejects_missing_boundary_domain() {
        let raw_input = "做一个 IDE";
        let response = json!({
            "origin": {
                "raw_input": "做一个 IDE"
            },
            "boundary": {}
        });

        let err =
            validate_capture_domain_response(raw_input, response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("boundary fields must be exactly: domain")
        );
    }

    #[test]
    fn validate_capture_domain_response_rejects_extra_top_level_field() {
        let raw_input = "做一个 IDE";
        let response = json!({
            "origin": {
                "raw_input": "做一个 IDE"
            },
            "boundary": {
                "domain": "软件开发工具"
            },
            "extra": {}
        });

        let err =
            validate_capture_domain_response(raw_input, response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("capture response top-level fields must be exactly: origin, boundary")
        );
    }
}
