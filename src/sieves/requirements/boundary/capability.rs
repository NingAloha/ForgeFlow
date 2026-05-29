use anyhow::{Result, anyhow};
use serde_json::Value;

use crate::llm::call_llm_json;

pub fn capture_capability_from_context(context: &Value) -> Result<Value> {
    let user_prompt = serde_json::to_string_pretty(context)
        .map_err(|err| anyhow!("failed to serialize capability capture context: {err}"))?;

    let response = call_llm_json(
        include_str!("prompts/capability_capture_system.txt"),
        &user_prompt,
    )?;

    validate_capability_capture_response(response)
}

fn validate_capability_capture_response(response: Value) -> Result<Value> {
    let top = response
        .as_object()
        .ok_or_else(|| anyhow!("capability capture response must be a JSON object"))?;

    if top.len() != 1 || !top.contains_key("boundary") {
        return Err(anyhow!(
            "capability capture response top-level fields must be exactly: boundary"
        ));
    }

    let boundary = top
        .get("boundary")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("boundary must be an object"))?;

    if boundary.len() != 1 || !boundary.contains_key("capability") {
        return Err(anyhow!(
            "capability capture response boundary fields must be exactly: capability"
        ));
    }

    boundary
        .get("capability")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("boundary.capability must be a string"))?;

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::validate_capability_capture_response;
    use serde_json::json;

    #[test]
    fn validate_capability_capture_response_accepts_valid_capability() {
        let response = json!({
            "boundary": {
                "capability": "统一组织、关联和管理知识"
            }
        });

        let validated =
            validate_capability_capture_response(response.clone()).expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_capability_capture_response_accepts_empty_capability() {
        let response = json!({
            "boundary": {
                "capability": ""
            }
        });

        let validated =
            validate_capability_capture_response(response.clone()).expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_capability_capture_response_rejects_missing_capability() {
        let response = json!({
            "boundary": {}
        });

        let err = validate_capability_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string().contains(
                "capability capture response boundary fields must be exactly: capability"
            )
        );
    }

    #[test]
    fn validate_capability_capture_response_rejects_extra_top_level_field() {
        let response = json!({
            "boundary": {
                "capability": "通过自然语言辅助软件开发"
            },
            "extra": {}
        });

        let err = validate_capability_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("capability capture response top-level fields must be exactly: boundary")
        );
    }

    #[test]
    fn validate_capability_capture_response_rejects_extra_boundary_field() {
        let response = json!({
            "boundary": {
                "capability": "集中管理和协作代码资产",
                "extra": "x"
            }
        });

        let err = validate_capability_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string().contains(
                "capability capture response boundary fields must be exactly: capability"
            )
        );
    }
}
